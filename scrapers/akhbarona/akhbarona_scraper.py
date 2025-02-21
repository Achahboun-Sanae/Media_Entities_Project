import requests
from bs4 import BeautifulSoup
import time
import random
import sys
import os

# Ajouter le répertoire racine du projet au chemin d'accès pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.mongodb import get_mongo_collection  # Importer la configuration MongoDB

# Connexion à la collection MongoDB "articles_ar"
collection = get_mongo_collection("articles_ar")

# Définition des headers pour simuler un vrai navigateur et éviter les blocages
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Liste des catégories d'articles à scraper
<<<<<<< HEAD
CATEGORIES = ["culture"]
=======
CATEGORIES = ["culture","Economy","national","world"]
>>>>>>> cb2b3da0d491cb7db20d66dc0cc93e9e30415205

# Fonction pour récupérer les URLs des articles à partir des pages de catégories
def get_article_urls():
    base_url = "https://www.akhbarona.com"
    article_urls = set()
    
    for category in CATEGORIES:
        page = 1  # Initialisation du compteur de pages
        
        while True:  # Boucle infinie, s'arrêtera si une page est introuvable
            url = f"{base_url}/{category}/index.{page}.html"
            print(f"🔍 Scraping {url}...")

            response = requests.get(url, headers=HEADERS)

            if response.status_code == 404:  # Si la page n'existe pas, arrêter le scraping de cette catégorie
                print(f"⚠️ Page {page} pour {category.upper()} introuvable (404), arrêt.")
                break

            if response.status_code != 200:  # Si une autre erreur HTTP survient
                print(f"❌ Erreur {response.status_code} sur {url}, on passe à la suivante.")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # Extraction des liens d'articles
            articles = soup.find_all("a", href=True)
            found = 0  # Compteur d'articles trouvés

            for article in articles:
                href = article["href"]

                # Vérification si l'URL correspond bien à un article
                if "/articles/" in href or any(cat in href for cat in CATEGORIES):
                    full_url = "https://www.akhbarona.com" + href if href.startswith("/") else href
                    if full_url not in article_urls:
                        article_urls.add(full_url)
                        found += 1

            print(f"📄 {category.upper()} - Page {page} scannée, {found} nouveaux articles trouvés. Total: {len(article_urls)} articles.")

            if found == 0:  # Si aucune nouvelle URL trouvée, on suppose la fin des articles
                print(f"🚫 Aucune nouvelle URL trouvée sur {category.upper()} page {page}, arrêt de la catégorie.")
                break

            page += 1  # Passer à la page suivante
            time.sleep(random.uniform(1, 3))  # Pause aléatoire pour éviter le blocage du site

    return list(article_urls)

# Fonction pour scraper le contenu d'un article
def scrape_article(url):
    try:
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 404:
            print(f"⚠ Article introuvable (404) : {url}")
            return None

        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} sur {url}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Extraction du titre de l'article
        titre_tag = soup.find("h1", class_="artical-content-heads")
        titre = titre_tag.text.strip() if titre_tag else "Titre inconnu"

        # Extraction du contenu de l'article
        contenu_div = soup.find("div", class_="bodystr")
        contenu = " ".join([p.text.strip() for p in contenu_div.find_all("p")]) if contenu_div else "Contenu non disponible"

        # Vérification si l'article est déjà enregistré dans la base de données
        if collection.find_one({"url": url}):
            print(f"⚠ Article déjà enregistré : {titre}")
            return None

        return {
            "url": url,
            "titre": titre,
            "auteur": "Akhbarona",
            "contenu": contenu,
            "source": "Akhbarona",
        }

    except Exception as e:
        print(f"⚠ Erreur lors du scraping de {url}: {e}")
        return None

# Récupération des URLs des articles
article_urls = get_article_urls()
print(f"✅ {len(article_urls)} articles trouvés. Début du scraping...")

# Scraper et stocker les articles dans MongoDB
articles = []
for i, url in enumerate(article_urls, 1):
    article = scrape_article(url)
    if article:
        articles.append(article)

    # Insérer les articles en lots de 100 pour optimiser l'accès à la base de données
    if len(articles) >= 100:
        collection.insert_many(articles)
        print(f"💾 {len(articles)} articles enregistrés dans MongoDB.")
        articles = []  # Réinitialiser la liste temporaire

    # Pause aléatoire entre les requêtes pour éviter d'être détecté comme bot
    time.sleep(random.uniform(1, 3))

# Insérer les derniers articles restants dans MongoDB
if articles:
    collection.insert_many(articles)
    print(f"💾 {len(articles)} derniers articles enregistrés dans MongoDB.")

print("✅ 📂 Tous les articles sont enregistrés !")
