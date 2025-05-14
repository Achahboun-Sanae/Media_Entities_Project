import os
import sys
from datetime import datetime
import locale  # Pour gérer les formats de date en français
from pretraitement import clean_text, filter_entities
from extraction_entites import extract_entities_spacy, extract_entities_stanza, extract_entities_bert, merge_entities
from eventsdetection import traitement_titre
import time

# Ajouter le chemin d'importation du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase
from bson import ObjectId

# Définir la locale française pour parser les dates
locale.setlocale(locale.LC_TIME, "fr_FR")

# Connexion à MongoDB
collection = get_mongo_atlass_collection("articles_fr")

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

def process_single_french_article(article_id_str):
    article_id = ObjectId(article_id_str)
    doc = collection.find_one({"_id": article_id})
    
    if not doc:
        return {"error": "Article non trouvé"}
    
    title = doc.get("titre", "")
    content = doc.get("contenu", "")
    
    cleaned_text = clean_text(f"{title} {content}")
    
    ents = [
        extract_entities_spacy(cleaned_text),
        extract_entities_stanza(cleaned_text),
        extract_entities_bert(cleaned_text),
    ]
    
    merged = merge_entities(ents)
    filtered = filter_entities(merged)
    
    categories = {
        "persons": [],
        "locations": [],
        "organizations": [],
        "events": [],
    }
    
    for entity, label in filtered:
        if label == "PERSON":
            categories["persons"].append(entity)
        elif label == "LOCATION":
            categories["locations"].append(entity)
        elif label == "ORGANIZATION":
            categories["organizations"].append(entity)
        elif label == "EVENT":
            categories["events"].append(entity)

    try:
        titre_events = traitement_titre(title)
        if isinstance(titre_events, list):
            categories["events"] = titre_events
        elif isinstance(titre_events, str):
            categories["events"] = [titre_events]
    except Exception as e:
        print(f"Erreur lors du traitement du titre: {e}")
    
    result = {
        "persons": sorted(list(set(categories["persons"]))),
        "locations": sorted(list(set(categories["locations"]))),
        "organizations": sorted(list(set(categories["organizations"]))),
        "events": sorted(list(set(
            [e.strip() for e in categories["events"] if len(e.strip()) > 2]
        ))),
    }

    article_id_str = str(article_id)
    enregistrer_entites(result["persons"], article_id_str, "entite_fr_pers")
    enregistrer_entites(result["locations"], article_id_str, "entite_fr_loc")
    enregistrer_entites(result["organizations"], article_id_str, "entite_fr_org")
    
    raw_date = doc.get("date", None)
    events_with_date = [(e, raw_date) for e in result["events"] if isinstance(e, str) and e.strip()]
    enregistrer_entites(events_with_date, article_id_str, "entite_fr_event", include_date=True)

    return result

def article_already_processed(article_id):
    """
    Vérifie si l'article est déjà présent dans toutes les tables Supabase.
    """
    tables = ["entite_fr_pers", "entite_fr_loc", "entite_fr_org", "entite_fr_event"]
    for table in tables:
        try:
            response = supabase.table(table).select("id").eq("article_id", article_id).limit(1).execute()
            if not response.data:
                return False
        except Exception as e:
            print(f"⚠️ Erreur de vérification dans {table} : {e}")
            return False
    return True


def process_french_articles_from_id(start_id_str, batch_size=300, delay=0.5):
    # start_id = ObjectId(start_id_str)
    # query = {"_id": {"$gte": start_id}}
    start_id = ObjectId(start_id_str)
    query = {
        "_id": {"$gte": start_id},
        "source": "le360_fr"  # 🔍 Filtre pour ne traiter que les articles de cette source
    }
    skip = 0

    while True:
        batch = list(collection.find(query).skip(skip).limit(batch_size))
        if not batch:
            break

        for doc in batch:
            article_id_str = str(doc["_id"])

            if article_already_processed(article_id_str):
                print(f"⏩ Article {article_id_str} déjà traité. On passe.")
                continue

            print(f"🔍 Traitement article {article_id_str}")
            try:
                process_single_french_article(article_id_str)
            except Exception as e:
                print(f"❌ Erreur sur l'article {article_id_str} : {e}")

        print(f"✅ {len(batch)} articles traités. Pause de {delay} secondes.")
        time.sleep(delay)
        skip += batch_size

# Exemple d'utilisation

if __name__ == "__main__":
    print("🚀 Démarrage du traitement des articles français depuis un ID spécifique...")
    process_french_articles_from_id("68098ff0aa9ac536723721db")
    print("🎉 Traitement terminé.")
