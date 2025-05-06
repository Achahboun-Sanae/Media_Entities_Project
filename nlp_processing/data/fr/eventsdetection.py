import spacy

# Charger le modèle de langue français
nlp = spacy.load("fr_core_news_md")

# Fonction pour détecter les événements dans le titre
def traitement_titre(titre):
    doc = nlp(titre)

    # Extraire les tokens importants (lemmatisés, sans stopwords ni ponctuation)
    tokens_lemmes = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]

    # Reformuler l'événement sous forme de phrase
    event_phrase = " ".join(tokens_lemmes).strip()

    # Vérifier si la phrase extraite est un événement valide
    if event_phrase and len(event_phrase) > 3:  # On ignore les résultats trop courts
        return [event_phrase]  # Retourne une liste d'événements
    
    return []  # Retourne une liste vide si aucun événement n'est trouvé
