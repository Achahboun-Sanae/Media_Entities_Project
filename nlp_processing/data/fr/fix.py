import sys
import os
import re
from bson import ObjectId
import spacy
from itertools import combinations
from spacy.tokens import Span
from collections import defaultdict
from datetime import datetime

# Configuration des chemins
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase

# Chargement du modèle spaCy
nlp = spacy.load("fr_core_news_lg")

# Connexion MongoDB
collection = get_mongo_atlass_collection("articles_fr")

# Dictionnaire de mapping des prépositions
PREP_MAPPING = {
    'à': 'a lieu à',
    'dans': 'se déroule dans',
    'par': 'organisé par',
    'de': 'associé à',
    'avec': 'en collaboration avec',
    'pour': 'destiné à',
    'sur': 'concernant'
}

def get_entites_from_supabase(article_id):
    """Récupère les entités depuis Supabase par catégorie"""
    entites = defaultdict(list)
    tables = {
        "personnes": "entite_fr_pers",
        "lieux": "entite_fr_loc",
        "organisations": "entite_fr_org",
        "evenements": "entite_fr_event"
    }
    for cat, table in tables.items():
        res = supabase.table(table).select("nom").eq("article_id", article_id).execute()
        entites[cat] = list({e["nom"].strip() for e in res.data if e["nom"].strip()})
    return entites

def annotate_entities(doc, entites):
    """Annotation des entités avec gestion des chevauchements"""
    from spacy.matcher import PhraseMatcher
    from spacy.util import filter_spans

    # Mapping des catégories
    category_mapping = {
        'personnes': 'PER',
        'lieux': 'LOC',
        'organisations': 'ORG',
        'evenements': 'EVENT'
    }

    # Création du matcher avec matching insensible à la casse
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    spans = []

    # Ajout des motifs pour chaque catégorie
    for cat, names in entites.items():
        label = category_mapping.get(cat)
        if not label or not names:
            continue
        
        # Création des patterns pour la catégorie
        patterns = [nlp.make_doc(name.strip()) for name in names if name.strip()]
        if patterns:
            matcher.add(label, patterns)

    # Recherche des correspondances
    matches = matcher(doc)
    for match_id, start, end in matches:
        label = nlp.vocab.strings[match_id]
        span = Span(doc, start, end, label=label)
        spans.append(span)

    # Filtrage des chevauchements et doublons
    filtered_spans = filter_spans(spans)  # Garde les spans les plus longs
    unique_spans = []
    seen = set()
    
    for span in filtered_spans:
        ident = (span.start, span.end, span.label_)
        if ident not in seen:
            seen.add(ident)
            unique_spans.append(span)

    # Définition des entités dans le doc
    doc.ents = unique_spans
    return doc
def obtenir_relation(ent1, ent2, sent):
    """Détection des relations améliorée avec prépositions et verbes"""
    root1 = ent1.root
    root2 = ent2.root

    # Vérification des prépositions
    for token in sent:
        if token.dep_ == 'prep':
            if token.head == root1:
                for child in token.children:
                    if child == root2 and child.dep_ == 'pobj':
                        return PREP_MAPPING.get(token.text.lower(), token.text)
            elif token.head == root2:
                for child in token.children:
                    if child == root1 and child.dep_ == 'pobj':
                        return PREP_MAPPING.get(token.text.lower(), token.text)

    # Recherche d'un ancêtre verbal commun
    ancestors1 = {anc for anc in root1.ancestors}
    for anc in root2.ancestors:
        if anc in ancestors1 and anc.pos_ == 'VERB':
            return anc.lemma_.lower()

    # Vérification des verbes enfants directs
    for token in sent:
        if token.pos_ == 'VERB':
            if root1 in token.children and root2 in token.children:
                return token.lemma_.lower()

    # Défaut pour les relations non détectées
    return "en relation avec"

