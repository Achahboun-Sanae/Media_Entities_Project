import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
import random

# Configuration MongoDB
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "medias_maroc"
COLLECTION_NAME = "articles"

# Connexion à MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Headers pour éviter d'être bloqué
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Catégories à scraper
CATEGORIES = ["national"]

# Fonction pour récupérer les URLs des articles de toutes les pages
def get_article_urls():
    base_url = "https://www.akhbarona.com"
    article_urls = set()
    
    for category in CATEGORIES:
        page = 1
        
        while True:  # Continue jusqu'à ce que la page soit introuvable
            url = f"{base_url}/{category}/index.{page}.html"
            print(f"🔍 Scraping {url}...")

            response = requests.get(url, headers=HEADERS)

            if response.status_code == 404:
                print(f"⚠️ Page {page} pour {category.upper()} introuvable (404), arrêt.")
                break  # Arrêter cette catégorie

            if response.status_code != 200:
                print(f"❌ Erreur {response.status_code} sur {url}, on passe à la suivante.")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # Trouver tous les liens des articles
            articles = soup.find_all("a", href=True)
            found = 0  # Compteur d'articles trouvés

            for article in articles:
                href = article["href"]

                # Vérifier si le lien correspond à un article valide
                if "/articles/" in href or any(cat in href for cat in CATEGORIES):
                    full_url = "https://www.akhbarona.com" + href if href.startswith("/") else href
                    if full_url not in article_urls:
                        article_urls.add(full_url)
                        found += 1

            print(f"📄 {category.upper()} - Page {page} scannée, {found} nouveaux articles trouvés. Total: {len(article_urls)} articles.")

            # Si aucune nouvelle URL trouvée, c'est peut-être la fin de la catégorie
            if found == 0:
                print(f"🚫 Aucune nouvelle URL trouvée sur {category.upper()} page {page}, arrêt de la catégorie.")
                break

            page += 1
            time.sleep(random.uniform(1, 3))  # Pause aléatoire pour éviter de se faire bloquer

    return list(article_urls)

# Fonction pour scraper un article
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

        # Titre
        titre_tag = soup.find("h1", class_="artical-content-heads")
        titre = titre_tag.text.strip() if titre_tag else "Titre inconnu"

        # Contenu
        contenu_div = soup.find("div", class_="bodystr")
        contenu = " ".join([p.text.strip() for p in contenu_div.find_all("p")]) if contenu_div else "Contenu non disponible"

        # Vérifier si l'article est déjà en base de données
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


# Récupérer les URLs des articles
article_urls = get_article_urls()
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
