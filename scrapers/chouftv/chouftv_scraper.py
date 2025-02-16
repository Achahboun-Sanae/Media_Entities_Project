import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
import random
import sys
import os

# Ajouter le répertoire racine du projet au chemin d'accès pour permettre les imports personnalisés
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.mongodb import get_mongo_collection  # Import de la fonction pour récupérer la collection MongoDB

# Connexion à la collection MongoDB "articles_fr"
collection = get_mongo_collection("articles_fr")

# Headers pour éviter d'être bloqué
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Fonction pour récupérer les URLs des articles
def get_article_urls(max_articles=5120):
    base_url = "https://chouftv.ma/press/page/"
    article_urls = set()
    page = 1

    while len(article_urls) < max_articles:
        url = f"{base_url}{page}"
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} en accédant à {url}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)

        for link in links:
            href = link["href"]
            if "/press/" in href and href not in article_urls:
                article_urls.add(href)

        print(f"📄 Page {page} scannée, {len(article_urls)} articles trouvés.")
        page += 1

        time.sleep(random.uniform(1, 3))  # Pause aléatoire pour éviter le bannissement

        if len(article_urls) >= max_articles:
            break

    return list(article_urls)[:max_articles]


# Fonction pour scraper un article
def scrape_article(url):
    try:
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} sur {url}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Titre
        titre_tag = soup.find("h1", class_="title-full-content")
        titre = titre_tag.text.strip() if titre_tag else "Titre inconnu"

        # Contenu
        contenu_div = soup.find("div", class_="full-content")
        contenu = " ".join([p.text.strip() for p in contenu_div.find_all("p")]) if contenu_div else "Contenu non disponible"

        # Vérification de doublon
        if collection.find_one({"url": url}):
            print(f"⚠ Article déjà enregistré : {titre}")
            return None

        # Stocker l'article
        return {
            "url": url,
            "titre": titre,
            "auteur": "Chouf TV MA",
            "contenu": contenu,
            "source": "Chouf TV"
        }

    except Exception as e:
        print(f"⚠ Erreur lors du scraping de {url}: {e}")
        return None


# Récupérer les URLs des articles
article_urls = get_article_urls(5000)
print(f"✅ {len(article_urls)} articles trouvés. Début du scraping...")

# Scraper chaque article
articles = []
for i, url in enumerate(article_urls, 1):
    article = scrape_article(url)
    if article:
        articles.append(article)

    # Insérer dans MongoDB par lots de 100
    if len(articles) >= 100:
        collection.insert_many(articles)
        print(f"💾 {len(articles)} articles enregistrés dans MongoDB.")
        articles = []  # Réinitialiser la liste

    # Pause aléatoire pour éviter de se faire bloquer
    time.sleep(random.uniform(1, 3))

# Insérer les derniers articles restants
if articles:
    collection.insert_many(articles)
    print(f"💾 {len(articles)} derniers articles enregistrés dans MongoDB.")

print("✅ 📂 Tous les articles sont enregistrés !")
