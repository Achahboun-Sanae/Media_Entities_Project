import re
from functools import lru_cache
from typing import List, Tuple, Dict, Set, Any
import spacy
import stanza
from transformers import pipeline
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import fuzz
from pretraitement import clean_text,filter_entities
from eventsdetection import traitement_titre
# Normalisation des labels NER
LABEL_MAPPING = {
    "PER": "PERSON",
    "PERS": "PERSON",
    "Person": "PERSON",
    "ORG": "ORGANIZATION",
    "ORGANISATION": "ORGANIZATION",
    "LOC": "LOCATION",
    "LIEU": "LOCATION",
    "FAC": "LOCATION",
}

def normalize_label(label: str) -> str:
    return LABEL_MAPPING.get(label.strip().upper(), "OTHER")

# Chargement des modèles
MODELS = {
    "spacy": None,
    "stanza": None,
    "bert": None
}

def load_models():
    if not MODELS["spacy"]:
        MODELS["spacy"] = spacy.load("fr_core_news_lg", disable=["parser", "lemmatizer"])
        MODELS["spacy"].add_pipe("merge_entities")
    if not MODELS["stanza"]:
        MODELS["stanza"] = stanza.Pipeline("fr", processors="tokenize,ner", use_gpu=False, verbose=False)
    if not MODELS["bert"]:
        MODELS["bert"] = pipeline(
            "ner",
            model="Jean-Baptiste/camembert-ner",
            tokenizer="Jean-Baptiste/camembert-ner",
            aggregation_strategy="max",
            device=-1
        )

load_models()

# Extraction d'entités avec chaque modèle
@lru_cache(maxsize=512)
def extract_entities_spacy(text: str) -> List[Tuple[str, str]]:
    doc = MODELS["spacy"](text)
    return [(ent.text.strip(), normalize_label(ent.label_)) for ent in doc.ents]

def extract_entities_stanza(text: str) -> List[Tuple[str, str]]:
    doc = MODELS["stanza"](text)
    return [(ent.text.strip(), normalize_label(ent.type)) for ent in doc.ents]

def extract_entities_bert(text: str) -> List[Tuple[str, str]]:
    entities = MODELS["bert"](text[:1024])
    return [
        (entity["word"].replace("▁", " ").strip(), normalize_label(entity["entity_group"]))
        for entity in entities
        if entity["word"].strip()
    ]

# Détection d'acronymes améliorée
def is_acronym(a: str, b: str) -> bool:
    a_clean = re.sub(r"[^a-zA-Z]", "", a.upper())
    b_clean = re.sub(r"[^a-zA-Z]", "", b.upper())
    
    if a_clean == b_clean or min(len(a_clean), len(b_clean)) < 2:
        return False
    
    short, long = sorted([a_clean, b_clean], key=len)
    long_words = re.split(r"[\s-]+", long)
    initials = "".join([word[0] for word in long_words if word])
    
    return short == initials or short in long

# Clustering des entités similaires
def cluster_similar_names(names: List[str]) -> List[str]:
    if len(names) < 2:
        return names
    
    normalized = [re.sub(r"[^a-zA-Z]", "", n.lower()) for n in names]
    
    # Matrice de similarité combinée
    tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3)).fit_transform(names)
    tfidf_sim = cosine_similarity(tfidf)
    
    # Construction du graphe de similarité
    graph: Dict[int, Set[int]] = {i: set() for i in range(len(names))}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if (
                tfidf_sim[i][j] >= 0.75
                or fuzz.ratio(normalized[i], normalized[j]) >= 85
                or is_acronym(names[i], names[j])
            ):
                graph[i].add(j)
                graph[j].add(i)
    
    # Détection des clusters
    clusters: List[Set[int]] = []
    visited: Set[int] = set()
    
    for i in range(len(names)):
        if i not in visited:
            cluster = set()
            stack = [i]
            while stack:
                node = stack.pop()
                if node not in visited:
                    visited.add(node)
                    cluster.add(node)
                    stack.extend(graph[node] - visited)
            clusters.append(cluster)
    
    # Sélection du meilleur représentant
    results: List[str] = []
    for cluster in clusters:
        candidates = [names[i] for i in cluster]
        best = max(
            candidates,
            key=lambda x: (
                len(x),
                sum(1 for c in x if c.isupper()),
                -len(x.split()),
                x.count(" "),
            ),
        )
        results.append(best)
    
    return results

