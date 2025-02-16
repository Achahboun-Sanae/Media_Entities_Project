def parse_le360_articles(articles):
    parsed_articles = []
    for article in articles:
        # Exemple de traitement des articles, en ajoutant des entités comme la catégorie ou l'auteur
        parsed_article = {
            "title": article["title"],
            "link": article["link"],
            "date": article["date"],
            "category": article["category"],
            "summary": article["summary"],
            "author": article["author"]
        }
        parsed_articles.append(parsed_article)

    return parsed_articles
