from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from .connect_mongo import connect_mongo
from .connect_supabase import supabase  # Import de la connexion Supabase
from .clean_text import clean_text  
from .tokenize_and_lemmatize_text import tokenize_and_lemmatize_text
from .ner_extraction import extract_entities_bert
import stanza
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
import time

# Dictionnaire des mois en arabe et leur traduction en numérique (format sur deux chiffres)
mois_arabe = {
    "يناير": "01", "فبراير": "02", "مارس": "03", "أبريل": "04",
    "مايو": "05", "يونيو": "06", "يوليو": "07", "أغسطس": "08",
    "سبتمبر": "09", "أكتوبر": "10", "نوفمبر": "11", "ديسمبر": "12"
}

def convertir_date_arabe(date_arabe):
    """
    Convertir une date en arabe de la forme "الأربعاء 19 فبراير 2025 - 10:51"
    en le format "YYYY-MM-DD HH:MM:SS".
    """
    parts = date_arabe.split(' - ')
    if len(parts) != 2:
        return None  # Format inattendu
    date_part, time_part = parts
    date_parts = date_part.split()
    if len(date_parts) != 4:
        return None
    jour = date_parts[1]
    mois_arabe_part = date_parts[2]
    annee = date_parts[3]
    mois_num = mois_arabe.get(mois_arabe_part, None)
    if not mois_num:
        return None
    date_str = f"{annee}-{mois_num}-{jour} {time_part}:00"
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return date_obj.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

# Connexion à MongoDB
mongo_collection = connect_mongo("articles_ar")

# Télécharger les ressources pour Stanza (arabe)
stanza.download('ar')
nlp_stanza = stanza.Pipeline('ar', processors='tokenize,mwt,pos,lemma,ner')

# Charger le modèle BERT pour la NER arabe
model_name = "hatmimoha/arabic-ner"
model = AutoModelForTokenClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
nlp_ner = pipeline("ner", model=model, tokenizer=tokenizer)

def chunk_text_smart(text, max_length=507):
    """ Divise le texte en segments de max 512 tokens en respectant les phrases. """
    doc = nlp_stanza(text)
    sentences = [" ".join([word.text for word in sent.words]) for sent in doc.sentences]

    chunks, current_chunk, current_length = [], [], 0
    for sentence in sentences:
        tokens = tokenizer.tokenize(sentence)
        token_count = len(tokens)

        while token_count > max_length:
            chunks.append(tokenizer.convert_tokens_to_string(tokens[:max_length]))
            tokens = tokens[max_length:]
            token_count = len(tokens)
        
        if current_length + token_count > max_length:
            if current_chunk:
                chunks.append(tokenizer.convert_tokens_to_string(current_chunk))
            current_chunk, current_length = tokens, token_count
        else:
            current_chunk.extend(tokens)
            current_length += token_count

    if current_chunk:
        chunks.append(tokenizer.convert_tokens_to_string(current_chunk))

    return chunks

def merge_entities(entities):
    """ Fusionne les entités fragmentées en une seule. """
    merged_entities = []
    current_entity, current_label = "", ""

    for entity, label in entities:
        if label.startswith("B-"):  # Nouvelle entité
            if current_entity:  
                merged_entities.append((current_entity.strip(), current_label))
            current_entity, current_label = entity, label[2:]  # Retirer le préfixe B-
        elif label.startswith("I-") and current_label == label[2:]:  # Continuité de la même entité
            current_entity += " " + entity
        else:
            if current_entity:
                merged_entities.append((current_entity.strip(), current_label))
            current_entity, current_label = entity, label  # Nouvelle entité indépendante

    if current_entity:
        merged_entities.append((current_entity.strip(), current_label))  # Ajouter la dernière entité

    return merged_entities

def process_text(text):
    """ Pipeline NLP complet : nettoyage, segmentation, tokenisation, lemmatisation, NER. """
    cleaned_text = clean_text(text)
    chunked_texts = chunk_text_smart(cleaned_text)

    all_tokens, all_lemmatized_tokens, all_entities = [], [], []
    for chunk in chunked_texts:
        tokens, lemmatized_tokens = tokenize_and_lemmatize_text(chunk)
        entities = extract_entities_bert(chunk)
        all_tokens.extend(tokens)
        all_lemmatized_tokens.extend(lemmatized_tokens)
        all_entities.extend(entities)

    # Correction des tokens fragmentés (ex: ##phosphates) et fusion des entités
    corrected_entities = []
    for entity, label in all_entities:
        if entity.startswith("##") and corrected_entities:
            corrected_entities[-1] = (corrected_entities[-1][0] + entity[2:], label)
        else:
            corrected_entities.append((entity, label))

    # Fusion des entités multi-mots
    merged_entities = merge_entities(corrected_entities)

    # Filtrage des entités pertinentes
    filtered_entities = [(ent, label) for ent, label in merged_entities if label in [
        'PERSON', 'LOCATION', 'ORGANIZATION', 'EVENT'
    ]] 

    # Suppression des doublons
    unique_entities = list({(entity, label): (entity, label) for entity, label in filtered_entities}.values())

    return {
        'cleaned_text': cleaned_text,
        'tokens': all_tokens,
        'lemmatized_tokens': all_lemmatized_tokens,
        'entities': unique_entities
    }

def process_and_store_article(article):
    """ Traite un article individuel et insère les entités dans Supabase """
    titre = article.get("titre", "").strip()
    contenu = article.get("contenu", "").strip()
    article_id = str(article.get("_id"))
    date_article = article.get("date")  # Date au format arabe stockée dans MongoDB
    full_text = f"{titre}. {contenu}"
    
    if full_text:
        # Traitement du texte
        result = process_text(full_text)
        entities = result['entities']

        # Convertir la date de l'article au format désiré pour les événements
        timestamp = None
        if date_article:
            timestamp = convertir_date_arabe(date_article)

        # Insertion des entités dans Supabase (PostgreSQL)
        for entity, label in entities:
            data = {
                "nom": entity,
                "article_id": article_id
            }
            if label == 'PERSON':
                response = supabase.table("entite_ar_pers").insert(data).execute()
            elif label == 'LOCATION':
                response = supabase.table("entite_ar_loc").insert(data).execute()
            elif label == 'ORGANIZATION':
                response = supabase.table("entite_ar_org").insert(data).execute()
            elif label == 'EVENT':
                data["date"] = timestamp  # Date convertie ou None si la conversion a échoué
                response = supabase.table("entite_ar_event").insert(data).execute()

            # Vérification de l'insertion
            if response.data:
                print(f"✅ Entité enregistrée : {data}")
            else:
                print(f"❌ Erreur d'insertion : {response.error_message}")

def process_and_store_articles_in_batches(batch_size=300, max_workers=8):
    """ Récupère les articles par lots, applique le pipeline NLP et insère les entités dans Supabase en parallèle. """
    cursor = mongo_collection.find().limit(batch_size)  # Récupérer les articles par lots
    articles = list(cursor)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_article = {executor.submit(process_and_store_article, article): article for article in articles}

        for future in as_completed(future_to_article):
            article = future_to_article[future]
            try:
                future.result()
            except Exception as e:
                print(f"❌ Erreur dans un thread pour l'article {article.get('_id')}: {e}")
    print(f"✅ Batch traité.")

if __name__ == "__main__":
    print("🔍 Traitement des articles en cours...")
    process_and_store_articles_in_batches(batch_size=300, max_workers=8)
