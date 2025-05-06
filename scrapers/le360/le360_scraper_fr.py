import random
import requests
from bs4 import BeautifulSoup
<<<<<<< HEAD
import time
import random
import sys
import os
from datetime import datetime, timedelta
import re

# Configuration des chemins
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.mongo_atlass import get_mongo_atlass_collection  

# Initialisation MongoDB
collection = get_mongo_atlass_collection("articles_ar")

# Configuration du scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

CATEGORIES = ["world"]
MAX_ARTICLES_PER_CATEGORY = 600

def parse_relative_date(relative_time_str):
    """Convertit les dates relatives en datetime"""
    now = datetime.now()
    time_units = {
        'ثانية': 'seconds',
        'دقيقة': 'minutes',
        'ساعة': 'hours',
        'ساعات': 'hours',
        'يوم': 'days',
        'أيام': 'days',
        'أسبوع': 'weeks',
        'شهر': 'months',
        'سنة': 'years'
    }
    
    matches = re.findall(r'(\d+)\s+(ثانية|ثوان|دقيقة|دقائق|ساعة|ساعات|يوم|أيام|أسبوع|أسابيع|شهر|أشهر|سنة|سنوات)', relative_time_str)
    
    if not matches:
        return now
    
    kwargs = {}
    for value, unit in matches:
        english_unit = time_units.get(unit)
        if english_unit:
            kwargs[english_unit] = int(value)
    
    if 'months' in kwargs:
        months = kwargs.pop('months')
        now = now - timedelta(days=months*30)
    if 'years' in kwargs:
        years = kwargs.pop('years')
        now = now - timedelta(days=years*365)
    
    if kwargs:
        now = now - timedelta(**kwargs)
    
    return now

def normalize_date(date_str):
    """Normalise tous les formats de date"""
    if not date_str:
        return None
    
    if 'مضت' in date_str:
        return parse_relative_date(date_str)
    
    try:
        return datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
    except ValueError:
        return None

def extract_author(author_str, first_para=None):
    """Extrait proprement le nom d'auteur depuis la balise ou le contenu"""
    if not author_str:
        author_str = ""
    
    # Nettoyage initial
    author_str = author_str.strip()
    
    # Cas spécial: auteur avec *
    if "*" in author_str:
        return author_str.split("*")[0].strip()
    
    # Extraction depuis la balise
    separators = [' - ', ' ـ ', ' : ', 'ـ']
    for sep in separators:
        if sep in author_str:
            parts = author_str.split(sep)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
    
    # Si pas trouvé dans balise, chercher dans le premier paragraphe
    if first_para:
        match = re.search(r'أخبارنا المغربية\s*[ـ\-:]\s*(.*?)(?:\n|$|\.)', first_para)
        if match:
            return match.group(1).strip()
    
    return author_str if author_str else "أخبارنا المغربية"

def clean_content(content_paragraphs, author_name):
    """Nettoie le contenu si l'auteur y apparaît"""
    if not content_paragraphs or not author_name or author_name == "أخبارنا المغربية":
        return content_paragraphs
    
    first_para = content_paragraphs[0]
    patterns = [
        r'أخبارنا المغربية\s*[ـ\-:]\s*' + re.escape(author_name),
        r'بقلم\s*' + re.escape(author_name)
    ]
    
    for pattern in patterns:
        if re.search(pattern, first_para):
            cleaned_para = re.sub(pattern, '', first_para).strip()
            if cleaned_para:
                content_paragraphs[0] = cleaned_para
            else:
                content_paragraphs.pop(0)
            break
    
    return content_paragraphs

def is_duplicate(url, title):
    """Vérifie les doublons par URL et titre"""
    return collection.find_one({"$or": [{"url": url}, {"titre": title}]})

def get_article_urls():
    """Récupère les URLs des articles"""
    base_url = "https://www.akhbarona.com"
    article_urls = set()

    for category in CATEGORIES:
        page = 1
        category_count = 0
        
        while category_count < MAX_ARTICLES_PER_CATEGORY:
            url = f"{base_url}/{category}/index.{page}.html"
            print(f"🔍 Scraping {url}...")

            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                if response.status_code == 404:
                    break
                if response.status_code != 200:
                    time.sleep(5)
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                articles = soup.find_all("a", href=True)

                found = 0
                for article in articles:
                    href = article["href"]
                    if "/articles/" in href or any(cat in href for cat in CATEGORIES):
                        full_url = base_url + href if href.startswith("/") else href
                        if full_url not in article_urls:
                            article_urls.add(full_url)
                            found += 1
                            category_count += 1
                            
                            if category_count >= MAX_ARTICLES_PER_CATEGORY:
                                break

                if found == 0:
                    break

                page += 1
                time.sleep(random.uniform(1, 3))

            except Exception as e:
                print(f"❌ Erreur: {e}")
                time.sleep(5)

    return list(article_urls)

