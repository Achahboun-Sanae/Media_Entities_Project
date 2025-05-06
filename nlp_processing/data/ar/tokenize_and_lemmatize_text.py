
import stanza

# Charger le modèle Stanza pour l'arabe
stanza.download('ar')
nlp_stanza = stanza.Pipeline('ar', processors='tokenize,mwt,pos,lemma')

# Fonction améliorée de tokenisation et lemmatisation
def tokenize_and_lemmatize_text(text, debug=False):
    """
    Tokenise et lemmatise un texte arabe avec Stanza.
    
    Args:
        text (str): Texte en entrée.
        debug (bool): Si True, affiche les résultats.

    Returns:
        tokens (list): Liste des mots tokenisés.
        lemmatized_tokens (list): Liste des mots après lemmatisation.
    """
    doc = nlp_stanza(text)
    
    tokens = []
    lemmatized_tokens = []
    
    for sentence in doc.sentences:
        for word in sentence.words:
            # Ignorer les symboles et ponctuations
            if word.text.isalnum():
                tokens.append(word.text)
                lemmatized_tokens.append(word.lemma if word.lemma else word.text)

    if debug:
        print("Tokens :", tokens)
        print("Lemmatisation :", lemmatized_tokens)
    
    return tokens, lemmatized_tokens


