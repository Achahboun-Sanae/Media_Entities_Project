import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

# Ajouter le répertoire racine au PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scrapers.hespress.hespress_parser import clean_date
from utils.mongo_connector import save_to_mongo
from config.settings import MONGO_URI, DATABASE_NAME, COLLECTION_NAME

# URL de la page d'accueil de Hespress
HESPRESS_URL = "https://www.hespress.com/"

def parse_article_page(article_url):
    """
    Extrait les détails d'un article à partir de son URL.
    :param article_url: L'URL de l'article.
    :return: Un dictionnaire contenant les détails de l'article.
    """
    try:
        # 1. Récupérer le contenu de la page de l'article
        response = requests.get(article_url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        # 2. Parser le contenu HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # 3. Extraire les détails de l'article
        title = soup.find("h1", class_="post-title").text.strip()
        content = " ".join(p.text.strip() for p in soup.find("div", class_="article-content").find_all("p"))
        date_span = soup.find("span", class_="date-post")
        date = clean_date(date_span.text.strip()) if date_span else datetime.now().strftime("%Y-%m-%d")

        # 4. Retourner les données structurées
        return {
            "titre": title,
            "contenu": content,
            "source": "hespress",
            "date": date,
            "link": article_url
        }

    except Exception as e:
        print(f"Erreur lors de l'extraction de l'article {article_url} : {e}")
        return None

def scrape_hespress():
    """
    Scraper pour extraire les articles de Hespress.
    """
    try:
        articles_collected = 0  # Compteur d'articles collectés
        page_number = 1  # Commencer à la première page

        while articles_collected < 5000:
            # Construire l'URL de la page
            page_url = f"{HESPRESS_URL}/page/{page_number}"
            print(f"Scraping de la page {page_number} : {page_url}")

            # 1. Récupérer le contenu de la page
            response = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()  # Vérifier que la requête a réussi

            # 2. Parser le contenu HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # 3. Extraire les liens des articles
            articles = soup.find_all("div", class_="post-content")  # Adaptez ce sélecteur à la structure de Hespress

            for article in articles:
                # Extraire le lien de l'article
                article_link = article.find("a")["href"]

                # Extraire les détails de l'article
                article_details = parse_article_page(article_link)

                # Sauvegarder l'article dans MongoDB
                if article_details:
                    save_to_mongo(article_details)
                    articles_collected += 1
                    print(f"Article {articles_collected} sauvegardé : {article_details['titre']}")

                    # Arrêter si on a atteint 5 000 articles
                    if articles_collected >= 5000:
                        break

            # Passer à la page suivante
            page_number += 1

    except Exception as e:
        print(f"Erreur lors du scraping de Hespress : {e}")

if __name__ == "__main__":
    scrape_hespress()