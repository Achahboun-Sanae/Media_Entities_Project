import requests
from bs4 import BeautifulSoup
import time
import json
from .le360_parser import parse_le360_articles

BASE_URL = "https://fr.le360.ma/page/"

def scrape_le360(pages=200):
    all_articles = []

    for page_num in range(1, pages + 1):
        url = f"{BASE_URL}{page_num}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Erreur lors de l'accès à la page {page_num}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("article")  # Adapté à la structure du site
        
        for article in articles:
            title = article.find("h2").text.strip() if article.find("h2") else "Titre manquant"
            link = article.find("a")["href"] if article.find("a") else "Lien manquant"
            date = article.find("time").text.strip() if article.find("time") else "Date manquante"
            category = article.find("span", class_="category").text.strip() if article.find("span", class_="category") else "Catégorie manquante"
            summary = article.find("p").text.strip() if article.find("p") else "Résumé manquant"
            
            # Ajouter des informations supplémentaires (ex. auteur)
            author = article.find("span", class_="author").text.strip() if article.find("span", class_="author") else "Auteur manquant"
            
            all_articles.append({
                "title": title,
                "link": link,
                "date": date,
                "category": category,
                "summary": summary,
                "author": author
            })

        time.sleep(2)  # Pour éviter de surcharger le serveur

    return all_articles

if __name__ == "__main__":
    articles = scrape_le360(pages=200)  # Pour récupérer environ 5000 articles
    with open("le360_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

