import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
import random
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Ajout du chemin du dossier parent pour l'importation des modules personnalisés
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.mongo_atlass import get_mongo_atlass_collection

# Connexion à la collection MongoDB pour stocker les articles
collection = get_mongo_atlass_collection("articles_ar")

# Définition de l'en-tête HTTP pour éviter le blocage par le site web
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, comme Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_article_urls(max_articles=6000):
    """
    Récupère les URLs des articles en parcourant les pages d'index.
    
    :param max_articles: Nombre maximal d'articles à récupérer.
    :return: Liste des URLs des articles trouvés.
    """
    base_url = "https://chouftv.ma/press/page/"
    article_urls = set()
    page = 1

    while len(article_urls) < max_articles:
        response = requests.get(f"{base_url}{page}", headers=HEADERS)
        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} sur {base_url}{page}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extraction des liens vers les articles
        article_urls.update(
            {link["href"] for link in soup.find_all("a", href=True) if "/press/" in link["href"]}
        )
        
        print(f"📄 Page {page} scannée, {len(article_urls)} articles trouvés.")
        page += 1

        if len(article_urls) >= max_articles:
            break
    
    return list(article_urls)[:max_articles]

def scrape_article(url):
    """
    Extrait les informations d'un article donné par son URL.
    
    :param url: URL de l'article à scraper.
    :return: Dictionnaire contenant les informations de l'article ou None en cas d'échec.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extraction du titre
        titre = soup.select_one("h1.title-full-content")
        titre = titre.text.strip() if titre else "Titre inconnu"
        
        # Extraction du contenu de l'article
        contenu_div = soup.select_one("div.full-content")
        contenu = " ".join(p.text.strip() for p in contenu_div.find_all("p")) if contenu_div else "Contenu non disponible"
        
        # Vérification si le contenu est vide ou indisponible
        if contenu in ["", "Contenu non disponible"]:
            return None
        
        # Extraction de la date
        date_tag = soup.select_one("div.left-info time")
        date_text = date_tag.text.strip() if date_tag else "Date inconnue"
        try:
            date_formatee = datetime.strptime(date_text, "%A %d %B %Y | %H:%M").strftime("%d %B %Y %H:%M")
        except ValueError:
            date_formatee = date_text
        
        # Extraction de la catégorie
        categorie = soup.select_one("section > ul.navbar-head > li:nth-child(2) > a")
        categorie = categorie.text.strip() if categorie else "Catégorie inconnue"
        
        # Vérifier si l'article existe déjà dans la base de données
        if collection.find_one({"url": url}):
            return None
        
        return {
            "url": url,
            "titre": titre,
            "auteur": "Chouf TV MA",
            "date": date_formatee,
            "categorie": categorie,
            "contenu": contenu,
            "source": "Chouf TV"
        }
    except Exception:
        return None

def main():
    """
    Fonction principale qui exécute le scraping et stocke les articles dans MongoDB.
    """
    article_urls = get_article_urls(6000)
    print(f"✅ {len(article_urls)} articles trouvés. Début du scraping...")
    
    articles = []
    
    # Utilisation d'un ThreadPoolExecutor pour accélérer le scraping
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(scrape_article, article_urls))
        articles = [article for article in results if article]
    
    # Enregistrement des articles dans MongoDB
    if articles:
        collection.insert_many(articles)
        print(f"💾 {len(articles)} articles enregistrés dans MongoDB.")
    print("✅ 📂 Tous les articles sont enregistrés !")

if __name__ == "__main__":
    main()
