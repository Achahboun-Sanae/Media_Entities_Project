import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import time
import concurrent.futures
import re
import sys
import os
from urllib.parse import urljoin
import logging
from logging.handlers import RotatingFileHandler

# Configuration
MAX_WORKERS = 5
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
ARTICLES_PER_CATEGORY = 1670

# Dictionnaire de correspondance des catégories (français -> arabe)
CATEGORIES_TRANSLATION = {
    'politique': 'سياسة',
    'economie': 'اقتصاد',
    'societe': 'مجتمع',
    'culture': 'ثقافة',
    'monde': 'دولي',
    'sports': 'رياضة',
    'medias': 'ميديا'
}

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('le360_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire racine du projet au chemin d'accès pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.mongo_atlass import get_mongo_atlass_collection

# Connexion MongoDB
collection = get_mongo_atlass_collection("articles_ar")

def extract_and_parse_date(soup):
    """
    Extrait et parse la date depuis le HTML
    Args:
        soup: Objet BeautifulSoup
    Returns:
        datetime: Objet datetime ou None si non trouvé
    """
    # Sélecteurs prioritaires pour le site le360.ma
    date_selectors = [
        'div.article-main-information-subheadline-date',
        'div.article-date',
        'div.subheadline-date',
        'span.date',
        'time[datetime]',
        'div.timestamp'
    ]
    for selector in date_selectors:
        date_tag = soup.select_one(selector)
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            parsed_date = parse_arabic_date(date_text)
            if parsed_date:
                return parsed_date
    return None

def parse_arabic_date(date_text):
    """
    Parse les dates en format arabe
    """
    try:
        # Pattern pour le format le360.ma
        pattern = r'في (\d{2}/\d{2}/\d{4}) على الساعة (\d{2}:\d{2})'
        match = re.search(pattern, date_text)
        if match:
            return datetime.strptime(f"{match.group(1)} {match.group(2)}", "%d/%m/%Y %H:%M")
        # Autres formats possibles
        patterns = [
            (r'(\d{2}/\d{2}/\d{4})', "%d/%m/%Y"),
            (r'(\d{2}-\d{2}-\d{4})', "%d-%m-%Y"),
            (r'(\d{4}-\d{2}-\d{2})', "%Y-%m-%d"),
            (r'(\d{1,2}\s+\w+\s+\d{4})', "%d %m %Y")
        ]
        for pattern, date_format in patterns:
            match = re.search(pattern, date_text)
            if match:
                return datetime.strptime(match.group(1), date_format)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Erreur de parsing de date: {date_text} - {str(e)}")
    return None

def extract_title(soup):
    """Extrait le titre de l'article de manière robuste"""
    try:
        # Essayer d'abord avec le sélecteur spécifique
        title_elem = soup.find('h1', class_='headline-container')
        if title_elem:
            return title_elem.get_text(strip=True)
        # Fallback aux autres méthodes
        title_elem = soup.find('h1') or \
            soup.find('meta', {'property': 'og:title'}) or \
            soup.find('meta', {'name': 'title'})
        if title_elem:
            return title_elem.get('content', title_elem.get_text(strip=True))
    except Exception as e:
        logger.warning(f"Erreur d'extraction du titre: {str(e)}")
    return "بدون عنوان"

def extract_content(soup):
    """Extrait le contenu principal de l'article"""
    try:
        # Sélecteurs prioritaires pour le contenu
        content_selectors = [
            'article.default__ArticleBody-sc-10mj2vp-2',
            'div.article-body',
            'div.post-content',
            'div.article-content'
        ]
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Nettoyage des éléments non désirés
                for elem in content_elem(['script', 'style', 'iframe', 'aside',
                                           'figure', 'div.ad-container', 'div.related-articles']):
                    elem.decompose()
                # Extraction du texte avec préservation des paragraphes
                paragraphs = []
                for p in content_elem.find_all(['p', 'h2', 'h3'], recursive=True):
                    text = p.get_text(' ', strip=True)
                    if len(text) > 20:  # Filtre les paragraphes trop courts
                        paragraphs.append(text)
                if paragraphs:
                    return '\n\n'.join(paragraphs)
    except Exception as e:
        logger.warning(f"Erreur d'extraction du contenu: {str(e)}")
    return "المحتوى غير متوفر"

def extract_author(soup):
    """Extraction optimisée de l'auteur"""
    author_selectors = [
        'a.byline-credits-bold',
        'div.author-name',
        'span.author',
        'span.byline-credits-bold',
        'a[href*="/author/"]',
        'div.article-author'
    ]
    for selector in author_selectors:
        author_tag = soup.select_one(selector)
        if author_tag:
            author = author_tag.get_text(strip=True)
            if author:
                return ' '.join(author.split())
    return "le360.ma"

def get_sitemap_urls(category):
    """Récupère les URLs des sitemaps pour une catégorie"""
    sitemap_index_url = f"https://ar.le360.ma/arc/outboundfeeds/sitemap-index/category/{category}/"
    try:
        response = requests.get(sitemap_index_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        return [sitemap.find('loc').text for sitemap in soup.find_all('sitemap')
                if f"/category/{category}/" in sitemap.find('loc').text][:17]
    except Exception as e:
        logger.error(f"Erreur sitemap pour {category}: {str(e)}")
    return []

def extract_articles_from_sitemap(sitemap_url):
    """Extrait les URLs d'articles depuis un sitemap"""
    try:
        response = requests.get(sitemap_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        return [{
            'url': url.find('loc').text,
            'lastmod': url.find('lastmod').text if url.find('lastmod') else None,
            'image': url.find('image:loc').text if url.find('image:loc') else None
        } for url in soup.find_all('url')]
    except Exception as e:
        logger.error(f"Erreur sitemap {sitemap_url}: {str(e)}")
    return []

def scrape_article(url, category_fr, retry=0):
    """Scrape le contenu d'un article avec gestion des erreurs"""
    if retry >= MAX_RETRIES:
        return None

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Conversion de la catégorie française en arabe
        category_ar = CATEGORIES_TRANSLATION.get(category_fr, category_fr)

        return {
            'titre': extract_title(soup),
            'contenu': extract_content(soup),
            'auteur': extract_author(soup),
            'date': extract_and_parse_date(soup),
            'url': url,
            'categorie': category_ar,  # Stockage en arabe dans la base
            'source': 'le360_ar',
            'date_import': datetime.now(),
        }

    except Exception as e:
        logger.warning(f"Retry {retry+1} pour {url}: {str(e)}")
        time.sleep(2 * (retry + 1))
        return scrape_article(url, category_fr, retry + 1)

def process_category(category_fr):
    """Traite une catégorie complète"""
    logger.info(f"Traitement catégorie: {category_fr}")
    start_time = time.time()

    # 1. Récupération des sitemaps
    sitemap_urls = get_sitemap_urls(category_fr)
    logger.info(f"Nombre de sitemaps: {len(sitemap_urls)}")

    # 2. Extraction des URLs d'articles
    article_urls = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(extract_articles_from_sitemap, url) for url in sitemap_urls]
        article_urls = [url for future in concurrent.futures.as_completed(futures)
                        for url in future.result()][:ARTICLES_PER_CATEGORY]
    logger.info(f"Articles à scraper: {len(article_urls)}")

    # 3. Scraping des articles
    scraped_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_article, article['url'], category_fr): article
                   for article in article_urls}

        for future in concurrent.futures.as_completed(futures):
            article_data = future.result()
            if article_data:
                try:
                    collection.update_one(
                        {'url': article_data['url']},
                        {'$setOnInsert': article_data},
                        upsert=True
                    )
                    scraped_count += 1
                    if scraped_count % 100 == 0:
                        logger.info(f"Progression: {scraped_count}/{len(article_urls)}")
                except Exception as e:
                    logger.error(f"Erreur MongoDB: {str(e)}")

    logger.info(f"Terminé: {scraped_count} articles | Temps: {(time.time()-start_time)/60:.1f}min")
    return scraped_count

def main():
    """Fonction principale"""
    categories_fr = [
        #'politique',
        #'economie',
        #'societe',
        #'culture',
        'monde',
        'sports',
        'medias'
    ]
    total = 0
    start_time = time.time()
    for category_fr in categories_fr:
        try:
            total += process_category(category_fr)
            time.sleep(10)
        except Exception as e:
            logger.error(f"ERREUR catégorie {category_fr}: {str(e)}")

    logger.info(f"SCRAPING TERMINÉ: {total} articles | Temps total: {(time.time()-start_time)/3600:.1f} heures")

if __name__ == "__main__":
    main()
