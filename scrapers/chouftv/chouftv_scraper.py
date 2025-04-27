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

collection = get_mongo_atlass_collection("articles_chouftv_sport")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

CATEGORIES = {
    '''
    "press": [
        "https://chouftv.ma/press/presscategory/politique",
        "https://chouftv.ma/press/presscategory/societe",
        "https://chouftv.ma/press/presscategory/international"
    ],
    '''
    "sport": [
        "https://chouftv.ma/sport/sportcategory/دوريات",
        "https://chouftv.ma/sport/sportcategory/رياضات-أخرى",
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

def get_article_urls(max_articles_per_category=1700):
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
            "source": "شوف تي في",
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

if __name__ == "__main__":
    main()