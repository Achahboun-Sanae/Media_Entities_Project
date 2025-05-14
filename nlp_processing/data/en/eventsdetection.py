import spacy
from spacy import displacy

# Chargement du modèle spaCy transformer
nlp = spacy.load("en_core_web_trf")

def remove_duplicate_words(text):
    """Supprime les doublons successifs dans une phrase (insensible à la casse)"""
    words = text.split()
    seen = set()
    result = []
    for word in words:
        if word.lower() not in seen:
            result.append(word)
            seen.add(word.lower())
    return " ".join(result)

def traitement_titre(title):
    """Extrait la proposition principale (événement) d'un titre en anglais"""

    doc = nlp(title)
    
    # Stratégie 1: Extraire la clause avec un verbe principal
    for sent in doc.sents:
        verbs = [token for token in sent 
                 if token.pos_ == "VERB" and token.dep_ in ("ROOT", "acl", "relcl")]
        
        if verbs:
            main_verb = verbs[0]
            clause = list(main_verb.subtree)  # Pas besoin de rajouter main_verb
            clause_sorted = sorted(clause, key=lambda x: x.i)
            text = " ".join([t.text for t in clause_sorted]).strip()
            return remove_duplicate_words(text)

    # Stratégie 2: Fallback - plus longue phrase nominale
    noun_phrases = [chunk.text for chunk in doc.noun_chunks]
    if noun_phrases:
        return remove_duplicate_words(max(noun_phrases, key=len))

    # Stratégie 3: Fallback final - segment central
    words = [t.text for t in doc if not t.is_punct]
    mid = len(words) // 2
    segment = " ".join(words[max(0, mid-3):min(len(words), mid+4)])
    return remove_duplicate_words(segment)
