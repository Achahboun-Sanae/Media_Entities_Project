import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from urllib.parse import urljoin
import sys
import os

# Ajouter le répertoire racine du projet au chemin d'accès pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import de la fonction pour se connecter à MongoDB
from config.mongodb import get_mongo_collection

# Connexion à MongoDB
collection = get_mongo_collection("articles_fr")

# URL de base du site
BASE_URL = "https://fr.le360.ma/"

# Fonction pour extraire les détails d'un article
def extract_article_details(article_url):
    try:
        response = requests.get(article_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extraire le titre
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "Titre non trouvé"

            # Essayer plusieurs méthodes pour extraire le contenu
            content = ""

            # 1️⃣ Essayer avec <article>
            article_body = soup.find('article')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

            # 2️⃣ Essayer avec <div class="article-content">
            if not content:
                alt_body = soup.find('div', class_="article-content")
                if alt_body:
                    paragraphs = alt_body.find_all('p')
                    content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

            # 3️⃣ Essayer avec d'autres balises si toujours vide
            if not content:
                all_paragraphs = soup.find_all('p')
                content = "\n".join([p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True)])

            return {
                "titre": title,
                "contenu": content if content else "Contenu non récupéré",
                "url": article_url,
                "source": "Le360",
                "auteur": "Le360"
            }
        else:
            print(f"❌ Erreur: Impossible d'accéder à {article_url} - Code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erreur lors de la récupération de l'article {article_url}: {e}")
        return None

# Fonction pour scraper les liens des articles
def scrape_article_links():
    article_links = set()
    page_number = 1

    while len(article_links) < 500:  # Scraper 500 articles
        page_url = f"{BASE_URL}?page={page_number}"
        print(f"🔍 Scraping de la page : {page_url}")

        try:
            response = requests.get(page_url, timeout=10)
            if response.status_code != 200:
                print(f"❌ Erreur: Impossible d'accéder à {page_url} - Code {response.status_code}")
                break

            soup = BeautifulSoup(response.content, 'html.parser')

            # Trouver les liens des articles
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/culture/') and len(article_links) < 500:
                    full_url = urljoin(BASE_URL, href)
                    article_links.add(full_url)

            page_number += 1

        except requests.exceptions.RequestException as e:
            print(f"🚨 Erreur lors de la récupération de la page {page_url}: {e}")
            break

    return list(article_links)

# Fonction principale
def main():
    article_links = scrape_article_links()
    print(f"📌 Nombre total de liens d'articles trouvés : {len(article_links)}")

    for link in article_links:
        article_details = extract_article_details(link)
        if article_details:
            collection.insert_one(article_details)
            print(f"✅ Article inséré : {article_details['titre']}")

    print("🎯 Scraping terminé. Les articles ont été stockés dans MongoDB.")

# Exécuter le script
if __name__ == "__main__":
    main()
