import sys
import os
import time
import json
from itertools import combinations
from bson import ObjectId
import datetime
from transformers import BertTokenizer, BertForSequenceClassification, pipeline

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase

# Chargement du modèle BERT
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertForSequenceClassification.from_pretrained("bert-base-uncased")

# Utilisation de la pipeline pour la classification zero-shot
relation_extractor = pipeline("zero-shot-classification", model=model, tokenizer=tokenizer)

# Connexion à MongoDB
collection = get_mongo_atlass_collection("articles_eng")

# Mapping des catégories
category_mapping = {
    'personnes': 'PER',
    'lieux': 'LOC',
    'organisations': 'ORG',
    'evenements': 'EVENT'
}

# Fonction pour récupérer les entités depuis Supabase
def get_entites_from_supabase(article_id):
    entity_categories = {
        "personnes": "entite_en_pers",
        "lieux": "entite_en_loc",
        "organisations": "entite_en_org",
        "evenements": "entite_en_event",
    }
    entities = {}
    for cat, table in entity_categories.items():
        try:
            resp = (
                supabase
                .table(table)
                .select("nom")
                .eq("article_id", article_id)
                .execute()
            )
            entities[cat] = {e["nom"] for e in resp.data if "nom" in e}
        except Exception as e:
            print(f"⚠️ Erreur Supabase ({table}): {e}")
            entities[cat] = set()
    return entities

# Fonction pour détecter la relation entre deux entités en utilisant BERT
def detecter_relation(text, span1, span2):
    # Créer une phrase pour BERT en combinant les entités
    combined_text = f"{span1} [SEP] {span2}"
    
    # Utiliser BERT pour prédire la relation entre les entités
    result = relation_extractor(combined_text, candidate_labels=["related to", "works for", "located at", "part of", "owned by"])
    
    # Obtenir la relation avec le score le plus élevé
    relation = result["labels"][0] if result["scores"][0] > 0.5 else "related to"  # Valeur par défaut si pas assez confiant

    # Affichage pour débogage
    print(f"Relation entre {span1} et {span2}: {relation}")
    
    return relation

# Fonction principale pour extraire les entités et relations
def extraire_entites_et_relations(article_id):
    try:
        doc_mongo = collection.find_one({"_id": ObjectId(article_id)})
    except Exception as e:
        raise ValueError(f"❌ Article introuvable en MongoDB : {e}")

    if not doc_mongo:
        raise ValueError("❌ Article introuvable en MongoDB")

    texte = f"{doc_mongo.get('titre','')} {doc_mongo.get('contenu','')}"

    entites_dict = get_entites_from_supabase(article_id)
    entites = {
        (nom, cat)
        for cat, noms in entites_dict.items()
        for nom in noms
    }

    # Récupération des champs "source" et "date"
    source_media = doc_mongo.get("source", "")
    date = doc_mongo.get("date", None)
    if isinstance(date, (datetime.datetime, datetime.date)):
        date = date.isoformat()

    relations = []
    for (nom1, cat1), (nom2, cat2) in combinations(entites, 2):
        if nom1 == nom2:
            continue

        # Les entités sont déjà extraites via Supabase, donc on ne les extrait pas de texte avec 'nlp'
        span1 = nom1
        span2 = nom2

        # Si les entités sont trop éloignées, ignorer cette paire
        if abs(texte.find(span1) - texte.find(span2)) > 15:
            continue

        rel = detecter_relation(texte, span1, span2)
        if rel:
            # Utilisation du contexte de la relation (phrase) pour `source_title`
            sentence = texte if texte.find(span1) <= texte.find(span2) else texte
            relations.append({
                "source": nom1,
                "type_source": category_mapping.get(cat1, cat1),
                "cible": nom2,
                "type_cible": category_mapping.get(cat2, cat2),
                "relation": rel,
                "source_title": sentence,  # Le contexte de la relation
                "article_id": article_id,
                "media_source": source_media,   # Média source (champ "source" de MongoDB)
                "date": date      # Date formatée en ISO
            })
    return relations

# Fonction pour enregistrer les relations dans Supabase
def enregistrer_relations_dans_supabase(relations):
    for rel in relations:
        try:
            supabase.table("relations_en").insert([{
                "nom_source": rel["source"],
                "type_source": rel["type_source"],
                "nom_cible": rel["cible"],
                "type_cible": rel["type_cible"],
                "relation": rel["relation"],
                "source_title": rel["source_title"],  # Contexte de la relation
                "article_id": rel["article_id"],
                "source": rel["media_source"],         # Champ "source" (média)
                "date": rel["date"],     # Champ "date"
            }]).execute()
            print(f"✅ Relation {rel['source']} --> {rel['cible']} enregistrée.")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'enregistrement : {e}")

# Fonction pour vérifier si des relations ont déjà été enregistrées
def relations_deja_enregistrees(article_id):
    try:
        result = supabase.table("relations_en").select("id").eq("article_id", article_id).execute()
        return bool(result.data)
    except Exception as e:
        print(f"⚠️ Erreur vérification enregistrement : {e}")
        return False

# Nouvelle fonction pour lire les IDs depuis le fichier JSON
def charger_article_ids_depuis_fichier(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [item["article_id"] for item in data if "article_id" in item]

# Fonction principale pour traiter la liste d'IDs fournie
def traiter_articles_specifiques(article_ids):
    for article_id_str in article_ids:
        try:
            doc_mongo = collection.find_one({"_id": ObjectId(article_id_str)})
            if not doc_mongo:
                print(f"❌ Article {article_id_str} introuvable")
                continue

            if relations_deja_enregistrees(article_id_str):
                print(f"✅ Relations déjà existantes pour {article_id_str}")
                continue

            print(f"🔍 Traitement de l'article {article_id_str}")
            relations = extraire_entites_et_relations(article_id_str)
            if relations:
                enregistrer_relations_dans_supabase(relations)
                print(f"✅ {len(relations)} relations enregistrées")
            else:
                print("ℹ️ Aucune relation détectée")
        except Exception as e:
            print(f"⚠️ Erreur sur l'article {article_id_str} : {str(e)}")

# Exécution principale
if __name__ == "__main__":
    print("🔍 Début du traitement des articles spécifiques...")
    chemin_fichier = "missing_article_ids.txt"  # Chemin vers votre fichier d'IDs
    article_ids = charger_article_ids_depuis_fichier(chemin_fichier)
    traiter_articles_specifiques(article_ids)
    print("🎉 Traitement terminé.")
