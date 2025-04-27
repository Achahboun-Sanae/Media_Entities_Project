import os
import sys
import re
import time
import json
from datetime import datetime
from random import uniform
from urllib.parse import urljoin
from bson import ObjectId

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# Ajouter le répertoire racine au path pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.mongo_atlass import get_mongo_atlass_collection

# Configuration
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
MAX_ARTICLES_PER_CATEGORY = 1670
SCROLL_PAUSE_TIME = 2
MAX_SCROLLS = 400
LOAD_MORE_WAIT_TIME = 5
MAX_CLICKS = 100
# Configuration du logging

class SimpleLogger:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.stats = {
            'total': 0,
            'added': 0,
            'skipped_category': 0,
            'skipped_missing': 0,
            'skipped_duplicate': 0,
            'errors': 0
        }
    
    def log(self, message, level='info'):
        if self.verbose or level in ('error', 'stats'):
            print(message)
    
    def show_stats(self):
        print("\n📊 Statistiques de scraping:")
        print(f"Total d'articles traités: {self.stats['total']}")
        print(f"Articles ajoutés: {self.stats['added']}")
        print(f"Articles ignorés (catégorie): {self.stats['skipped_category']}")
        print(f"Articles ignorés (données manquantes): {self.stats['skipped_missing']}")
        print(f"Articles ignorés (doublons): {self.stats['skipped_duplicate']}")
        print(f"Erreurs de scraping: {self.stats['errors']}")

logger = SimpleLogger(verbose=False)

def parse_hespress_date(date_str):
    """Convert English dates to datetime objects."""
    month_mapping = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    try:
        date_str = re.sub(r'^\w+\s', '', date_str).strip()
        date_part, time_part = date_str.split(' - ')
        day, month_en, year = date_part.split()
        hour, minute = map(int, time_part.split(':'))
        month = month_mapping.get(month_en.lower(), 1)
        return datetime(int(year), month, int(day), hour, minute)
    except Exception as e:
        logger.log(f"Date conversion error: {date_str} ({e})", 'error')
        return datetime.now()
    
def setup_driver():
    """Configure Selenium WebDriver avec plus d'options"""
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    options.add_argument('--enable-unsafe-swiftshader')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Pour éviter la détection comme bot
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    
    return webdriver.Chrome(options=options)

def scroll_to_bottom(driver):
    """Nouvelle version améliorée du scrolling"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    article_count = 0
    
    while scroll_attempts < MAX_SCROLLS:
        # Faire défiler jusqu'en bas
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        
        # Attendre le chargement des nouveaux éléments
        try:
            WebDriverWait(driver, LOAD_MORE_WAIT_TIME).until(
                lambda d: d.execute_script("return document.body.scrollHeight") > last_height
            )
        except:
            pass  # Pas de nouveau contenu chargé
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # Vérifier si de nouveaux articles sont apparus
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        new_count = len(soup.select('div.overlay.card'))
        
        if new_count == article_count and new_height == last_height:
            scroll_attempts += 1
            if scroll_attempts > 3:  # Arrêter après 3 tentatives sans changement
                break
        else:
            scroll_attempts = 0
        
        last_height = new_height
        article_count = new_count
        
        print(f"Articles chargés: {article_count}", end='\r')
        
        if article_count >= MAX_ARTICLES_PER_CATEGORY:
            break

def get_article_content(article_url):
    """Récupère le contenu complet d'un article"""
    try:
        time.sleep(uniform(1, 3))
        response = requests.get(article_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraction auteur
        author_element = soup.select_one('div.author-name a, span.author a')
        author = author_element.get_text(strip=True) if author_element else "Hespress"
        
        # Extraction contenu
        content_div = soup.select_one('div.article-content')
        if content_div:
            for element in content_div.select('div.article-tags, div.share-article, script, style'):
                element.decompose()
            content = ' '.join(p.get_text(strip=True) for p in content_div.select('p'))
        else:
            content = ""
        
        return {'auteur': author, 'contenu': content}
        
    except Exception as e:
        print(f"Erreur lors de la récupération de l'article {article_url}: {e}")
        return {'auteur': "Hespress", 'contenu': ""}

def scrape_hespress_category(category_url, collection):
    """Version améliorée du scraping de catégorie"""
    driver = setup_driver()
    articles_processed = 0
    
    try:
        print(f"\nScraping de la catégorie: {category_url}")
        driver.get(category_url)
        
        # Attendre que les premiers articles soient chargés
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.overlay.card')))
        
        print("Défilement pour charger plus d'articles...")
        scroll_to_bottom(driver)
        
        # Maintenant récupérer tous les articles visibles
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        article_cards = soup.select('div.overlay.card')[:MAX_ARTICLES_PER_CATEGORY]
        
        print(f"\nNombre total d'articles trouvés: {len(article_cards)}")
        
        for i, card in enumerate(article_cards, 1):
            try:
                article_data = process_article_card(card, category_url)
                
                # Insertion dans MongoDB
                result = collection.update_one(
                    {'url': article_data['url']},
                    {'$set': article_data},
                    upsert=True
                )
                
                if result.upserted_id:
                    articles_processed += 1
                    print(f"✓ [{i}/{len(article_cards)}] Nouvel article: {article_data['titre']}")
                else:
                    print(f"→ [{i}/{len(article_cards)}] Article existant: {article_data['titre']}")
                    
            except Exception as e:
                print(f"Erreur avec l'article {i}: {str(e)}")
                
    except Exception as e:
        print(f"Erreur lors du scraping: {e}")
    finally:
        driver.quit()
    
    return articles_processed

def process_article_card(card, base_url):
    """Traitement d'une carte d'article"""
    article_data = {
        '_id': ObjectId(),
        'source': 'hespress_eng',
        'date_import': datetime.now(),
        'url': None
    }
    
    # Extraction des métadonnées
    title_element = card.select_one('h3.card-title')
    article_data['titre'] = title_element.get_text(strip=True) if title_element else None
    
    link_element = card.select_one('a.stretched-link')
    if not link_element:
        raise ValueError("Pas de lien trouvé dans la carte d'article")
        
    article_url = urljoin(base_url, link_element['href'])
    article_data['url'] = article_url
    
    category_element = card.select_one('span.cat')
    article_data['categorie'] = category_element.get_text(strip=True) if category_element else None
    
    date_element = card.select_one('span.date-card small')
    if date_element:
        article_data['date'] = parse_hespress_date(date_element.get_text(strip=True))
    
    # Récupération du contenu
    content_data = get_article_content(article_url)
    article_data.update(content_data)
    
    return article_data

def load_more_sport_articles(driver):
    """Clique sur le bouton 'Afficher plus' pour la catégorie Sport"""
    click_attempts = 0
    article_count = 0
    
    while click_attempts < MAX_CLICKS:
        try:
            # Trouver le bouton "Afficher plus"
            show_more_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button.show_more'))
            )
            
            # Faire défiler jusqu'au bouton
            driver.execute_script("arguments[0].scrollIntoView();", show_more_button)
            time.sleep(1)  # Pause courte avant le clic
            
            # Cliquer avec JavaScript pour éviter les problèmes
            driver.execute_script("arguments[0].click();", show_more_button)
            
            # Attendre le chargement des nouveaux articles
            time.sleep(LOAD_MORE_WAIT_TIME)
            
            # Vérifier le nombre d'articles chargés
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            new_count = len(soup.select('div.overlay.card'))
            
            if new_count == article_count:
                click_attempts += 1
                print(f"Aucun nouvel article chargé. Tentative {click_attempts}/{MAX_CLICKS}")
            else:
                click_attempts = 0
                article_count = new_count
                print(f"Articles chargés: {article_count}")
                
            if article_count >= MAX_ARTICLES_PER_CATEGORY:
                break
                
        except Exception as e:
            click_attempts += 1
            print(f"Erreur lors du clic sur 'Afficher plus' (tentative {click_attempts}/{MAX_CLICKS}): {str(e)}")
            if click_attempts >= 3:
                break
            time.sleep(2)

