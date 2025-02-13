from datetime import datetime

def parse_article(article):
    """
    Parse un article HTML de Hespress et retourne un dictionnaire structuré.
    :param article: Un élément BeautifulSoup représentant un article.
    :return: Un dictionnaire contenant les données de l'article.
    """
    try:
        # Extraire le titre
        title = article.find("h1", class_="post-title").text.strip()

        # Extraire le lien
        link = article.find("a")["href"]

        # Extraire le contenu (tous les paragraphes dans la div "article-content")
        content_div = article.find("div", class_="article-content")
        content = " ".join(p.text.strip() for p in content_div.find_all("p"))

        # Extraire la date
        date_span = article.find("span", class_="date-post")
        date = clean_date(date_span.text.strip()) if date_span else datetime.now().strftime("%Y-%m-%d")

        # Retourner les données structurées
        return {
            "titre": title,
            "contenu": content,
            "source": "hespress",
            "date": date,
            "link": link
        }

    except Exception as e:
        print(f"Erreur lors du parsing d'un article : {e}")
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