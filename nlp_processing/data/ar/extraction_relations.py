import time 
import logging
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline, AutoModelForSequenceClassification
from .connect_supabase import supabase 
from config.mongo_atlass import get_mongo_atlass_collection 
from bson import ObjectId  # Import nécessaire pour la conversion en ObjectId
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Connexion à MongoDB
collection = get_mongo_atlass_collection("articles_ar")


@lru_cache(maxsize=1)
def load_models():
    ner_model = AutoModelForTokenClassification.from_pretrained("ychenNLP/arabic-ner-ace")
    ner_tokenizer = AutoTokenizer.from_pretrained("ychenNLP/arabic-ner-ace")
    ner_pip = pipeline("ner", model=ner_model, tokenizer=ner_tokenizer, grouped_entities=True)

    re_model = AutoModelForSequenceClassification.from_pretrained("ychenNLP/arabic-relation-extraction")
    re_tokenizer = AutoTokenizer.from_pretrained("ychenNLP/arabic-relation-extraction")
    re_pip = pipeline("text-classification", model=re_model, tokenizer=re_tokenizer)

    return ner_pip, re_pip, re_tokenizer

ner_pip, re_pip , re_tokenizer= load_models()
# Dictionnaire de traduction des relations
relation_translation = {
    "ORG-AFF": "ينتمي إلى",
    "PART-WHOLE": "جزء من",
    "GEN-AFF": "علاقة جغرافية",
    "PHYS": "مادي"
}

def process_ner_output(entity_mention, inputs):
    """Prépare les paires d'entités pour la détection des relations."""
    re_input = []
    for idx1 in range(len(entity_mention) - 1):
        for idx2 in range(idx1 + 1, len(entity_mention)):
            ent_1 = entity_mention[idx1]
            ent_2 = entity_mention[idx2]
            ent_1_type = ent_1['entity_group']
            ent_2_type = ent_2['entity_group']
            ent_1_s = ent_1['start']
            ent_1_e = ent_1['end']
            ent_2_s = ent_2['start']
            ent_2_e = ent_2['end']
            new_re_input = ""
            for c_idx, c in enumerate(inputs):
                if c_idx == ent_1_s:
                    new_re_input += "<{}>".format(ent_1_type)
                elif c_idx == ent_1_e:
                    new_re_input += "</{}>".format(ent_1_type)
                elif c_idx == ent_2_s:
                    new_re_input += "<{}>".format(ent_2_type)
                elif c_idx == ent_2_e:
                    new_re_input += "</{}>".format(ent_2_type)
                new_re_input += c
            re_input.append({"re_input": new_re_input, "arg1": ent_1, "arg2": ent_2, "input": inputs})
    return re_input

def post_process_re_output(re_output, text_input, ner_output, re_input):
    """Post-traitement des résultats d'extraction des relations."""
    final_output = []
    for idx, out in enumerate(re_output):
        if out["label"] != 'O':
            tmp = re_input[idx]
            tmp['relation_type'] = relation_translation.get(out["label"], out["label"])
            tmp.pop('re_input', None)
            final_output.append(tmp)
    
    template = {"input": text_input,
                "entity": ner_output,
                "relation": final_output}
    return template

def prepare_relation_inputs(entites, text):
    """Prépare les paires d'entités pour la détection des relations."""
    relation_inputs = []
    
    seen_pairs = set()
    
    # Filtrage des entités : Personnes, Lieux, Organisations, et GPE
    relevant_entities = { "personnes": entites["personnes"], "lieux": entites["lieux"], "organisations": entites["organisations"], "gpe": entites["gpe"] }
    
    for key1, entity_list1 in relevant_entities.items():
        for key2, entity_list2 in relevant_entities.items():
            for entity_1 in entity_list1:
                for entity_2 in entity_list2:
                    if entity_1 != entity_2 and (entity_1, entity_2) not in seen_pairs:
                        seen_pairs.add((entity_1, entity_2))
                        seen_pairs.add((entity_2, entity_1))
                        marked_text = text.replace(entity_1, f"<{key1.upper()}>{entity_1}</{key1.upper()}>")
                        marked_text = marked_text.replace(entity_2, f"<{key2.upper()}>{entity_2}</{key2.upper()}>")
                        
                        # Troncature des textes si nécessaire
                        tokens = re_tokenizer.tokenize(marked_text)
                        if len(tokens) > 510:  # Limite de longueur du modèle
                            tokens = tokens[:510]
                        truncated_text = re_tokenizer.convert_tokens_to_string(tokens)
                        
                        relation_inputs.append({
                            "text": truncated_text,
                            "entity_1": entity_1,
                            "entity_2": entity_2,
                            "type_1": key1,
                            "type_2": key2
                        })
    
    return relation_inputs

