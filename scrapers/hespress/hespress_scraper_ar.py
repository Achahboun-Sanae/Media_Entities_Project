import time
import random
import requests
from bs4 import BeautifulSoup
import sys
import os
# Ajouter le répertoire racine du projet au chemin d'accès pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.mongodb import get_mongo_collection  # Import de la fonction pour se connecter à MongoDB

# Fonction pour extraire les URLs d'un sitemap
def extract_urls_from_sitemap(sitemap_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Effectuer une requête HTTP GET pour obtenir le contenu du sitemap
        response = requests.get(sitemap_url, headers=headers, timeout=10)
        # Ajouter un délai aléatoire entre les requêtes pour éviter de surcharger le serveur
        time.sleep(random.uniform(1, 3))

        # Si la réponse n'est pas 200 (OK), afficher un message d'erreur et retourner une liste vide
        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} pour {sitemap_url}")
            return []

        # Utiliser BeautifulSoup pour analyser le contenu XML du sitemap
        soup = BeautifulSoup(response.content, "xml")
        print(f"Récupération du sitemap : {sitemap_url}")

        # Extraire toutes les URLs contenues dans les balises <loc>
        urls = [loc.text for loc in soup.find_all("loc")]

        # Filtrer les URLs pour exclure celles se terminant par .jpg ou .jpeg
        filtered_urls = [url for url in urls if not (url.endswith(".jpg") or url.endswith(".jpeg"))]

        # Retourner la liste des URLs filtrées
        return filtered_urls

    except Exception as e:
        # Gérer les erreurs éventuelles (ex. erreur réseau)
        print(f"❌ Erreur lors de l'extraction du sitemap {sitemap_url}: {e}")
        return []

# Récupérer le sitemap principal
sitemap_index = "https://www.hespress.com/sitemap.xml"
sub_sitemaps = extract_urls_from_sitemap(sitemap_index)

# Afficher les sous-sitemaps extraits
print(f"Sous-sitemaps extraits : {sub_sitemaps}")

# Liste pour stocker toutes les URLs d'articles extraites
all_articles = []
max_articles = 8000  # Limiter le nombre d'articles à 8000

# Extraire les URLs des articles depuis les sous-sitemaps
for sitemap in sub_sitemaps:
    if len(all_articles) >= max_articles:
        break  # Si le nombre maximum d'articles est atteint, arrêter l'extraction
    all_articles.extend(extract_urls_from_sitemap(sitemap))

# Limiter le nombre d'articles à 8000
all_articles = all_articles[:max_articles]

# Afficher le nombre total d'articles trouvés
print(f"Nombre total d'articles trouvés : {len(all_articles)}")

# Afficher un exemple d'URL d'article (si des articles ont été trouvés)
if all_articles:
    print("Exemple d'URL :", all_articles[0])
else:
    print("Aucune URL d'article trouvée.")

# Connexion à la collection MongoDB "articles_ar" pour enregistrer les articles
collection = get_mongo_collection("articles_ar")

# Fonction pour scraper les informations d'un article à partir de son URL
def scrape_article(url):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # Effectuer une requête HTTP GET pour récupérer la page de l'article
        response = requests.get(url, headers=headers, timeout=10)

        # Si la réponse n'est pas 200 (OK), afficher un message d'erreur
        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code} sur {url}")
            return

        # Analyser le contenu HTML de la page de l'article avec BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Extraire le titre de l'article
        titre = soup.find("h1", class_="post-title")
        titre = titre.text.strip() if titre else "Titre inconnu"

        # Extraire la date de publication de l'article
        time_tag = soup.find("time", class_="date-post")
        date = time_tag["datetime"] if time_tag and time_tag.get("datetime") else "Date inconnue"

        # Extraire l'auteur de l'article
        auteur_span = soup.find("span", class_="author")
        auteur = auteur_span.find("a").text.strip() if auteur_span and auteur_span.find("a") else "Auteur inconnu"

        # Extraire le contenu de l'article
        contenu_div = soup.find("div", class_="article-content")
        contenu = " ".join([p.text.strip() for p in contenu_div.find_all("p")]) if contenu_div else "Contenu non disponible"

        # Si le titre de l'article est inconnu, l'ignorer
        if titre == "Titre inconnu":
            print(f"⚠️ Article ignoré (titre inconnu) : {url}")
            return

        # Si des informations essentielles manquent (date, auteur, contenu), ignorer l'article
        if "inconnu" in [date, auteur, contenu]:
            print(f"⚠️ Article avec informations manquantes : {url}")
            return

        # Si l'article est déjà enregistré dans la base de données, l'ignorer
        if collection.find_one({"url": url}):
            print(f"⚠️ Article déjà enregistré : {url}")
            return

        # Créer un dictionnaire avec les informations de l'article
        article = {
            "url": url,
            "titre": titre,
            "auteur": auteur,
            "contenu": contenu,
            "source": "hespress"  # Ajouter la source "hespress"
        }

        # Insérer l'article dans la collection MongoDB
        collection.insert_one(article)
        print(f"✅ Article enregistré : {titre}")

    except Exception as e:
        # Gérer les erreurs éventuelles lors du scraping de l'article
        print(f"❌ Erreur lors du scraping de l'article {url}: {e}")

# Scraper tous les articles extraits
for url in all_articles:
    # Si l'article est déjà enregistré, passer au suivant
    if collection.find_one({"url": url}):
        print(f"⚠️ Article déjà enregistré, passé : {url}")
        continue  

    # Scraper l'article
    scrape_article(url)

# Afficher un message indiquant que tous les nouveaux articles ont été enregistrés dans MongoDB
print("📂 Tous les nouveaux articles sont enregistrés dans MongoDB !")