def scrape_article(url):
    """Scrape un article individuel"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Extraction des données de base
        titre_tag = soup.find("h1", class_="text-end artical-content-heads lc-fs24")
        titre = titre_tag.text.strip() if titre_tag else None

        # Vérification précoce des doublons
        if is_duplicate(url, titre):
            print(f"⏭ Doublon détecté: {titre[:50]}...")
            return None

        contenu_div = soup.find("div", class_="bodystr")
        contenu_paragraphs = [p.text.strip() for p in contenu_div.find_all("p")] if contenu_div else []
        first_para = contenu_paragraphs[0] if contenu_paragraphs else None

        # Extraction de l'auteur
        auteur_tag = soup.find("h4", class_="mb-3 lc-clr1")
        auteur_str = auteur_tag.text.strip() if auteur_tag else None
        auteur = extract_author(auteur_str, first_para)

        # Nettoyage du contenu
        contenu_paragraphs = clean_content(contenu_paragraphs, auteur)
        contenu = " ".join(contenu_paragraphs) if contenu_paragraphs else None

        # Autres métadonnées
        categorie_tag = soup.find("span", class_="ms-2")
        categorie = categorie_tag.text.strip() if categorie_tag else None

        date_tag = soup.find("span", class_="story_date")
        date_str = date_tag.text.strip() if date_tag else None
        date_publication = normalize_date(date_str)

        # Validation finale
        if not titre or not contenu:
            return None

        return {
            "url": url,
            "titre": titre,
            "categorie": categorie,
            "date": date_publication,
            "auteur": auteur,
            "contenu": contenu,
            "source": "Akhbarona",
            "date_import": datetime.now()
        }

    except Exception as e:
        print(f"❌ Erreur sur {url}: {e}")
        return None

def main():
    """Point d'entrée principal"""
    print("🚀 Début du scraping...")
    article_urls = get_article_urls()
    
    if not article_urls:
        print("⚠ Aucun article trouvé")
        return

    articles = []
    for i, url in enumerate(article_urls, 1):
        print(f"📄 ({i}/{len(article_urls)}) Traitement: {url}")
        article = scrape_article(url)
        if article:
            articles.append(article)

        if len(articles) >= 50:
            try:
                collection.insert_many(articles)
                articles = []
            except Exception as e:
                print(f"❌ Erreur MongoDB: {e}")

        time.sleep(random.uniform(1, 3))

    if articles:
        try:
            collection.insert_many(articles)
        except Exception as e:
            print(f"❌ Erreur finale MongoDB: {e}")

    print("✅ Scraping terminé avec succès !")

if __name__ == "__main__":
    main()
=======
from pymongo import MongoClient
from datetime import datetime, timedelta
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
collection = get_mongo_atlass_collection("articles_fr")

