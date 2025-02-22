import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
import random  
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.mongo_atlass import get_mongo_atlass_collection  
collection = get_mongo_atlass_collection("articles_fr")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Liste des catégories principales pour le scraping
CATEGORIES = {
    "politique": [],
    "economie": [],
    "societe": [],
    "monde": [],
    "culture": [],
    "medias": [],
    "people": [],
    "lifestyle": [],
    "tourisme": []
}
    

def get_articles_from_page(category, subcategory, page):
    url = f"https://fr.le360.ma/{category}/" + (f"{subcategory}/?page={page}" if subcategory else f"?page={page}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion : {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []

    for article in soup.find_all('div', class_='article-list--headline-container'):
        title_tag = article.find('a')
        if title_tag:
            title = title_tag.text.strip()
            link = title_tag['href']
            if link.startswith("/"):
                link = f"https://fr.le360.ma{link}"
            # Vérifier si l'article est déjà dans la base avant de l'ajouter
            if not collection.find_one({"url": link}):
                articles.append({'title': title, 'link': link, 'category': category, 'subcategory': subcategory})
    
    return articles

def scrape_and_save_articles(categories, max_articles_per_category=5000):
    all_articles = []

    for category, subcategories in categories.items():
        print(f"🔍 Scraping catégorie : {category}...")

        for subcategory in ([None] if not subcategories else subcategories):
            print(f"➡️ Sous-catégorie : {subcategory if subcategory else 'Général'}")
            page = 1
            category_articles = []

            while len(category_articles) < max_articles_per_category:
                articles = get_articles_from_page(category, subcategory, page)
                if not articles:
                    print(f"⚠️ Fin des articles pour {category}/{subcategory} à la page {page}.")
                    break

                category_articles.extend(articles)
                print(f"📄 {category.upper()} {f'- {subcategory.upper()}' if subcategory else ''} - Page {page}, {len(articles)} articles ajoutés. Total: {len(category_articles)} articles.")

                if len(category_articles) >= max_articles_per_category:
                    break

                page += 1
                time.sleep(random.uniform(1, 3))  

            all_articles.extend(category_articles)

    for article in all_articles:
        url = article['link']
        title = article['title']
        category = article['category']

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            titre_tag = soup.find("h1", class_="article-page-header")
            titre = titre_tag.text.strip() if titre_tag else title

            contenu_div = soup.find("article", class_="default__ArticleBody-sc-10mj2vp-2 NypNt article-body-wrapper")
            contenu = " ".join([p.text.strip() for p in contenu_div.find_all("p")]) if contenu_div else "Contenu non disponible"

            # Extraction de la date de publication
            date_tag = soup.find("div", class_="article-main-information-subheadline-date article-body-subheadline-date")
            date_publication = date_tag.text.strip() if date_tag else "Date non disponible"

            # Extraction de l'auteur
            auteur_tag = soup.find("a", class_="article-main-information-credits-bold href")
            auteur = auteur_tag.text.strip() if auteur_tag else "Le360"

            category_tag = soup.find("a", class_="overline-link")
            categorie = category_tag.text.strip() if category_tag else "Catégorie non disponible"

            article_data = {
                "url": url,
                "titre": titre,
                "auteur": auteur,
                "contenu": contenu,
                "source": "Le360_fr",
                "categorie": categorie,
                "date": date_publication
            }
            collection.insert_one(article_data)
            print(f"💾 Article enregistré : {titre} | ✍ Auteur : {auteur} | 📅 Date : {date_publication}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur HTTP sur {url}: {e}")
        except Exception as e:
            print(f"⚠ Erreur lors du scraping de {url}: {e}")

    print(f"✅ Scraping terminé. {len(all_articles)} nouveaux articles enregistrés.")

if __name__ == "__main__":
    scrape_and_save_articles(CATEGORIES, max_articles_per_category=5000)
