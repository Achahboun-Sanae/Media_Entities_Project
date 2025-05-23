<<<<<<< HEAD
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
import random
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, unquote

# Configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.mongo_atlass import get_mongo_atlass_collection

collection = get_mongo_atlass_collection("articles_chouftv_new2")
=======
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
>>>>>>> 279f7cd5a57f4a08a6efea424b503f95e2d0cd35

MAX_ARTICLES_PER_CATEGORY = 1670
SCROLL_PAUSE_TIME = 2
MAX_SCROLLS = 300
LOAD_MORE_WAIT_TIME = 5
MAX_CLICKS = 100

<<<<<<< HEAD
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

CATEGORIES = {
    "press": [
        "https://chouftv.ma/press/presscategory/international"
        # Nouvelle catégorie ajoutée
    ]
  
}

def parse_arabic_date(date_str):
    """
    Convertit une date arabe comme "الأحد 20 أبريل 2025 | 18:41" ou "الأحد 20 أبريل 202518:41"
    en objet datetime. Retourne None si la conversion échoue.
    """
    if not date_str:
        return None

    # Dictionnaire de traduction des mois arabes
    month_trans = {
        'يناير': 'January', 'فبراير': 'February', 'مارس': 'March',
        'أبريل': 'April', 'ماي': 'May', 'يونيو': 'June',
        'يوليو': 'July', 'غشت': 'August', 'شتنبر': 'September',
        'أكتوبر': 'October', 'نونبر': 'November', 'دجنبر': 'December'
    }

    try:
        # Nettoyer la chaîne
        date_str = date_str.strip()
        
        # Séparer la date et l'heure
        if '|' in date_str:
            # Format avec séparateur: "الأحد 20 أبريل 2025 | 20:47"
            date_part, time_part = [p.strip() for p in date_str.split('|')]
        else:
            # Format sans séparateur: "الأحد 20 أبريل 202520:47"
            # Trouver où commence l'heure (recherche du premier ':' précédé de 2 chiffres)
            hour_index = -1
            for i in range(len(date_str)):
                if date_str[i] == ':' and i >= 2 and date_str[i-2:i].isdigit():
                    hour_index = i - 2
                    break
            
            if hour_index > 0:
                date_part = date_str[:hour_index].strip()
                time_part = date_str[hour_index:].strip()
            else:
                date_part = date_str
                time_part = "00:00"

        # Extraire les composants de la date
        date_parts = date_part.split()
        if len(date_parts) < 3:
            return None

        day = date_parts[-3]  # 20
        month_ar = date_parts[-2]  # أبريل
        year = date_parts[-1]  # 2025

        # Traduire le mois
        month_en = month_trans.get(month_ar)
        if not month_en:
            return None

        # Traiter l'heure
        try:
            if ':' in time_part:
                hours, minutes = map(int, time_part.split(':'))
            else:
                # Si l'heure est mal formatée (ex: "2047" au lieu de "20:47")
                if len(time_part) >= 4 and time_part[:2].isdigit() and time_part[2:4].isdigit():
                    hours = int(time_part[:2])
                    minutes = int(time_part[2:4])
                else:
                    hours, minutes = 0, 0
        except:
            hours, minutes = 0, 0

        # Créer l'objet datetime
        date_obj = datetime.strptime(f"{day} {month_en} {year}", "%d %B %Y")
        date_obj = date_obj.replace(hour=hours, minute=minutes)

        return date_obj

    except Exception as e:
        print(f"Erreur de conversion de la date '{date_str}': {str(e)}")
        return None

def get_article_urls(max_articles_per_category=30):
    """Récupère les URLs des articles"""
    article_urls = set()
    
    for section, categories in CATEGORIES.items():
        for category_url in categories:
            print(f"🔍 Scanning category: {unquote(category_url)}")
            page = 1
            category_articles = 0
            
            while category_articles < max_articles_per_category:
                try:
                    if page > 1:
                        category_page_url = f"{category_url}/page/{page}"
                    else:
                        category_page_url = category_url
                    
                    response = requests.get(category_page_url, headers=HEADERS, timeout=10)
                    if response.status_code != 200:
                        if response.status_code == 404:
                            print(f"⚠️ Category not found: {unquote(category_url)}")
                        else:
                            print(f"❌ Error {response.status_code} on {unquote(category_page_url)}")
                        break

                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    articles = soup.find_all("a", href=True)
                    found_articles = 0
                    
                    for link in articles:
                        href = link["href"]
                        if f"/{section}/" in href and href not in article_urls:
                            full_url = urljoin(category_url, href)
                            article_urls.add(full_url)
                            category_articles += 1
                            found_articles += 1
                            if category_articles >= max_articles_per_category:
                                break
                    
                    if found_articles == 0:
                        break
                    
                    print(f"📄 Page {page}: Found {found_articles} articles (Total: {category_articles})")
                    page += 1
                    time.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    print(f"⚠️ Error processing {unquote(category_url)}: {str(e)}")
                    break
    
    return list(article_urls)