def scrape_hespress_sport(sport_url, collection):
    """Scraping spécifique pour la catégorie Sport"""
    driver = setup_driver()
    articles_processed = 0
    
    try:
        print(f"\nScraping de la catégorie Sport: {sport_url}")
        driver.get(sport_url)
        
        # Attendre que les premiers articles soient chargés
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.overlay.card')))
        
        print("Chargement des articles supplémentaires...")
        load_more_sport_articles(driver)
        
        # Maintenant récupérer tous les articles visibles
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        article_cards = soup.select('div.overlay.card')[:MAX_ARTICLES_PER_CATEGORY]
        
        print(f"\nNombre total d'articles trouvés: {len(article_cards)}")
        
        for i, card in enumerate(article_cards, 1):
            try:
                article_data = process_article_card(card, sport_url)
                
                # Insertion dans MongoDB
                result = collection.update_one(
                    {'url': article_data['url']},
                    {'$set': article_data},
                    upsert=True
                )
                
                if result.upserted_id:
                    articles_processed += 1
                    print(f"✓ [{i}/{len(article_cards)}] Nouvel article: {article_data['titre']}")
                else:
                    print(f"→ [{i}/{len(article_cards)}] Article existant: {article_data['titre']}")
                    
            except Exception as e:
                print(f"Erreur avec l'article {i}: {str(e)}")
                
    except Exception as e:
        print(f"Erreur lors du scraping: {e}")
    finally:
        driver.quit()
    
    return articles_processed

def get_hespress_categories():
    """Liste des catégories à scraper"""
    return [
        "https://en.hespress.com/international",
        "https://en.hespress.com/society",
        "https://en.hespress.com/politics",
        "https://en.hespress.com/economy",
        "https://en.hespress.com/culture",
        "https://en.hespress.com/sports",
        "https://en.hespress.com/media",
        "https://en.hespress.com/africa"
    ]

def main():
    # Connexion à MongoDB Atlas
    try:
        collection = get_mongo_atlass_collection("articles_eng")
        print("Connexion à MongoDB Atlas établie avec succès")
    except Exception as e:
        print(f"Erreur de connexion à MongoDB: {e}")
        return
    collection.create_index([('url', 1)], unique=True)
    total_articles = 0
    categories = get_hespress_categories()
    
    for category_url in categories:
            processed = scrape_hespress_category(category_url, collection)
            total_articles += processed
            print(f"→ {processed} articles traités pour cette catégorie")
            time.sleep(uniform(2, 5))
    print(f"\nScraping terminé. {total_articles} articles au total ont été traités.")
    print(f"Vérifiez votre collection MongoDB: {collection.name}")

if __name__ == "__main__":
    main()