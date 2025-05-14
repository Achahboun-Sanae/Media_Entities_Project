import re
from nltk.corpus import stopwords
from typing import List, Tuple, Dict, Set, Any

# Stopwords français
french_stopwords = set(stopwords.words('french'))

# Nettoyage et normalisation du texte
def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)  # remove extra spaces
    text = re.sub(r"[«»“”]", '"', text)
    text = re.sub(r"–|—", "-", text)
    text = re.sub(r"\s+([?.!,;:])", r"\1", text)  # no space before punctuation
    text = re.sub(r"([?.!,;:])(?=[^\s])", r"\1 ", text)  # space after punctuation
    return text.strip()

import unicodedata

# Liste de prépositions/articles à exclure dans les noms propres
STOP_ENTITY_TOKENS = {
    'de', 'du', 'des', 'la', 'le', 'les', 'à', 'au', 'aux', "d'", "l'",
    "et", "en", "sur", "sous", "chez", "avec", "pour", "par", "dans"
}

def is_valid_entity(text: str, label: str) -> bool:
    if len(text.strip()) < 2:
        return False
    tokens = text.lower().split()
    if any(tok in STOP_ENTITY_TOKENS for tok in tokens):
        return False
    if label == "PERSON" and any(tok in STOP_ENTITY_TOKENS for tok in tokens):
        return False
    if re.fullmatch(r"[^\w\s]+", text):  # que de la ponctuation
        return False
    if len(text.split()) == 1 and not text[0].isupper():
        return False
    return True

def filter_entities(entities: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    seen = set()
    filtered = []
    for ent, label in entities:
        if (ent.lower(), label) not in seen and is_valid_entity(ent, label):
            seen.add((ent.lower(), label))
            filtered.append((ent, label))
    return filtered

