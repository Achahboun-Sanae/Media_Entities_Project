import json

def parse_akhbarona_articles(input_file="akhbarona_articles.json", output_file="akhbarona_articles_parsed.json"):
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            articles = json.load(f)
    except FileNotFoundError:
        print(f"❌ Le fichier {input_file} est introuvable.")
        return
    except json.JSONDecodeError:
        print(f"❌ Erreur lors de la lecture du fichier JSON.")
        return

    parsed_articles = []
    for article in articles:
        parsed_article = {
            "title": article["title"],
            "link": article["link"],
            "summary": article["summary"],
            "category": "Non spécifié",  # Placeholder si non disponible
            "author": "Auteur inconnu"   # Placeholder si non disponible
        }
        parsed_articles.append(parsed_article)

    # Sauvegarde en JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(parsed_articles, f, ensure_ascii=False, indent=4)

    print(f"✅ Parsing terminé ! {len(parsed_articles)} articles enregistrés dans {output_file}.")

if __name__ == "__main__":
    parse_akhbarona_articles()