def extraire_relations(texte, entites, source_media, date):
    """Extraction des relations entre événements et autres entités"""
    doc = nlp(texte)
    doc = annotate_entities(doc, entites)
    relations = []
    
    for sent in doc.sents:
        spans = [e for e in doc.ents if sent.start <= e.start < sent.end]
        events = [e for e in spans if e.label_ == 'EVENT']  # Modifié ici
        others = [e for e in spans if e.label_ in ['PER', 'LOC', 'ORG']]  # Modifié ici
        
        for event, other in combinations(events + others, 2):
            relation_data = None
            if event.label_ == 'EVENT' and other.label_ != 'EVENT':  # Modifié ici
                rel = obtenir_relation(event, other, sent)
                relation_data = {
                    'nom_source': event.text,
                    'type_source': event.label_,
                    'relation': rel,
                    'nom_cible': other.text,
                    'type_cible': other.label_,
                    'source_title': sent.text,
                    'source': source_media,
                    'date': date
                }
            elif other.label_ == 'EVENT' and event.label_ != 'EVENT':  # Modifié ici
                rel = obtenir_relation(other, event, sent)
                relation_data = {
                    'nom_source': other.text,
                    'type_source': other.label_,
                    'relation': rel,
                    'nom_cible': event.text,
                    'type_cible': event.label_,
                    'source_title': sent.text,
                    'source': source_media,
                    'date': date
                }
            
            if relation_data:
                relations.append(relation_data)
    
    return relations

def enregistrer_relations_supabase(article_id, relations):
    """Enregistre les relations dans Supabase avec vérification des doublons"""
    BATCH_SIZE = 500
    for i in range(0, len(relations), BATCH_SIZE):
        batch = relations[i:i+BATCH_SIZE]
        
        # Vérification des doublons
        existing = supabase.table("relations_fr").select("*").eq("article_id", article_id).execute()
        existing_relations = {(r['nom_source'], r['nom_cible'], r['relation']) for r in existing.data}
        
        # Filtrage des nouvelles relations
        new_relations = [
            {**rel, 'article_id': article_id} 
            for rel in batch 
            if (rel['nom_source'], rel['nom_cible'], rel['relation']) not in existing_relations
        ]
        
        if new_relations:
            try:
                supabase.table("relations_fr").insert(new_relations).execute()
                print(f"✅ {len(new_relations)} relations insérées")
            except Exception as e:
                print(f"❌ Erreur d'insertion : {str(e)}")

def traiter_tous_les_articles():
    """Parcours de tous les articles et extraction/enregistrement des relations"""
 # ID de départ
    id_depart = ObjectId("680beff8aa9ac53672378f2c")

    # Trouver tous les documents à partir de cet ID
    cursor = collection.find(
        {'_id': {'$gte': id_depart}},
        {'titre': 1, 'contenu': 1, '_id': 1, 'source': 1, 'date': 1}
    )

    total_articles = 0
    total_relations = 0

    for art in cursor:
        article_id = str(art['_id'])
        titre = art.get('titre', '').strip()
        contenu = art.get('contenu', '').strip()
        source_media = art.get('source', '')
        date = art.get('date', datetime.now().isoformat())

        if isinstance(date, datetime):
            date = date.isoformat()

        if not contenu:
            continue  # Ignorer les articles vides

        texte = f"{titre}. {contenu}" if not titre.endswith(('.', '!', '?')) else f"{titre} {contenu}"
        entites = get_entites_from_supabase(article_id)

        print(f"\n🔍 Traitement de l'article [{titre[:50]}...] (ID: {article_id})")
        relations = extraire_relations(texte, entites, source_media, date)

        if relations:
            enregistrer_relations_supabase(article_id, relations)
            total_relations += len(relations)
            print(f"💾 {len(relations)} relations enregistrées")
        else:
            print("⚠️ Aucune relation détectée")

        total_articles += 1

    print(f"\n✅ Traitement terminé : {total_articles} articles parcourus, {total_relations} relations enregistrées.")


if __name__ == '__main__':
    traiter_tous_les_articles()
