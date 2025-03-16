import re
from nltk.corpus import stopwords

# Stopwords français
french_stopwords = set(stopwords.words('french'))

# Fonction pour nettoyer le texte
def clean_text(text):
    # Remplacer les apostrophes par des espaces pour éviter la fusion des mots
    text = text.replace("’", "'")  
    text = re.sub(r"\s+", " ", text).strip()  # Supprimer les espaces multiples
    text = re.sub(r"([.,;!?“”\"()–—«»])", " ", text)  # Supprimer ponctuation sauf apostrophes et traits d’union
    text = re.sub(r"(\s'\s)|(\s-\s)", " ", text)  # Corriger les espaces autour des apostrophes et traits d'union
    text = re.sub(r"[^a-zA-ZÀ-ÿ0-9'’\- ]", "", text)  # Garder apostrophes et traits d’union
    return text.strip()

# Filtrage et normalisation des entités
def filter_entities(entities):
    filtered_entities = []
    seen_entities = set()
    label_mapping = {'PER': 'PERSON', 'LOC': 'LOCATION', 'ORG': 'ORGANIZATION', 'MISC': 'EVENT'}
    
    for entity, label in entities:
        if len(entity) < 2 or entity.lower() in french_stopwords:
            continue
        
        # Si l'entité est composée de plusieurs noms, la séparer en entités distinctes
        entity_parts = entity.split('  ')  # Sépare les entités par des doubles espaces
        
        for part in entity_parts:
            if len(part.strip()) < 2:
                continue  # Ignorer les entités trop courtes
            mapped_label = label_mapping.get(label, label)
            if part not in seen_entities:
                filtered_entities.append((part.strip(), mapped_label))
                seen_entities.add(part.strip())
    
    return filtered_entities