import sys
import os
from pymongo import MongoClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase

# Fonction pour récupérer tous les article_id d'une table Supabase donnée
def get_all_article_ids_from_supabase(table_name, column_name="article_id", page_size=1000):
    all_ids = set()
    offset = 0

    while True:
        try:
            response = supabase.table(table_name).select(column_name).range(offset, offset + page_size - 1).execute()
            if response.error:
                print(f"Erreur lors de la récupération des données de la table {table_name}: {response.error}")
                break
            data = response.data
            if not data:
                break
            all_ids.update(row[column_name] for row in data)
            offset += page_size
        except Exception as e:
            print(f"Erreur lors de l'appel à Supabase pour la table {table_name}: {e}")
            break

    return all_ids

def detect_missing_article_ids():
    # Étape 1 : Récupérer les article_id de MongoDB
    try:
        collection = get_mongo_atlass_collection("articles_fr")
        mongo_article_ids = set(
            str(doc["_id"]) for doc in collection.find({"_id": {"$exists": True}}, {"_id": 1})
        )
        print(f"Nombre total d'_id récupérés depuis MongoDB : {len(mongo_article_ids)}")
    except Exception as e:
        print(f"Erreur lors de la récupération des article_id depuis MongoDB: {e}")
        return

    # Étape 2 : Récupérer les article_id de Supabase depuis la table relations_en
    supabase_article_ids = set()

    try:
        print(f"Récupération des article_id depuis la table relations_fr...")
        table_ids = get_all_article_ids_from_supabase("relations_fr")
        print(f"Nombre d'_id récupérés depuis la table relations_fr : {len(table_ids)}")
        supabase_article_ids.update(table_ids)
    except Exception as e:
        print(f"Erreur lors de la récupération des article_id depuis Supabase: {e}")
        return

    # Étape 3 : Identifier les article_id manquants (c'est-à-dire ceux dans MongoDB mais pas dans Supabase)
    missing_article_ids = mongo_article_ids - supabase_article_ids
    print(f"Nombre d'_id présents dans MongoDB mais absents de Supabase : {len(missing_article_ids)}")

    # Enregistrer les article_id manquants dans une liste
    missing_article_ids_list = list(missing_article_ids)

    # Afficher les article_id manquants
    if missing_article_ids_list:
        print("Les article_id manquants sont :")
        for aid in missing_article_ids_list:
            print(aid)
    else:
        print("Aucun article_id manquant trouvé.")

    # Sauvegarder les article_id manquants dans un fichier texte au format souhaité (avec des virgules)
    try:
        with open("missing_article_ids.txt", "w") as file:
            for aid in missing_article_ids_list:
                file.write(f"('{aid}'),\n")  # Format avec des guillemets simples et une virgule à la fin
        print("Les article_id manquants ont été enregistrés dans 'missing_article_ids.txt'")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des article_id manquants dans un fichier : {e}")

if __name__ == "__main__":
    detect_missing_article_ids()