# Fusion des résultats
def merge_entities(entities_list: List[List[Tuple[str, str]]]) -> List[Tuple[str, str]]:
    entity_map: Dict[str, Dict[str, int]] = {}
    model_weights = {"spacy": 2, "stanza": 2, "bert": 3}
    
    for model_idx, entities in enumerate(entities_list):
        model_name = ["spacy", "stanza", "bert"][model_idx]
        for text, label in entities:
            clean_text = re.sub(r"\s+", " ", text.strip())
            if len(clean_text) < 2:
                continue
                
            weight = model_weights[model_name]
            if clean_text not in entity_map:
                entity_map[clean_text] = {}
            entity_map[clean_text][label] = entity_map[clean_text].get(label, 0) + weight
    
    # Sélection du label dominant
    priority = ["PERSON", "ORGANIZATION", "LOCATION", "EVENT"]
    final_entities = {}
    for text, labels in entity_map.items():
        sorted_labels = sorted(
            labels.items(),
            key=lambda x: (-x[1], priority.index(x[0]) if x[0] in priority else 999),
        )
        final_entities[text] = sorted_labels[0][0]
    
    # Clustering final
    names = list(final_entities.keys())
    clusters = cluster_similar_names(names)
    
    # Fusion des clusters
    merged = {}
    for cluster in clusters:
        candidates = [name for name in names if fuzz.ratio(name.lower(), cluster.lower()) >= 75]
        labels = [final_entities[name] for name in candidates]
        main_label = max(set(labels), key=lambda x: (labels.count(x), priority.index(x) if x in priority else 999))
        best_form = max(candidates, key=lambda x: (len(x), x.count(" ")))
        merged[best_form] = main_label
    
    return list(merged.items())


# Pipeline principal
# def extract_named_entities(text: str) -> Dict[str, List[str]]:
#     cleaned_text = clean_text(text)
    
#     # Extraction multi-modèle
#     ents = [
#         extract_entities_spacy(cleaned_text),
#         extract_entities_stanza(cleaned_text),
#         extract_entities_bert(cleaned_text),
#     ]
    
#     # Fusion et filtrage
#     merged = merge_entities(ents)
#     filtered = filter_entities(merged)
    
#     # Organisation des résultats
#     categories = {
#         "persons": [],
#         "locations": [],
#         "organizations": [],
#         "events": [],
#     }
    
#     for entity, label in filtered:
#         if label == "PERSON":
#             categories["persons"].append(entity)
#         elif label == "LOCATION":
#             categories["locations"].append(entity)
#         elif label == "ORGANIZATION":
#             categories["organizations"].append(entity)
#         elif label == "EVENT":
#             categories["events"].append(entity)
  
#     # Appel à traitement_titre si aucun événement détecté
#     if not categories["events"]:
#         try:
#             titre_events = traitement_titre(titre)
#             if isinstance(titre_events, list):
#                 categories["events"].extend(titre_events)
#             elif isinstance(titre_events, str):
#                 categories["events"].append(titre_events)
#         except Exception as e:
#             print(f"Erreur lors du traitement du titre: {e}")
   
#     # Post-traitement final avec dédoublonnage
#     return {
#         "persons": sorted(list(set(categories["persons"]))),
#         "locations": sorted(list(set(categories["locations"]))),
#         "organizations": sorted(list(set(categories["organizations"]))),
#         "events": sorted(list(set(
#             [e.strip() for e in categories["events"] if len(e.strip()) > 2]
#         ))),
#     }
