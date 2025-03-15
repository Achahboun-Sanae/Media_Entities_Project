import os
import sys
from datetime import datetime
import locale
from pretraitement import clean_text, filter_entities
from extraction_entites import extract_entities_spacy, extract_entities_stanza, extract_entities_bert, merge_entities
from eventsdetection import traitement_titre
import time

# Ajouter le chemin d'importation du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase

# Définir la locale française pour parser les dates
locale.setlocale(locale.LC_TIME, "fr_FR")

# Connexion à MongoDB
collection = get_mongo_atlass_collection("articles_fr")

def convert_date(date_str):
    """Convertit une date en format ISO 8601 (TIMESTAMPTZ)"""
    if not date_str or date_str.lower() == "date non disponible":
        return None  # Retourner None si la date est indisponible

    try:
        # Cas 1: Format "Le 18/02/2025 à 19h50"
        if date_str.startswith("Le "):
            date_str = date_str.replace("Le ", "").replace(" à", " -")  # Nettoyer et ajuster le format
            parsed_date = datetime.strptime(date_str, "%d/%m/%Y - %Hh%M")
            return parsed_date.isoformat()

        # Cas 2: Format "samedi 15 février 2025 - 18:10"
        # Ce format est déjà pris en charge par strptime avec la locale définie sur le français
        parsed_date = datetime.strptime(date_str, "%A %d %B %Y - %H:%M")
        return parsed_date.isoformat()

    except ValueError as e:
        print(f"⚠️ Erreur de conversion de la date '{date_str}': {e}")
        return None  # Retourner None en cas d'échec
 
def process_document(doc):
    titre = doc.get("titre", "").strip()
    contenu = doc.get("contenu", "").strip()
    article_id = str(doc.get("_id"))
    raw_date = doc.get("date", None)  # Récupérer la date brute
    date_article = convert_date(raw_date)  # Convertir au bon format
    
    if not titre and not contenu:
        return None
    
    full_text = f"{titre}. {contenu}"
    cleaned_text = clean_text(full_text)
    
    entities_spacy = extract_entities_spacy(cleaned_text)
    entities_stanza = extract_entities_stanza(cleaned_text)
    entities_bert = extract_entities_bert(cleaned_text)

    # Détection des événements via le titre
    raw_events = traitement_titre(titre)

    # Vérification et formatage des événements détectés
    event_entities = []
    for event in raw_events:
        if isinstance(event, str) and event.strip():
            event_entities.append((event.strip(), date_article))  # Ajouter avec la date
    
    merged_entities = merge_entities([entities_spacy, entities_stanza, entities_bert])
    filtered_entities = filter_entities(merged_entities)

    personnes = [entite[0] for entite in filtered_entities if isinstance(entite, tuple) and entite[1] == 'PERSON']
    lieux = [entite[0] for entite in filtered_entities if isinstance(entite, tuple) and entite[1] == 'LOCATION']
    organisations = [entite[0] for entite in filtered_entities if isinstance(entite, tuple) and entite[1] == 'ORGANIZATION']
    
    return {
        'article_id': article_id,
        'personnes': personnes,
        'lieux': lieux,
        'organisations': organisations,
        'evenements': event_entities  # Evénements [(nom, date)]
    }

def enregistrer_entites(entites, article_id, table_name, include_date=False):
    """Enregistre les entités dans la table spécifiée dans Supabase."""
    count = 0
    for entite in entites:
        if count >= 10:  
            break
        
        # Vérification de la structure des données
        if include_date:  
            if isinstance(entite, tuple) and len(entite) == 2:
                nom, date_article = entite
                if not date_article:  
                    continue  # Ne pas insérer si la date est invalide
                data = {
                    "nom": nom,
                    "article_id": article_id,
                    "date": date_article  # Déjà formaté en ISO 8601
                }
            else:
                continue
        else:
            nom = entite
            data = {
                "nom": nom,
                "article_id": article_id
            }
        
        print(f"📌 Insertion dans {table_name} : {data}")

        response = supabase.table(table_name).insert(data).execute()

        if response and hasattr(response, 'status_code') and response.status_code == 201:
            print(f"✅ Entité '{nom}' insérée avec succès dans {table_name}.")

        count += 1

def traiter_documents():
    batch_size = 300
    delay= 0.5
    skip = 0

    while True:
        batch = list(collection.find().skip(skip).limit(batch_size))
        
        if not batch:
            break

        for doc in batch:
            processed_data = process_document(doc)
            if processed_data:
                article_id = processed_data["article_id"]

                # Enregistrer les entités dans les bonnes tables
                enregistrer_entites(processed_data["personnes"], article_id, "entite_fr_pers")
                enregistrer_entites(processed_data["lieux"], article_id, "entite_fr_loc")
                enregistrer_entites(processed_data["organisations"], article_id, "entite_fr_org")
                enregistrer_entites(processed_data["evenements"], article_id, "entite_fr_event", include_date=True)

      # Pause pour éviter la surcharge
        print(f"Pausing for {delay} seconds...")
        time.sleep(delay)
        
        print(f"✅ Traitement terminé pour {len(batch)} articles.")
        
        skip += batch_size


if __name__ == "__main__":
    print("🔍 Démarrage du traitement des articles...")
    traiter_documents()
    print("🎉 Traitement terminé !")
