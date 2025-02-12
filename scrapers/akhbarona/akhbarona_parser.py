def parse_akhbarona_articles(articles):
    parsed_articles = []
    for article in articles:
        # Exemples de parsing additionnel: extraire des entités comme des catégories, des auteurs, etc.
        parsed_article = {
            "title": article["title"],
            "link": article["link"],
            "summary": article["summary"],
            # Ajouter des entités supplémentaires si disponibles
            "category": "Non spécifié",  # Exemple de donnée supplémentaire
            "author": "Auteur inconnu"   # Exemple de donnée supplémentaire
        }
        parsed_articles.append(parsed_article)

    return parsed_articles