def parse_french_date(date_text):
    """
    Parse les dates en format français spécifique à le360.ma
    Formats supportés:
    - "Le 07/04/2025 à 12h18"
    - "23.04.2025 - 18:37"
    - "07/04/2025 12:18"
    - "7 avril 2025 à 12h18"
    - "2025-04-07T18:37:00Z" (format ISO)
    - "Publié le 7 avril 2025 à 12h18"
    - "Mise à jour: 07/04/2025 12:18"
    """
    try:
        # Nettoyage préalable du texte
        date_text = date_text.strip()
        
        # Liste des mois en français
        months_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 
                    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
        
        # 1. Format "Le 07/04/2025 à 12h18"
        match = re.search(r'Le (\d{1,2})/(\d{1,2})/(\d{4}) à (\d{1,2})h(\d{2})', date_text)
        if match:
            day, month, year, hour, minute = match.groups()
            return datetime(int(year), int(month), int(day), int(hour), int(minute))

        # 2. Format "23.04.2025 - 18:37"
        match = re.search(r'(\d{2})\.(\d{2})\.(\d{4}) - (\d{2}):(\d{2})', date_text)
        if match:
            day, month, year, hour, minute = match.groups()
            return datetime(int(year), int(month), int(day), int(hour), int(minute))

        # 3. Format "7 avril 2025 à 12h18"
        match = re.search(r'(\d{1,2})\s+(' + '|'.join(months_fr) + r')\s+(\d{4})(?: à (\d{1,2})h(\d{2}))?', date_text)
        if match:
            day, month_fr, year, hour, minute = match.groups()
            month = months_fr.index(month_fr.lower()) + 1
            hour = int(hour) if hour else 0
            minute = int(minute) if minute else 0
            return datetime(int(year), month, int(day), hour, minute)

        # 4. Format ISO "2025-04-07T18:37:00Z"
        try:
            return datetime.fromisoformat(date_text.replace('Z', '+00:00'))
        except ValueError:
            pass

        # 5. Format "Publié le 7 avril 2025 à 12h18"
        match = re.search(r'Publié le (\d{1,2})\s+(' + '|'.join(months_fr) + r')\s+(\d{4})(?: à (\d{1,2})h(\d{2}))?', date_text)
        if match:
            day, month_fr, year, hour, minute = match.groups()
            month = months_fr.index(month_fr.lower()) + 1
            hour = int(hour) if hour else 0
            minute = int(minute) if minute else 0
            return datetime(int(year), month, int(day), hour, minute)
        
        # 6. Format "Mise à jour: 07/04/2025 12:18"
        match = re.search(r'Mise à jour:\s*(\d{2})/(\d{2})/(\d{4})\s*(\d{2}):(\d{2})', date_text)
        if match:
            day, month, year, hour, minute = match.groups()
            return datetime(int(year), int(month), int(day), int(hour), int(minute))

        # 7. Formats simples sans heure
        formats = [
            '%d/%m/%Y %H:%M',    # 07/04/2025 12:18
            '%d/%m/%Y',           # 07/04/2025
            '%d-%m-%Y',           # 07-04-2025
            '%Y-%m-%d',           # 2025-04-07
            '%d %B %Y',           # 7 avril 2025
            '%B %d, %Y',          # avril 7, 2025
            '%Y-%m-%d %H:%M:%S',  # 2025-04-07 12:18:00
            '%Y-%m-%dT%H:%M:%S%z' # 2025-04-07T12:18:00+0000
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue

        # 8. Format timestamp UNIX
        if date_text.isdigit() and len(date_text) == 10:
            try:
                return datetime.fromtimestamp(int(date_text))
            except ValueError:
                pass

    except Exception as e:
        logger.warning(f"Erreur de parsing de date '{date_text}': {str(e)}")
    
    return None

def extract_and_parse_date(soup):
    """
    Extrait et parse la date depuis le HTML avec plusieurs méthodes de fallback
    Version améliorée avec :
    - Plus de sélecteurs CSS
    - Meilleure gestion des meta tags
    - Recherche plus robuste dans le texte
    - Gestion des warnings de dépréciation
    """
    # Sélecteurs prioritaires pour le site le360.ma (mis à jour)
    date_selectors = [
        'div.article-date',
        'span.published-date',
        'time.published',
        'div.meta-date',
        'div.post-date',
        'div.date-published',
        'div.entry-date',
        'div.timestamp',
        'div.date',
        'span.date',
        'time[datetime]',
        'div.article-meta time',
        'div.article-header time',
        'div.article-info time',
        'div.article-main-information-subheadline-date',
        'div.article-date',
        'div.subheadline-date',
        'div.article-time',
        'span.article-date'
    ]
    
    # Meta tags contenant souvent la date (liste étendue)
    meta_selectors = [
        ('meta[property="article:published_time"]', 'content'),
        ('meta[name="date"]', 'content'),
        ('meta[name="pubdate"]', 'content'),
        ('meta[name="publish-date"]', 'content'),
        ('meta[name="DC.date.issued"]', 'content'),
        ('meta[itemprop="datePublished"]', 'content'),
        ('meta[property="og:published_time"]', 'content')
    ]
    
    # 1. Essayer d'abord les sélecteurs normaux
    for selector in date_selectors:
        date_tag = soup.select_one(selector)
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            if not date_text and 'datetime' in date_tag.attrs:
                date_text = date_tag['datetime']
            
            parsed_date = parse_french_date(date_text)
            if parsed_date:
                logger.debug(f"Date trouvée via sélecteur {selector}: {date_text}")
                return parsed_date
    
    # 2. Essayer les meta tags
    for selector, attr in meta_selectors:
        meta_tag = soup.select_one(selector)
        if meta_tag and meta_tag.get(attr):
            parsed_date = parse_french_date(meta_tag[attr])
            if parsed_date:
                logger.debug(f"Date trouvée via meta tag {selector}: {meta_tag[attr]}")
                return parsed_date
    
    # 3. Recherche avancée dans le texte
    try:
        # Nouvelle méthode sans warning de dépréciation
        date_pattern = re.compile(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b')
        potential_dates = soup.find_all(string=date_pattern)
        
        for text in potential_dates:
            if isinstance(text, str) and len(text.strip()) < 100:  # Éviter les longs textes
                match = date_pattern.search(text)
                if match:
                    parsed_date = parse_french_date(match.group())
                    if parsed_date:
                        logger.debug(f"Date trouvée via recherche texte: {match.group()}")
                        return parsed_date
    except Exception as e:
        logger.warning(f"Erreur recherche date texte: {str(e)}")
    
    # 4. Dernier recours: balises time et date alternatives
    fallback_selectors = [
        ('time', 'datetime'),
        ('span[class*="date"]', None),
        ('div[class*="date"]', None)
    ]
    
    for tag, attr in fallback_selectors:
        elements = soup.find_all(tag)
        for el in elements:
            date_text = el[attr] if attr and attr in el.attrs else el.get_text(strip=True)
            parsed_date = parse_french_date(date_text)
            if parsed_date:
                logger.debug(f"Date trouvée via fallback {tag}[{attr}]: {date_text}")
                return parsed_date
    
    logger.warning("Aucune date trouvée dans la page après recherche exhaustive")
    return None

def parse_arabic_date(date_text):
    """
    Parse les dates en format français spécifique à le360.ma
    Format attendu: "Le 20/04/2025 à 10h06"
    """
    try:
        # Pattern pour le format français de le360.ma
        pattern = r'Le (\d{2}/\d{2}/\d{4}) à (\d{2})h(\d{2})'
        match = re.search(pattern, date_text)
        
        if match:
            date_part = match.group(1)  # 20/04/2025
            hour = match.group(2)      # 10
            minute = match.group(3)    # 06
            return datetime.strptime(f"{date_part} {hour}:{minute}", "%d/%m/%Y %H:%M")
        
        # Autres formats français possibles
        patterns = [
            (r'(\d{2}/\d{2}/\d{4})', "%d/%m/%Y"),  # 20/04/2025
            (r'(\d{2}-\d{2}-\d{4})', "%d-%m-%Y"),   # 20-04-2025
            (r'(\d{4}-\d{2}-\d{2})', "%Y-%m-%d"),   # 2025-04-20
            (r'(\d{1,2}\s+[a-zA-Zéû]+\s+\d{4})', "%d %B %Y")  # 20 avril 2025
        ]
        
        for pattern, date_format in patterns:
            match = re.search(pattern, date_text)
            if match:
                return datetime.strptime(match.group(1), date_format)
                
    except (ValueError, AttributeError) as e:
        logger.warning(f"Erreur de parsing de date française: {date_text} - {str(e)}")
    
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
    
    return "aucun titre"

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
    
    return "Contenu Non disponible"

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
    sitemap_index_url = f"https://fr.le360.ma/arc/outboundfeeds/sitemap-index/category/{category}/"
    
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
    """Scrape le contenu d'un article avec gestion robuste des dates"""
    if retry >= MAX_RETRIES:
        logger.warning(f"Max retries reached for {url}")
        return None
        
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraction des données de base
        article_data = {
            'titre': extract_title(soup),
            'contenu': extract_content(soup),
            'auteur': extract_author(soup),
            'url': url,
            'categorie': category_fr,
            'source': 'le360_fr',
            'date_import': datetime.now(),

        }
        
        # Extraction de la date avec fallbacks hiérarchisés
        article_date = extract_and_parse_date(soup)
        
        if article_date:
            article_data['date'] = article_date
        else:
            # Fallback 1: Date de dernière modification dans l'en-tête HTTP
            last_modified = response.headers.get('Last-Modified')
            if last_modified:
                try:
                    article_data['date'] = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
                    article_data['date_source'] = 'http_header'
                    logger.info(f"Used HTTP Last-Modified header for {url}")
                except ValueError:
                    pass
            
            # Fallback 2: Date actuelle moins un délai aléatoire
            if 'date' not in article_data:
                random_days = random.randint(1, 30)
                article_data['date'] = datetime.now() - timedelta(days=random_days)
                article_data['date_estimated'] = True
                article_data['date_source'] = 'estimated'
                logger.warning(f"Estimated date for {url}")
        
        return article_data
        
    except Exception as e:
        logger.warning(f"Retry {retry+1} for {url}: {str(e)}")
        time.sleep(2 * (retry + 1))
        return scrape_article(url, category_fr, retry + 1)

def get_date_from_sitemap(url):
    """Essaie de récupérer la date depuis le sitemap"""
    try:
        # Cette fonction devrait être adaptée à votre implémentation des sitemaps
        # Voici un exemple basique:
        domain = re.match(r'https?://[^/]+', url).group()
        sitemap_url = f"{domain}/sitemap.xml"
        
        response = requests.get(sitemap_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        
        for url_tag in soup.find_all('url'):
            if url_tag.find('loc').text == url:
                lastmod = url_tag.find('lastmod')
                if lastmod:
                    return parse_french_date(lastmod.text)
    except Exception:
        return None

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
        'politique', 
        'economie', 
        'societe', 
        'culture', 
        'monde',
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
    
>>>>>>> 279f7cd5a57f4a08a6efea424b503f95e2d0cd35
