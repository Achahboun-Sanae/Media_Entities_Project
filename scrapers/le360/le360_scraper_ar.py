import requests
from bs4 import BeautifulSoup
import json
import time
import random

# Fonction pour récupérer les articles d'une page spécifique
def get_articles_from_page(category, page):
    url = f"https://ar.le360.ma/{category}/?page={page}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Erreur {response.status_code} lors de l'accès à {url}")
            return []
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
                link = f"https://ar.le360.ma{link}"
            articles.append({'title': title, 'link': link})
    
    return articles

# Fonction principale pour récupérer les articles d'une liste de catégories
def scrape_le360(categories, max_articles_per_category=5000):
    all_articles = []
    
    for category in categories:
        print(f"🔍 Scraping catégorie: {category}...")
        page = 1
        category_articles = []

        while len(category_articles) < max_articles_per_category:
            articles = get_articles_from_page(category, page)
            if not articles:
                print(f"⚠️ Aucun nouvel article trouvé sur la page {page} de {category}. Arrêt.")
                break
            
            category_articles.extend(articles)
            print(f"📄 {category.upper()} - Page {page} scannée, {len(articles)} articles trouvés. Total: {len(category_articles)} articles.")
            
            if len(category_articles) >= max_articles_per_category:
                break

            page += 1
            time.sleep(random.uniform(1, 3))  # Pause aléatoire pour éviter d'être bloqué
        
        all_articles.extend(category_articles)

    return all_articles

if __name__ == "__main__":
    categories = ["societe", "politique", "economie", "culture", "media", "sport"]
    articles = scrape_le360(categories, max_articles_per_category=5000)
    
    with open("le360_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Scraping terminé. {len(articles)} articles enregistrés dans 'le360_articles.json'.")
