import requests
from bs4 import BeautifulSoup  
from datetime import datetime
from utils.mongo_connector import save_to_mongo

# URL de la page d'accueil de Hespress
HESPRESS_URL = "https://www.hespress.com/"

def scrape_hespress():
    """
    Scraper pour extraire les articles de Hespress.
    """
    try:
        # 1. Récupérer le contenu de la page
        response = requests.get(HESPRESS_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()  # Vérifier que la requête a réussi

        # 2. Parser le contenu HTML
        soup = BeautifulSoup(response.text, "html.parser")  # Utilisation de BeautifulSoup

        # ... (le reste du code)
    except Exception as e:
        print(f"Erreur lors du scraping de Hespress : {e}")