def scrape_article(url):
    """Scrape un article avec gestion améliorée"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Titre
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "عنوان غير معروف"
        
        # Contenu
        content_div = soup.find("div", class_="middleContent")
        content = ""
        if content_div:
            paragraphs = [p.get_text(strip=True) for p in content_div.find_all("p") 
                        if not p.find_parent("li", class_="pub300-250")]
            content = " ".join(paragraphs)
        
        if not content:
            return None
        
        # Date de publication
        published_date = None
        time_tag = soup.find('time')
        if time_tag:
            date_text = time_tag.get_text(strip=True)
            published_date = parse_arabic_date(date_text)
        
        # Auteur
        author = "شوف تي في"
        source_span = soup.find("span", class_="source")
        if source_span:
            author = source_span.get_text(strip=True).replace("المصدر:", "").strip()
        
        # Catégorie
        category = "غير معروف"
        navbar = soup.find("ul", class_="navbar-head")
        if navbar:
            breadcrumb_links = navbar.find_all("a", href=True)
            if len(breadcrumb_links) > 1:
                category = breadcrumb_links[-1].get_text(strip=True)
        
        # Fallback par URL
        if category == "غير معروف":
            for cat_ar, cat_urls in CATEGORIES.items():
                if any(cat_url in url for cat_url in cat_urls):
                    category = cat_ar
                    break
        
        # Vérification des doublons
        if collection.find_one({"url": url}):
            return None
        
        return {
            "url": url,
            "titre": title,
            "auteur": author,
            "date": published_date,
            "categorie": category,
            "contenu": content,
            "source": "Chouf TV",
            "date_import": datetime.now()
        }
        
    except Exception as e:
        print(f"⚠️ Error scraping {url}: {str(e)}")
        return None

def main():
    """Fonction principale"""
    print("🚀 Starting ChoufTV scraper...")
    
    article_urls = get_article_urls()
    print(f"✅ Found {len(article_urls)} articles. Starting scraping...")
    
    successful = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i, result in enumerate(executor.map(scrape_article, article_urls)):
            if result:
                collection.insert_one(result)
                successful += 1
            print(f"📊 Progress: {i+1}/{len(article_urls)} articles processed", end="\r")
    
    print(f"\n💾 Saved {successful} articles to MongoDB.")
    print("✅ All done!")

=======
def parse_hespress_date(date_str):
    """
    Convertit les dates françaises de Hespress en objets datetime.
    Format: "mardi 18 février 2025 - 23:00"
    """
    month_mapping = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
    }

    try:
        # Nettoyage de la chaîne
        date_str = re.sub(r'^\w+\s', '', date_str)  # Supprimer le jour
        date_str = date_str.strip()
        
        # Séparation date/heure
        date_part, time_part = date_str.split(' - ')
        day, month_fr, year = date_part.split()
        hour, minute = map(int, time_part.split(':'))
        
        # Conversion du mois
        month = month_mapping.get(month_fr.lower(), 1)
        
        return datetime(int(year), month, int(day), hour, minute)
        
    except Exception as e:
        print(f"Erreur de conversion de date: {date_str} ({e})")
        return datetime.now()

def setup_driver():
    """Configure Selenium WebDriver avec plus d'options"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
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
        'source': 'hespress_fr',
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
        
        "https://fr.hespress.com/societe",
        "https://fr.hespress.com/politique",
        "https://fr.hespress.com/sport",
        "https://fr.hespress.com/monde",
        "https://fr.hespress.com/economie",
        "https://fr.hespress.com/culture",
        "https://fr.hespress.com/media"
    ]

def main():
    # Connexion à MongoDB Atlas
    try:
        collection = get_mongo_atlass_collection("articles_fr")
        print("Connexion à MongoDB Atlas établie avec succès")
    except Exception as e:
        print(f"Erreur de connexion à MongoDB: {e}")
        return
    collection.create_index([('url', 1)], unique=True)
    total_articles = 0
    categories = get_hespress_categories()
    
    for category_url in categories:
            if "sport" in category_url:
                processed = scrape_hespress_sport(category_url, collection)
            else:
                processed = scrape_hespress_category(category_url, collection)
            total_articles += processed
            print(f"→ {processed} articles traités pour cette catégorie")
            time.sleep(uniform(2, 5))
    print(f"\nScraping terminé. {total_articles} articles au total ont été traités.")
    print(f"Vérifiez votre collection MongoDB: {collection.name}")

>>>>>>> 279f7cd5a57f4a08a6efea424b503f95e2d0cd35
if __name__ == "__main__":
    main()