import requests
from bs4 import BeautifulSoup
import json

BASE_URL = "https://fr.le360.ma/page/"

def scrape_le360(pages=200):  # Scraper un nombre élevé de pages pour atteindre 5000 articles
    extracted_data = []
    
    for page_num in range(1, pages + 1):
        url = BASE_URL + str(page_num)
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Erreur lors de l'accès à la page {page_num}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("article")  # Adapter selon la structure du site
        
        for article in articles:
            title = article.find("h2").text.strip() if article.find("h2") else "Titre manquant"
            link = article.find("a")["href"] if article.find("a") else "Lien manquant"
            date = article.find("time").text.strip() if article.find("time") else "Date manquante"
            category = article.find("span", class_="category").text.strip() if article.find("span", class_="category") else "Catégorie manquante"
            summary = article.find("p").text.strip() if article.find("p") else "Résumé manquant"
            
            # Ajoute toutes les entités trouvées
            extracted_data.append({
                "title": title,
                "link": link,
                "date": date,
                "category": category,
                "summary": summary
            })

        # Pause pour éviter de surcharger le serveur
        time.sleep(2)

    return extracted_data

if __name__ == "__main__":
    articles = scrape_le360(pages=200)  # Scraper 200 pages pour atteindre environ 5000 articles
    with open("le360_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)
