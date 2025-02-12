import requests
from bs4 import BeautifulSoup
import time
import json
from .akhbarona_parser import parse_akhbarona_articles

BASE_URL = "https://www.akhbarona.com/"

def scrape_akhbarona(pages=200):
    all_articles = []

    for page_num in range(1, pages + 1):
        url = f"{BASE_URL}page-{page_num}.html"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Erreur lors de l'accès à la page {page_num}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("div", class_="list-item")  # Adapter en fonction de la structure HTML
        
        for article in articles:
            title = article.find("h2").text.strip() if article.find("h2") else "Titre manquant"
            link = article.find("a")["href"] if article.find("a") else "Lien manquant"
            summary = article.find("p").text.strip() if article.find("p") else "Résumé manquant"
            
            all_articles.append({
                "title": title,
                "link": link,
                "summary": summary
            })

        time.sleep(2)  # Pour éviter d'envoyer trop de requêtes trop vite

    # Retourner les articles récupérés pour les parser
    return all_articles

if __name__ == "__main__":
    articles = scrape_akhbarona(pages=200)  # Pour récupérer environ 5000 articles
    with open("akhbarona_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)
