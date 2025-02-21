import time
import requests
from bs4 import BeautifulSoup
import sys
import os
from datetime import datetime


# Ajouter le répertoire racine du projet au chemin d'accès pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.mongo_atlass import get_mongo_atlass_collection  # Importer la configuration MongoDB


def extract_urls_from_sitemap(sitemap_url):
    """
    Extrait les URLs des articles à partir d'un fichier sitemap XML.
    
    :param sitemap_url: URL du sitemap à analyser
    :return: Liste des URLs d'articles extraites
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(sitemap_url, headers=headers, timeout=10)
        time.sleep(3)  # Pause pour éviter d'être bloqué par le serveur

        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} pour {sitemap_url}")
            return []

        soup = BeautifulSoup(response.content, "xml")  # Parser XML pour extraire les URLs
        print(f"Récupération du sitemap : {sitemap_url}")

        urls = [loc.text for loc in soup.find_all("loc")]  # Extraction des URLs

        # Filtrer pour ne garder que les URLs .html (éviter les images .jpg et .jpeg)
        filtered_urls = [url for url in urls if not (url.endswith(".jpg") or url.endswith(".jpeg"))]

        return filtered_urls
    
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction du sitemap {sitemap_url}: {e}")
        return []


# URL du sitemap principal
sitemap_index = "https://www.hespress.com/sitemap.xml"
sub_sitemaps = extract_urls_from_sitemap(sitemap_index)
print(f"Sous-sitemaps extraits : {sub_sitemaps}")

# Extraction de toutes les URLs d'articles (limite : 6000 articles)
all_articles = []
max_articles = 6

for sitemap in sub_sitemaps:
    if len(all_articles) >= max_articles:
        break
    extracted_urls = extract_urls_from_sitemap(sitemap)
    all_articles.extend(extracted_urls)

# Limiter la liste des articles à 6000  
all_articles = all_articles[:max_articles]
print(f"Nombre total d'articles trouvés : {len(all_articles)}")

if all_articles:
    print("Exemple d'URL :", all_articles[0])
else:
    print("Aucune URL d'article trouvée.")

# Connexion à la collection MongoDB "articles_ar"
collection = get_mongo_atlass_collection("articles_ar")

def scrape_article(url):
    """
    Récupère et enregistre le contenu d'un article à partir de son URL.
    
    :param url: URL de l'article à scraper
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} sur {url}")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        # Extraction du titre de l'article
        titre = soup.find("h1", class_="post-title")
        titre = titre.text.strip() if titre else "Titre inconnu"

        # Extraction de la date de publication
        time_tag = soup.find("span", class_="date-post")
        if time_tag:
            formatted_date = time_tag.text.strip()  # Extraire la date directement sans conversion
        else:
            formatted_date = "Date inconnue"

        # Extraction de la catégorie depuis le breadcrumb (2ème <li> de classe 'breadcrumb-item')
        breadcrumb = soup.find("ol", class_="breadcrumb")
        if breadcrumb:
            breadcrumb_items = breadcrumb.find_all("li", class_="breadcrumb-item")
            if len(breadcrumb_items) > 1:
                category = breadcrumb_items[1].text.strip()  # Catégorie dans le 2ème <li>
            else:
                category = "Catégorie inconnue"
        else:
            category = "Catégorie inconnue"

        # Extraction de l'auteur
        auteur_span = soup.find("span", class_="author")
        auteur = auteur_span.find("a").text.strip() if auteur_span and auteur_span.find("a") else "Auteur inconnu"

        # Extraction du contenu principal
        contenu_div = soup.find("div", class_="article-content")
        contenu = " ".join([p.text.strip() for p in contenu_div.find_all("p")]) if contenu_div else "Contenu non disponible"

        # Vérification si l'article est incomplet
        if titre == "Titre inconnu":
            print(f"⚠️ Article ignoré (titre inconnu) : {url}")
            return
        
        if contenu == "Contenu non disponible":
            return None
        if contenu == "":
            return None

        if "inconnu" in [formatted_date, auteur]:
            print(f"⚠️ Article avec informations manquantes : {url}")
            return

        # Vérifier si l'article est déjà enregistré dans MongoDB
        if collection.find_one({"url": url}):
            print(f"⚠️ Article déjà enregistré : {url}")
            return

        # Création de l'objet article à insérer dans la base de données
        article = {
            "url": url,
            "titre": titre,
            "auteur": auteur,
            "contenu": contenu,
            "date": formatted_date,
            "categorie": category,
            "source": "hespress"
        }

        # Insertion de l'article dans la collection MongoDB
        collection.insert_one(article)
        print(f"✅ Article enregistré (Arabe) : {titre}")
    
    except Exception as e:
        print(f"❌ Erreur lors du scraping de l'article {url}: {e}")


# Scraper et enregistrer chaque article dans la base de données
for url in all_articles:
    if collection.find_one({"url": url}):
        print(f"⚠️ Article déjà enregistré, passé : {url}")
        continue
    scrape_article(url)

print("📂 Tous les nouveaux articles sont enregistrés dans MongoDB !")
