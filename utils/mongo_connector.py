from pymongo import MongoClient
from config.settings import MONGO_URI, DATABASE_NAME, COLLECTION_NAME

def get_mongo_client():
    """Retourne une instance de connexion à MongoDB."""
    return MongoClient(MONGO_URI)

def get_database():
    """Retourne la base de données partagée."""
    client = get_mongo_client()
    return client[DATABASE_NAME]



def save_to_mongo(article):
    """
    Sauvegarde un article dans MongoDB.
    :param article: Un dictionnaire contenant les détails de l'article.
    """
    try:
        # Connexion à MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        # Vérifier si l'article existe déjà (basé sur le lien)
        if collection.find_one({"link": article["link"]}):
            print(f"Article déjà existant : {article['link']}")
        else:
            # Insérer l'article dans la collection
            collection.insert_one(article)
            print(f"Article sauvegardé : {article['link']}")

    except Exception as e:
        print(f"Erreur lors de la sauvegarde dans MongoDB : {e}")

def find_in_mongo(query={}):
    """
    Recherche des données dans la collection "articles".
    :param query: Filtre de recherche (ex: {"source": "hespress"})
    """
    db = get_database()
    collection = db[COLLECTION_NAME]
    return list(collection.find(query))