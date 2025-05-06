# connect_mongo
from config.mongo_atlass import get_mongo_atlass_collection

def connect_mongo(collection_name):
    """Récupérer une collection spécifique depuis MongoDB Atlas."""
    return get_mongo_atlass_collection(collection_name)
