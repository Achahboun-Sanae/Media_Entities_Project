import spacy
import stanza
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Chargement des modèles
nlp_spacy = spacy.load("en_core_web_trf")
nlp_stanza = stanza.Pipeline("en", processors="tokenize,ner")
nlp_bert = pipeline("ner", model="Jean-Baptiste/roberta-large-ner-english", aggregation_strategy="simple")

# Normalisation des labels
LABEL_MAPPING = {
    "PER": "PERSON", "PERSON": "PERSON",
    "ORG": "ORG", "LOC": "LOC", "GPE": "LOC",
    "EVENT": "EVENT", "MISC": "MISC"
}

def normalize_label(label):
    return LABEL_MAPPING.get(label, label)

# Détection des entités avec les 3 modèles
def extract_entities_spacy(text):
    doc = nlp_spacy(text)
    return [(ent.text, normalize_label(ent.label_)) for ent in doc.ents]

def extract_entities_stanza(text):
    doc = nlp_stanza(text)
    return [(ent.text, normalize_label(ent.type)) for ent in doc.ents]

def extract_entities_bert(text):
    entities = nlp_bert(text)
    return [(entity["word"], normalize_label(entity["entity_group"])) for entity in entities]

# Regroupement des noms similaires (NLP-based)
def cluster_similar_names(names, threshold=0.85):
    if len(names) < 2:
        return names
    
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 3))
    tfidf = vectorizer.fit_transform(names)
    sim_matrix = cosine_similarity(tfidf)
    
    clusters = []
    visited = set()
    
    for i, name in enumerate(names):
        if i not in visited:
            similar_indices = [j for j, sim in enumerate(sim_matrix[i]) if sim >= threshold]
            if similar_indices:
                best_name = max([names[j] for j in similar_indices], key=len)
                clusters.append(best_name)
                visited.update(similar_indices)
    
    return clusters or names

# Fusion et déduplication
def merge_entities(entities_list):
    all_entities = [item for sublist in entities_list for item in sublist]
    names = [ent for ent, _ in all_entities]
    unique_names = cluster_similar_names(names)
    
    final_entities = {}
    for ent, label in all_entities:
        matched = next((u for u in unique_names if ent in u or u in ent), None)
        best_name = max(ent, matched, key=len) if matched else ent
        if best_name not in final_entities:
            final_entities[best_name] = label
    
    return list(final_entities.items())