import re

def clean_text(text):
    # Suppression des diacritiques (voyelles courtes)
    text = re.sub(r'[\u064B-\u0652]', '', text)
    # Remplacer les espaces multiples et nettoyer
    text = re.sub(r'\s+', ' ', text).strip()

    # Conservation de certains signes de ponctuation
    punctuation = r'[،؛؟!“”"\'()–—«»″]'
    text = re.sub(punctuation, ' ', text)

    # Supprimer les caractères non arabes et non numériques
    text = re.sub(r'[^\u0600-\u06FF0-9 ]', ' ', text)

 

    
    
    return text.strip()
