import time
import spacy
import sys
import os
from transformers import pipeline
import stanza

# Ajouter le chemin du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase

# Connexion à MongoDB
collection = get_mongo_atlass_collection("articles_fr")

# Charger les modèles NLP
nlp_spacy = spacy.load("fr_core_news_md")
stanza.download("fr")
nlp_stanza = stanza.Pipeline("fr")

# Stanza relation_extractor
relation_extractor = pipeline("ner", model="camembert-base", tokenizer="camembert-base")

# Mapping des types d'entités avec leurs abréviations correctes
type_mapping = {
    "personne": "pers",
    "organisation": "org",
    "lieu": "loc",
    "événement": "event"
}

# Fonction pour obtenir les types d'entités avec leurs abréviations correctes
def get_type_abbreviation(type_entite):
    type_entite = type_entite.lower()
    abbreviation = type_mapping.get(type_entite, None)
    if not abbreviation:
        print(f"Erreur : type d'entité '{type_entite}' invalide.")
    return abbreviation

def get_entites_from_supabase(article_id):
    """Récupère les entités associées à un article depuis Supabase."""
    entites = {
        "personnes": [],
        "lieux": [],
        "organisations": [],
        "evenements": []
    }

    tables = {
        "personnes": "entite_fr_pers",
        "lieux": "entite_fr_loc",
        "organisations": "entite_fr_org",
        "evenements": "entite_fr_event"
    }

    for key, table in tables.items():
        response = supabase.table(table).select("*").eq("article_id", article_id).execute()
        if hasattr(response, "data") and response.data:
            entites[key] = [item["nom"] for item in response.data]

    return entites

def extract_keywords_spacy(text):
    """Extraction des mots-clés (noms et verbes) avec SpaCy."""
    doc = nlp_spacy(text)
    keywords = []

    for token in doc:
        if token.pos_ in ["NOUN", "VERB"]:  # Nous gardons uniquement les noms et les verbes
            keywords.append(token.text)

    return keywords

def extract_relations_spacy(text, entites):
    """Extraction des relations avec SpaCy."""
    doc = nlp_spacy(text)
    relations = []
    keywords = extract_keywords_spacy(text)  # Extraire les mots-clés

    for ent1 in doc.ents:
        for ent2 in doc.ents:
            if ent1 != ent2 and ent1.start < ent2.start:
                sentence = next((sent for sent in doc.sents if ent1 in sent and ent2 in sent), None)
                if sentence:
                    # Filtrage des relations en gardant uniquement les verbes et noms significatifs
                    relation_words = [token.text for token in sentence if token.pos_ in ["VERB", "NOUN"]
                                      and token.text in keywords and len(token.text.split()) > 1]
                    relation = " ".join(relation_words)

                    if relation and len(relation.split()) > 1:  # Vérifie que la relation a un sens
                        # Associer les entités à leurs IDs correspondants
                        id_ent1 = next((item["id"] for item in entites["personnes"] if item["nom"] == ent1.text), None)
                        id_ent2 = next((item["id"] for item in entites["lieux"] if item["nom"] == ent2.text), None)

                        if id_ent1 and id_ent2:
                            relations.append((id_ent1, "pers", id_ent2, "loc", relation))
                        else:
                            id_event = next((item["id"] for item in entites["evenements"] if item["nom"] == ent2.text), None)
                            if id_event:
                                relations.append((id_ent1, "pers", id_event, "event", relation))
                            else:
                                id_org = next((item["id"] for item in entites["organisations"] if item["nom"] == ent2.text), None)
                                if id_org:
                                    relations.append((id_ent1, "pers", id_org, "org", relation))
                                else:
                                    # Gestion des relations entre organisations et événements
                                    id_org_ent1 = next((item["id"] for item in entites["organisations"] if item["nom"] == ent1.text), None)
                                    id_event_ent2 = next((item["id"] for item in entites["evenements"] if item["nom"] == ent2.text), None)
                                    if id_org_ent1 and id_event_ent2:
                                        relations.append((id_org_ent1, "org", id_event_ent2, "event", relation))

    return relations

def extract_relations_stanza(text, entites):
    """Extrait les relations entre les entités dans un texte donné en utilisant Stanza."""
    doc = nlp_stanza(text)
    relations = []
    keywords = extract_keywords_spacy(text)  # Extraire les mots-clés

    for sentence in doc.sentences:
        for ent1 in sentence.ents:
            for ent2 in sentence.ents:
                if ent1 != ent2 and ent1.start_char is not None and ent2.start_char is not None:
                    if ent1.start_char < ent2.start_char:
                        words_between = [
                            word.text for word in sentence.words
                            if word.start_char is not None and ent1.start_char < word.start_char < ent2.start_char
                            and word.text in keywords
                        ]
                        relation = " ".join(words_between)
                        if relation and len(relation.split()) > 1:  # Vérifie que la relation a un sens
                            if ent1.text in entites["personnes"] and ent2.text in entites["lieux"]:
                                relations.append((ent1.text, "personne", ent2.text, "lieu", relation))
                            elif ent1.text in entites["organisations"] and ent2.text in entites["evenements"]:
                                relations.append((ent1.text, "organisation", ent2.text, "evenement", relation))
                            elif ent1.text in entites["personnes"] and ent2.text in entites["organisations"]:
                                relations.append((ent1.text, "personne", ent2.text, "organisation", relation))
                            elif ent1.text in entites["personnes"] and ent2.text in entites["evenements"]:
                                relations.append((ent1.text, "personne", ent2.text, "evenement", relation))

    return relations

