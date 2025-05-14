import os
import sys
import time
from bson import ObjectId
from datetime import datetime
from pretraitement import clean_text, filter_entities
from extraction_entites import extract_entities_spacy, extract_entities_stanza, extract_entities_bert, merge_entities
from eventsdetection import traitement_titre

# Configuration MongoDB et Supabase
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase

collection = get_mongo_atlass_collection("articles_eng")


def article_already_processed(article_id):
    """
    Vérifie si l'article est déjà présent dans toutes les tables Supabase.
    """
    tables = ["entite_en_pers", "entite_en_loc", "entite_en_org", "entite_en_event"]
    for table in tables:
        try:
            response = supabase.table(table).select("id").eq("article_id", article_id).limit(1).execute()
            if not response.data:
                return False
        except Exception as e:
            print(f"⚠️ Erreur de vérification dans {table} : {e}")
            return False
    return True


def enregistrer_entites(entites, article_id, table_name, include_date=False):
    for entite in entites:
        if include_date:
            if isinstance(entite, tuple) and len(entite) == 2:
                nom, date_article = entite
                if not date_article:
                    continue
                if isinstance(date_article, datetime):
                    date_article = date_article.isoformat()
                data = {
                    "nom": nom,
                    "article_id": article_id,
                    "date": date_article
                }
            else:
                continue
        else:
            nom = entite
            data = {
                "nom": nom,
                "article_id": article_id
            }

        try:
            exists = supabase.table(table_name).select("id").match({
                "nom": nom,
                "article_id": article_id
            }).execute()

            if not exists.data:
                supabase.table(table_name).insert(data).execute()
        except Exception as e:
            print(f"Erreur lors de l'insertion de '{nom}' dans {table_name} : {e}")


def process_single_english_article(article_id_str):
    article_id = ObjectId(article_id_str)
    doc = collection.find_one({"_id": article_id})

    if not doc:
        return {"error": "Article not found"}

    title = doc.get("titre", "")
    content = doc.get("contenu", "")

    cleaned_text = clean_text(f"{title} {content}")

    entities = merge_entities([
        extract_entities_spacy(cleaned_text),
        extract_entities_stanza(cleaned_text),
        extract_entities_bert(cleaned_text[:512])
    ])

    filtered_entities = filter_entities(entities)

    raw_events = traitement_titre(title)
    if isinstance(raw_events, str):
        events = [raw_events]
    elif isinstance(raw_events, list):
        events = raw_events
    else:
        events = []

    result = {
        "persons": [ent[0] for ent in filtered_entities if ent[1] == 'PERSON'],
        "locations": [ent[0] for ent in filtered_entities if ent[1] == 'LOC'],
        "organizations": [ent[0] for ent in filtered_entities if ent[1] == 'ORG'],
        "events": events
    }

    article_id_str = str(article_id)
    enregistrer_entites(result["persons"], article_id_str, "entite_en_pers")
    enregistrer_entites(result["locations"], article_id_str, "entite_en_loc")
    enregistrer_entites(result["organizations"], article_id_str, "entite_en_org")

    raw_date = doc.get("date", None)
    events_with_date = [(e, raw_date) for e in result["events"] if isinstance(e, str) and e.strip()]
    enregistrer_entites(events_with_date, article_id_str, "entite_en_event", include_date=True)

    return result


def process_all_english_articles(batch_size=300, delay=0.5):
    skip = 0
    while True:
        batch = list(collection.find().skip(skip).limit(batch_size))
        if not batch:
            break

        for doc in batch:
            article_id_str = str(doc["_id"])

            if article_already_processed(article_id_str):
                print(f"⏩ Article {article_id_str} déjà traité. On passe.")
                continue

            print(f"🔍 Traitement article {article_id_str}")
            try:
                process_single_english_article(article_id_str)
            except Exception as e:
                print(f"❌ Erreur sur l'article {article_id_str} : {e}")

        print(f"✅ {len(batch)} articles traités. Pause de {delay} secondes.")
        time.sleep(delay)
        skip += batch_size


# Exemple d'utilisation
if __name__ == "__main__":
    print("🚀 Démarrage du traitement de tous les articles anglais...")
    process_all_english_articles()
    print("🎉 Traitement terminé.")
