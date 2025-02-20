# config/mongodb_atlass.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Charger les variables d'environnement à partir du fichier .env
load_dotenv()  
# Récupération de l'URI MongoDB depuis les variables d'environnement
MONGO_URI = os.getenv("MONGO_URI")

# Nom de la base de données utilisée
DATABASE_NAME = "medias_maroc"

def get_mongo_atlass_collection(collection_name):
    """Établit une connexion à MongoDB et retourne une collection spécifique.
    
    :param collection_name: Nom de la collection à récupérer.
    :return: Instance de la collection MongoDB."""
    
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    return db[collection_name]












