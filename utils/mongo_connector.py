from pymongo import MongoClient
from config.settings import MONGO_URI, DATABASE_NAME, COLLECTION_NAME

def get_mongo_client():
    """Retourne une instance de connexion à MongoDB."""
    return MongoClient(MONGO_URI)

def get_database():
    """Retourne la base de données partagée."""
    client = get_mongo_client()
    return client[DATABASE_NAME]

def save_to_mongo(data):
    """
    Sauvegarde des données dans la collection "articles".
    :param data: Données à sauvegarder (liste de dictionnaires)
    """
    db = get_database()
    collection = db[COLLECTION_NAME]
    return collection.insert_many(data)

def find_in_mongo(query={}):
    """
    Recherche des données dans la collection "articles".
    :param query: Filtre de recherche (ex: {"source": "hespress"})
    """
    db = get_database()
    collection = db[COLLECTION_NAME]
    return list(collection.find(query))