def extract_relations_bert(text):
    """Extraction des relations avec CamemBERT."""
    relations = []
    sentences = text.split(". ")

    for sentence in sentences:
        result = relation_extractor(sentence)
        print(result)  # Afficher le résultat brut
        if result and isinstance(result, list):
            for item in result:
                if "label" in item and "score" in item:
                    relations.append((sentence, "relation_detectée", item["label"], item["score"]))
                else:
                    print(f"Clé manquante dans l'élément : {item}")

    return relations

def fusionner_relations(relations_spacy, relations_stanza, relations_bert):
    """Fusionne les relations des trois modèles en éliminant les doublons."""
    relations_finales = set(relations_spacy + relations_stanza)

    for relation in relations_bert:
        sentence, _, label, _ = relation
        if label not in [r[4] for r in relations_finales]:  # Vérifie si la relation est déjà présente
            relations_finales.add(("BERT", "-", "-", "-", label))

    return list(relations_finales)

def enregistrer_relations(relations_finales, article_id):
    for relation in relations_finales:
        id_source = get_entite_id(relation[0], relation[1])  # Nom et type de source
        id_cible = get_entite_id(relation[2], relation[3])  # Nom et type de cible

        if not id_source or not id_cible:
            print(f"⚠️ Relation ignorée : ID manquant pour source ou cible. Source: {relation[0]}, Cible: {relation[2]}")
            continue  # Passer cette relation si les IDs sont manquants

        data = {
            "id_source": id_source,
            "type_source": relation[1],  # 'personne', 'lieu', etc.
            "id_cible": id_cible,
            "type_cible": relation[3],  # 'personne', 'lieu', etc.
            "relation": relation[4],  # Relation texte
            "article_id": article_id
        }

        # Affichage pour débogage
        print("Données insérées dans la table relations_fr :", data)

        response = supabase.table("relations_fr").insert(data).execute()
        if response:
            print(f"✅ Relation insérée avec succès: {data}")
        else:
            print(f"❌ Erreur lors de l'insertion de la relation: {response.error}")

def get_entite_id(nom, type_entite):
    """Récupère l'ID d'une entité en fonction de son nom et de son type."""
    type_abbr = get_type_abbreviation(type_entite)
    if not type_abbr:
        return None

    table_mapping = {
        "pers": "entite_fr_pers",
        "org": "entite_fr_org",
        "loc": "entite_fr_loc",
        "event": "entite_fr_event"
    }

    table_name = table_mapping.get(type_abbr)
    if not table_name:
        print(f"Erreur : Table pour {type_abbr} non trouvée.")
        return None

    response = supabase.table(table_name).select("id").eq("nom", nom).execute()
    if hasattr(response, "data") and response.data:
        return response.data[0]["id"]
    else:
        print(f"⚠️ Entité '{nom}' de type '{type_entite}' non trouvée dans la table '{table_name}'.")
        return None

def traiter_relations():
    """Traite les relations pour tous les articles extraits de MongoDB par lots de 300."""
    batch_size = 300
    skip = 0
    
    while True:
        batch = list(collection.find().skip(skip).limit(batch_size))
        if not batch:
            print("⚠️ Aucun article trouvé dans la base MongoDB.")
            break

        for doc in batch:
            titre = doc.get("titre", "").strip()
            contenu = doc.get("contenu", "").strip()
            article_id = str(doc.get("_id"))
            full_text = f"{titre}. {contenu}"

            print(f"🔍 Traitement de l'article {article_id}...")

            entites = get_entites_from_supabase(article_id)
            print(f"🔍 Entités récupérées:", entites)

            relations_spacy = extract_relations_spacy(full_text, entites)
            relations_stanza = extract_relations_stanza(full_text, entites)
            relations_bert = extract_relations_bert(full_text)

            relations_finales = fusionner_relations(relations_spacy, relations_stanza, relations_bert)
            print(f"🔍 Relations extraites:", relations_finales)

            if relations_finales:
                enregistrer_relations(relations_finales, article_id)

            print(f"✅ Traitement terminé pour l'article {article_id}.")

        # Pause pour éviter la surcharge
        delay = 0.5  # Délai de 5 secondes entre les traitements d'articles
        print(f"Pausing for {delay} seconds...")
        time.sleep(delay)
        
        skip += batch_size


if __name__ == "__main__":
    print("🔍 Démarrage du traitement des relations entre les entités...")
    traiter_relations()
    print("🎉 Traitement terminé !")