def extract_relations_with_entities(text, entites):
    """Utilise le modèle de Relation Extraction pour détecter les relations entre les entités."""
    relation_inputs = prepare_relation_inputs(entites, text)
    relations = []
    
    for input_data in relation_inputs:
        try:
            prediction = re_pip(input_data["text"])[0]
            if prediction["label"] != "O":
                relations.append({
                    "entity_1": input_data["entity_1"],
                    "entity_2": input_data["entity_2"],
                    "relation_type": prediction["label"],
                    "score": prediction["score"]
                })
        except Exception as e:
            logging.error(f"Erreur lors de la prédiction pour {input_data['entity_1']} et {input_data['entity_2']}: {e}")
    
    return relations

def insert_relations_in_supabase(article_id, relations, source_title):
    """Insère les relations extraites dans Supabase en batch."""
    batch_data = []

    for relation in relations:
        try:
            batch_data.append({
                "nom_source": relation['arg1']['word'],  # Entité source
                "type_source": relation['arg1']['entity_group'],  # Type de l'entité source
                "nom_cible": relation['arg2']['word'],  # Entité cible
                "type_cible": relation['arg2']['entity_group'],  # Type de l'entité cible
                "relation": relation['relation_type'],  # Type de relation
                "source_title": source_title,  # Titre de l'article
                "article_id": article_id  # ID de l'article
            })
        except Exception as e:
            logging.error(f"❌ Erreur lors de la préparation de la relation : {e}")

    if batch_data:
        try:
            response = supabase.table("relations_ar").insert(batch_data).execute()
            if response.error:
                logging.error(f"❌ Erreur d'insertion dans Supabase : {response.error}")
            else:
                logging.info(f"✅ {len(batch_data)} relations insérées avec succès.")
        except Exception as e:
            logging.error(f"❌ Erreur lors de l'insertion en batch : {e}")

def process_article(doc):
    """Traite chaque article pour extraire les relations et les insérer dans Supabase."""
    try:
        titre = doc.get("titre", "").strip()
        contenu = doc.get("contenu", "").strip()
        article_id = str(doc.get("_id"))
        full_text = f"{titre}. {contenu}"

        logging.info(f"🔍 Traitement de l'article {article_id}...")

        # Extraction des entités nommées
        ner_output = ner_pip(full_text)
        entites = {"personnes": [], "lieux": [], "organisations": [], "gpe": []}

        for entity in ner_output:
            entity_type = entity['entity_group']
            if entity_type == "PER":
                entites["personnes"].append(entity['word'])
            elif entity_type == "LOC" or entity_type == "FAC" or entity_type == "GPE":
                entites["lieux"].append(entity['word'])
            elif entity_type == "ORG":
                entites["organisations"].append(entity['word'])
            elif entity_type == "GPE":
                entites["gpe"].append(entity['word'])

        logging.info(f"🔍 Entités extraites: {entites}")

        # Traitement des relations
        re_input = process_ner_output(ner_output, full_text)
        re_output = [re_pip(input_data["re_input"])[0] for input_data in re_input]
        re_ner_output = post_process_re_output(re_output, full_text, ner_output, re_input)

        logging.info(f"🔍 Relations extraites: {re_ner_output['relation']}")

        # Insérer dans Supabase
        insert_relations_in_supabase(article_id, re_ner_output['relation'], titre)

        logging.info(f"✅ Traitement terminé pour l'article {article_id}.")
    except Exception as e:
        logging.error(f"Erreur lors du traitement de l'article {article_id}: {e}")

def traiter_relations():
    """Traite les relations pour tous les articles extraits de MongoDB par lots de 300, en commençant à partir de l'article spécifié."""
    batch_size = 300
    start_article_id = "67b5d3b49211c9a78d8912b4"  # ID de l'article de départ
    
    # Conversion de l'ID sous forme de chaîne en ObjectId
    article_id = ObjectId(start_article_id)  # Conversion en ObjectId
    starting_article = collection.find_one({"_id": article_id})  # Recherche de l'article dans MongoDB

    if starting_article:
        # Calculer la position de l'article de départ
        skip = collection.count_documents({"_id": {"$lt": article_id}})
        logging.info(f"🔍 Démarrage à partir de l'article {start_article_id} (position {skip})")
    else:
        logging.warning(f"L'article {start_article_id} n'a pas été trouvé.")
        return  # Si l'article n'est pas trouvé, sortir de la fonction

    while True:
        # Récupérer un lot d'articles
        batch = list(collection.find().skip(skip).limit(batch_size))
        if not batch:
            logging.warning("⚠️ Aucun article trouvé dans la base MongoDB.")
            break

        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(process_article, batch)

        # Pause et mise à jour du compteur skip
        delay = 0.01
        logging.info(f"Pause de {delay} secondes...")
        time.sleep(delay)

        skip += batch_size

# Exécution
if __name__ == "__main__":
    traiter_relations()