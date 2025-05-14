import re
import nltk
from nltk.corpus import stopwords

nltk.download('stopwords')

def clean_text(text):
    # Garder les points pour les acronymes
    text = re.sub(r"(?<!\w)([A-Z])\.", r"\1", text)  # Préserver les points dans les acronymes
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^a-zA-Z0-9'.\-\s]", ' ', text)  # Conserver les points
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def filter_entities(entities):
    stop_words = set(stopwords.words('english'))
    seen = set()
    filtered = []
    
    for entity, label in entities:
        # Nettoyage des entités
        entity = re.sub(r"'s\b", "", entity).strip()  # Enlever les possessifs
        entity = re.sub(r"\b([A-Za-z])\.\s?([A-Za-z])", r"\1.\2", entity)  # Corriger les acronymes
        
        if len(entity) < 2 or entity.lower() in stop_words:
            continue
            
        if entity not in seen:
            filtered.append((entity, label))
            seen.add(entity)
    
    return filtered