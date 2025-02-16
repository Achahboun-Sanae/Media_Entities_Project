# config/mongodb.py
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "medias_maroc"

def get_mongo_collection(collection_name):
    """Retourne la collection MongoDB demandée."""
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    return db[collection_name]
