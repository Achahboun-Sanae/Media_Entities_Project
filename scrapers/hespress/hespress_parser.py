from datetime import datetime

from bs4 import BeautifulSoup
import requests

def parse_article_page(article_url):
    """
    Extrait les détails d'un article à partir de son URL.
    :param article_url: L'URL de l'article.
    :return: Un dictionnaire contenant les détails de l'article.
    """
    try:
        # 1. Récupérer le contenu de la page de l'article
        response = requests.get(article_url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        # 2. Parser le contenu HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # 3. Extraire les détails de l'article
        title = soup.find("h1", class_="post-title").text.strip()
        content = " ".join(p.text.strip() for p in soup.find("div", class_="article-content").find_all("p"))
        date_span = soup.find("span", class_="date-post")
        date = clean_date(date_span.text.strip()) if date_span else datetime.now().strftime("%Y-%m-%d")

        # 4. Retourner les données structurées
        return {
            "titre": title,
            "contenu": content,
            "source": "hespress",
            "date": date,
            "link": article_url
        }

    except Exception as e:
        print(f"Erreur lors de l'extraction de l'article {article_url} : {e}")
        return None

def clean_date(date_str):
    """
    Nettoie et convertit la date au format ISO (YYYY-MM-DD).
    :param date_str: La date brute extraite du site (ex: "1er octobre 2023").
    :return: La date au format ISO (ex: "2023-10-01").
    """
    try:
        # Convertir "1er octobre 2023" en "2023-10-01"
        date_str = date_str.replace("1er", "1")  # Gérer le cas de "1er"
        date_obj = datetime.strptime(date_str, "%d %B %Y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d")  # Retourne la date actuelle en cas d'erreur