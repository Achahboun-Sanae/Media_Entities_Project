import requests
from bs4 import BeautifulSoup
import time
import random
import sys
import os
from datetime import datetime
import re

# Ajout du chemin pour importer les modules du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import de la connexion MongoDB
from config.mongo_atlass import get_mongo_atlass_collection  
collection = get_mongo_atlass_collection("articles_ar")

# Headers pour éviter d'être bloqué
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Catégories à scraper
CATEGORIES = ["politic", "economy", "national", "sport", "world", "health", "technology", "religion"]

def get_article_urls():
    """Scrape tous les articles disponibles dans chaque catégorie"""
    base_url = "https://www.akhbarona.com"
    article_urls = set()  # Utiliser un set pour éviter les doublons

    for category in CATEGORIES:
        page = 1
        while True:
            url = f"{base_url}/{category}/index.{page}.html"
            print(f"🔍 Scraping {url}...")

            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                if response.status_code == 404:
                    print(f"⚠ 404 - Fin des pages pour {category}, passage à la suivante.")
                    break
                if response.status_code != 200:
                    print(f"⚠ Erreur {response.status_code}, nouvelle tentative dans 5 secondes...")
                    time.sleep(5)
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                articles = soup.find_all("a", href=True)

                found = 0
                for article in articles:
                    href = article["href"]
                    if "/articles/" in href or any(cat in href for cat in CATEGORIES):
                        full_url = base_url + href if href.startswith("/") else href
                        if full_url not in article_urls:
                            article_urls.add(full_url)
                            found += 1

                if found == 0:
                    print(f"⚠ Aucun article trouvé sur {url}, fin de la catégorie.")
                    break  # Passer à la prochaine catégorie si aucune URL trouvée

                page += 1
                time.sleep(random.uniform(1, 3))

            except Exception as e:
                print(f"❌ Erreur lors du scraping de {url} : {e}")
                time.sleep(5)

    return list(article_urls)

def scrape_article(url):
    """Récupère les informations détaillées d'un article"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 404:
            print(f"⚠ Article non trouvé : {url}")
            return None
        if response.status_code != 200:
            print(f"⚠ Erreur {response.status_code} pour {url}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        titre_tag = soup.find("h1", class_="text-end artical-content-heads lc-fs24")
        titre = titre_tag.text.strip() if titre_tag else "Titre inconnu"

        contenu_div = soup.find("div", class_="bodystr")
        contenu_paragraphs = [p.text.strip() for p in contenu_div.find_all("p")] if contenu_div else []
        
        if contenu_paragraphs and "أخبارنا المغربية" in contenu_paragraphs[0]:
            contenu_paragraphs.pop(0)  # Supprimer l'auteur du début du contenu
        
        contenu = " ".join(contenu_paragraphs) if contenu_paragraphs else "Contenu non disponible"

        categorie_tag = soup.find("span", class_="ms-2")
        categorie = categorie_tag.text.strip() if categorie_tag else "Catégorie inconnue"

        date_tag = soup.find("span", class_="story_date")
        date_publication = date_tag.text.strip() if date_tag else "Date inconnue"

        auteur_tag = soup.find("h4", class_="mb-3 lc-clr1")
        auteur = auteur_tag.text.strip() if auteur_tag else "Auteur inconnu"

        # Vérifier si l'article existe déjà dans MongoDB
        if collection.find_one({"url": url}):
            print(f"⏭ Article déjà existant : {url}")
            return None

        return {
            "url": url,
            "titre": titre,
            "categorie": categorie,
            "date": date_publication,
            "auteur": auteur,
            "contenu": contenu,
            "source": "Akhbarona",
        }

    except Exception as e:
        print(f"❌ Erreur lors du scraping de l'article {url} : {e}")
        return None

def main():
    """Exécute le scraping et stocke les données dans MongoDB"""
    print("🚀 Début du scraping...")
    article_urls = get_article_urls()
    
    if not article_urls:
        print("⚠ Aucun article trouvé. Fin du programme.")
        return

    articles = []
    for i, url in enumerate(article_urls, 1):
        print(f"📄 ({i}/{len(article_urls)}) Scraping article : {url}")
        article = scrape_article(url)
        if article:
            articles.append(article)

        # Enregistrer en base de données par lots de 50 articles
        if len(articles) >= 50:
            print(f"💾 Enregistrement de {len(articles)} articles dans MongoDB...")
            collection.insert_many(articles)
            articles = []

        time.sleep(random.uniform(1, 3))

    # Insérer les derniers articles restants
    if articles:
        print(f"💾 Enregistrement final de {len(articles)} articles dans MongoDB...")
        collection.insert_many(articles)

    print("✅ Scraping terminé avec succès !")

if __name__ == "__main__":
    main()