import spacy

# Charger le modèle français
nlp = spacy.load("fr_core_news_lg")

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

def traitement_titre(titre):
    """Extrait la proposition principale (événement) d'un titre en français"""
    
    # Retirer le préfixe thématique avant les ":"
    if ":" in titre:
        titre = titre.split(":", 1)[-1].strip()
    
    doc = nlp(titre)

    # Stratégie 1 : Extraire la clause autour du verbe principal
    for sent in doc.sents:
        verbs = [t for t in sent if t.pos_ == "VERB" and t.dep_ in {"ROOT", "acl", "relcl"}]
        if verbs:
            main_verb = verbs[0]
            subtree = list(main_verb.subtree)
            sorted_clause = sorted(subtree, key=lambda x: x.i)
            phrase = " ".join([t.text for t in sorted_clause])
            return remove_duplicate_words(phrase)

    # Stratégie 2 : Retomber sur le plus grand groupe nominal
    noun_phrases = [chunk.text for chunk in doc.noun_chunks]
    if noun_phrases:
        return remove_duplicate_words(max(noun_phrases, key=len))

    # Stratégie 3 : Retomber sur un segment central
    words = [t.text for t in doc if not t.is_punct]
    mid = len(words) // 2
    segment = " ".join(words[max(0, mid - 3): min(len(words), mid + 4)])
    return remove_duplicate_words(segment)


