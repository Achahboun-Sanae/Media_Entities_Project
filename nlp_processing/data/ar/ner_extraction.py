from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

# Charger le modèle BERT pour la NER arabe
model_name = "hatmimoha/arabic-ner"
model = AutoModelForTokenClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
nlp_ner = pipeline("ner", model=model, tokenizer=tokenizer)

def extract_entities_bert(text):
    ner_results = nlp_ner(text)
    entities = [(result['word'], result['entity']) for result in ner_results]
    return entities