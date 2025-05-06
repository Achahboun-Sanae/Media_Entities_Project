import requests
from bs4 import BeautifulSoup
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

# Configuration scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
CATEGORIES = ["economy"]
MAX_ARTICLES_PER_CATEGORY = 2000

def parse_relative_date(relative_time_str):
    now = datetime.now()
    time_units = {
        'ثانية': 'seconds', 'ثوان': 'seconds',
        'دقيقة': 'minutes', 'دقائق': 'minutes',
        'ساعة': 'hours', 'ساعات': 'hours',
        'يوم': 'days', 'أيام': 'days',
        'أسبوع': 'weeks', 'أسابيع': 'weeks',
        'شهر': 'months', 'أشهر': 'months',
        'سنة': 'years', 'سنوات': 'years'
    }

    matches = re.findall(r'(\d+)\s+(ثانية|ثوان|دقيقة|دقائق|ساعة|ساعات|يوم|أيام|أسبوع|أسابيع|شهر|أشهر|سنة|سنوات)', relative_time_str)
    if not matches:
        return now

    kwargs = {}
    for value, unit in matches:
        eng_unit = time_units.get(unit)
        if eng_unit:
            kwargs[eng_unit] = int(value)

    if 'months' in kwargs:
        now -= timedelta(days=kwargs.pop('months') * 30)
    if 'years' in kwargs:
        now -= timedelta(days=kwargs.pop('years') * 365)
    if kwargs:
        now -= timedelta(**kwargs)

    return now

def normalize_date(date_str):
    if not date_str:
        return None
    if 'مضت' in date_str:
        return parse_relative_date(date_str)
    try:
        return datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
    except ValueError:
        return None

def extract_author(author_str, first_para=None):
    if not author_str:
        author_str = ""
    author_str = author_str.strip()

    if "*" in author_str:
        return author_str.split("*")[0].strip()

    for sep in [' - ', ' ـ ', ' : ', 'ـ']:
        if sep in author_str:
            parts = author_str.split(sep)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()

    if first_para:
        match = re.search(r'أخبارنا المغربية\s*[ـ\-:]\s*(.*?)(?:\n|$|\.)', first_para)
        if match:
            return match.group(1).strip()

    return author_str if author_str else "أخبارنا المغربية"

def clean_content(content_paragraphs, author_name):
    if not content_paragraphs or not author_name or author_name == "أخبارنا المغربية":
        return content_paragraphs

    first_para = content_paragraphs[0]
    patterns = [
        r'أخبارنا المغربية\s*[ـ\-:]\s*' + re.escape(author_name),
        r'بقلم\s*' + re.escape(author_name)
    ]
    for pattern in patterns:
        if re.search(pattern, first_para):
            cleaned = re.sub(pattern, '', first_para).strip()
            if cleaned:
                content_paragraphs[0] = cleaned
            else:
                content_paragraphs.pop(0)
            break

    return content_paragraphs

def is_duplicate(url, title):
    return collection.find_one({"$or": [{"url": url}, {"titre": title}]})

def get_article_urls():
    base_url = "https://www.akhbarona.com"
    article_urls = set()
    MAX_PAGES = 50  # Add a maximum page limit to prevent infinite loops

    for category in CATEGORIES:
        page = 1
        count = 0
        previous_urls_size = 0
        
        while count < MAX_ARTICLES_PER_CATEGORY and page <= MAX_PAGES:
            # Handle first page differently as it might not have "index.1.html"
            if page == 1:
                url = f"{base_url}/{category}/"
            else:
                url = f"{base_url}/{category}/index.{page}.html"
                
            print(f"🔍 Scraping {url}...")
            
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                
                # If page doesn't exist or returns error, stop
                if resp.status_code == 404:
                    print(f"⚠ Page {page} not found, moving to next category")
                    break
                
                if resp.status_code != 200:
                    print(f"⚠ Received status code {resp.status_code}, retrying...")
                    time.sleep(5)
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                
                # More specific article link selection
                article_links = soup.select("a[href*='/articles/']")
                found = 0
                
                for link in article_links:
                    href = link["href"]
                    # Ensure we're getting proper article URLs
                    if not href.endswith('.html'):
                        continue
                        
                    full_url = base_url + href if href.startswith("/") else href
                    
                    if full_url not in article_urls:
                        article_urls.add(full_url)
                        count += 1
                        found += 1
                        if count >= MAX_ARTICLES_PER_CATEGORY:
                            break
                
                # If no new articles found on this page, stop
                if found == 0:
                    print("⏹ No new articles found on this page, stopping")
                    break
                    
                # If we didn't find any new URLs after 2 pages, stop
                if len(article_urls) == previous_urls_size:
                    print("⏹ No new URLs found for 2 consecutive pages, stopping")
                    break
                    
                previous_urls_size = len(article_urls)
                page += 1
                time.sleep(random.uniform(1, 3))
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Request failed for {url}: {e}")
                time.sleep(10)
                continue
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                time.sleep(5)
                continue
    
    return list(article_urls)

def scrape_article(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        titre_tag = soup.find("h1", class_="text-end artical-content-heads lc-fs24")
        titre = titre_tag.text.strip() if titre_tag else None
        if is_duplicate(url, titre):
            print(f"⏭ Doublon détecté: {titre[:50]}...")
            return None

        contenu_div = soup.find("div", class_="bodystr")
        contenu_paragraphs = [p.text.strip() for p in contenu_div.find_all("p")] if contenu_div else []
        first_para = contenu_paragraphs[0] if contenu_paragraphs else None

        auteur_tag = soup.find("h4", class_="mb-3 lc-clr1")
        auteur_str = auteur_tag.text.strip() if auteur_tag else None
        auteur = extract_author(auteur_str, first_para)
        contenu_paragraphs = clean_content(contenu_paragraphs, auteur)
        contenu = " ".join(contenu_paragraphs) if contenu_paragraphs else None

        categorie_tag = soup.find("span", class_="ms-2")
        categorie = categorie_tag.text.strip() if categorie_tag else CATEGORIES[0]

        date_tag = soup.find("span", class_="story_date")
        date_str = date_tag.text.strip() if date_tag else None
        date_publication = normalize_date(date_str)

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
