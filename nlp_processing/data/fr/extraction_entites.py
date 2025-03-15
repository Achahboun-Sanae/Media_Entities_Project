import spacy
import stanza
from transformers import pipeline

# Charger les modèles NLP
nlp_spacy = spacy.load("fr_core_news_lg")
nlp_stanza = stanza.Pipeline('fr', processors='tokenize,ner')
nlp_bert = pipeline("ner", model="camembert-base", tokenizer="camembert-base")
# Extraction des entités avec spaCy
def extract_entities_spacy(text):
    doc = nlp_spacy(text)
    return [(ent.text, ent.label_) for ent in doc.ents if ent.label_ in ['GPE', 'LOC', 'PERSON', 'ORG']]

# Extraction des entités avec Stanza
def extract_entities_stanza(text):
    doc = nlp_stanza(text)
    return [(ent.text, ent.type) for ent in doc.ents if ent.type in ['GPE', 'LOC', 'PER', 'ORG']]

# Extraction des entités avec Camembert (BERT)
def extract_entities_bert(text):
    entities = nlp_bert(text)
    return [(entity['word'], entity['entity']) for entity in entities if entity['entity'] in ['LOC', 'PER', 'ORG']]

# Fusion des entités issues de plusieurs modèles
def merge_entities(entities_list):
    merged_entities = {}
    for entities in entities_list:
        for entity in entities:
            if isinstance(entity, tuple) and len(entity) == 2:  # Vérifie que c'est un tuple avec 2 éléments
                entity_text, entity_label = entity
                if entity_text not in merged_entities:
                    merged_entities[entity_text] = entity_label
            
    return list(merged_entities.items())