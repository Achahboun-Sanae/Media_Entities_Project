from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
from bs4 import BeautifulSoup

BASE_URL = "https://www.akhbarona.com/"

# Configurer les options pour Selenium (sans mode headless pour déboguer)
def setup_driver():
    chrome_options = Options()
    # Enlever "--headless" pour voir ce qui se passe visuellement
    # chrome_options.add_argument("--headless")  # Mode sans fenêtre (à commenter pour déboguer)
    driver = webdriver.Chrome(options=chrome_options)  # Si tu utilises un autre navigateur, adapte la ligne
    return driver

def scrape_akhbarona(pages=5):
    all_articles = []
    driver = setup_driver()

    for page_num in range(1, pages + 1):
        url = f"{BASE_URL}?page={page_num}"
        print(f"🔍 Scraping page {page_num} - {url}")

        driver.get(url)  # Ouvrir l'URL dans le navigateur Selenium

        # Augmenter l'attente pour s'assurer que la page est complètement chargée
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "news-item")))
        except:
            print(f"❌ Impossible de charger la page {page_num} correctement.")
            continue

        # Récupérer le contenu HTML une fois la page entièrement chargée
        page_html = driver.page_source

        # Extraire le contenu avec BeautifulSoup
        soup = BeautifulSoup(page_html, "html.parser")

        # Vérifier la structure HTML et extraire les articles
        articles = soup.find_all("div", class_="news-item")  # Modifier si nécessaire

        if not articles:
            print(f"⚠️ Aucun article trouvé sur la page {page_num}. Vérifie la structure HTML.")
            continue

        for article in articles:
            title_tag = article.find("h3")
            link_tag = article.find("a")
            summary_tag = article.find("p")

            title = title_tag.text.strip() if title_tag else "Titre manquant"
            link = BASE_URL + link_tag["href"] if link_tag and link_tag.has_attr("href") else "Lien manquant"
            summary = summary_tag.text.strip() if summary_tag else "Résumé manquant"

            all_articles.append({
                "title": title,
                "link": link,
                "summary": summary
            })

    driver.quit()  # Fermer le navigateur Selenium après le scraping

    # Sauvegarder les articles dans un fichier JSON
    with open("akhbarona_articles.json", "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=4)

    print(f"✅ Scraping terminé ! {len(all_articles)} articles enregistrés.")

if __name__ == "__main__":
    scrape_akhbarona(pages=5)  # Modifier le nombre de pages si nécessaire
