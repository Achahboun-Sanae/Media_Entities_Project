import sys
import os
import time
from itertools import combinations
from bson import ObjectId
import datetime
import spacy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase

# Chargement du modèle NLP
nlp = spacy.load("en_core_web_trf")

# Connexion à MongoDB
collection = get_mongo_atlass_collection("articles_eng")

# Fonction pour récupérer les entités depuis Supabase
def get_entites_from_supabase(article_id):
    entity_categories = {
        "personnes": "entite_en_pers",
        "lieux": "entite_en_loc",
        "organisations": "entite_en_org",
        "evenements": "entite_en_event",
    }
    entities = {}
    for cat, table in entity_categories.items():
        try:
            resp = (
                supabase
                .table(table)
                .select("nom")
                .eq("article_id", article_id)
                .execute()
            )
            entities[cat] = {e["nom"] for e in resp.data if "nom" in e}
        except Exception as e:
            print(f"⚠️ Erreur Supabase ({table}): {e}")
            entities[cat] = set()
    return entities

# Fonction pour trouver les indices des entités dans le texte
def _find_span_indices(doc, text):
    words = text.split()
    L = len(words)
    for i in range(len(doc) - L + 1):
        if [t.text for t in doc[i:i + L]] == words:
            return i, i + L
    return None

# Fonction pour détecter la relation entre deux entités
def detecter_relation(doc, span1, span2):
    head1, head2 = span1.root, span2.root
    anc1 = {a for a in head1.ancestors} | {head1}
    for a2 in [head2] + list(head2.ancestors):
        if a2 in anc1 and a2.pos_ == "VERB":
            lemma = a2.lemma_
            if lemma not in {"be", "have", "do", "say", "go", "get", "make", "know"}:
                return lemma
    return None

# Fonction principale pour extraire les entités et relations
def extraire_entites_et_relations(article_id):
    try:
        doc_mongo = collection.find_one({"_id": ObjectId(article_id)})
    except Exception as e:
        raise ValueError(f"❌ Article introuvable en MongoDB : {e}")

    if not doc_mongo:
        raise ValueError("❌ Article introuvable en MongoDB")

    texte = f"{doc_mongo.get('titre','')} {doc_mongo.get('contenu','')}"
    doc = nlp(texte)

    entites_dict = get_entites_from_supabase(article_id)
    entites = {
        (nom, cat)
        for cat, noms in entites_dict.items()
        for nom in noms
    }

    # ✅ Récupération des champs "source" et "date"
    source_media = doc_mongo.get("source", "")
    date = doc_mongo.get("date", None)
    if isinstance(date, (datetime.datetime, datetime.date)):
        date = date.isoformat()

    relations = []
    for (nom1, cat1), (nom2, cat2) in combinations(entites, 2):
        if nom1 == nom2:
            continue

        idx1 = _find_span_indices(doc, nom1)
        idx2 = _find_span_indices(doc, nom2)
        if not idx1 or not idx2:
            continue

        span1 = doc[idx1[0]:idx1[1]]
        span2 = doc[idx2[0]:idx2[1]]

        if abs(span1.start - span2.start) > 15:
            continue

        rel = detecter_relation(doc, span1, span2)
        if rel:
            # Utilisation du contexte de la relation (phrase) pour `source_title`
            sentence = span1.sent.text if span1.sent.start <= span2.start <= span1.sent.end else span2.sent.text
            relations.append({
                "source": nom1,
                "type_source": cat1,
                "cible": nom2,
                "type_cible": cat2,
                "relation": rel,
                "source_title": sentence,  # Le contexte de la relation
                "article_id": article_id,
                "media_source": source_media,   # ✅ Média source (champ "source" de MongoDB)
                "date": date      # ✅ Date formatée en ISO
            })
    return relations

# Fonction pour enregistrer les relations dans Supabase
def enregistrer_relations_dans_supabase(relations):
    for rel in relations:
        try:
            supabase.table("relations_en").insert([{
                "nom_source": rel["source"],
                "type_source": rel["type_source"],
                "nom_cible": rel["cible"],
                "type_cible": rel["type_cible"],
                "relation": rel["relation"],
                "source_title": rel["source_title"],  # Contexte de la relation
                "article_id": rel["article_id"],
                "source": rel["media_source"],         # ✅ Champ "source" (média)
                "date": rel["date"],     # ✅ Champ "date"
            }]).execute()
            print(f"✅ Relation {rel['source']} --> {rel['cible']} enregistrée.")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'enregistrement : {e}")

# Fonction pour vérifier si des relations ont déjà été enregistrées
def relations_deja_enregistrees(article_id):
    try:
        result = supabase.table("relations_en").select("id").eq("article_id", article_id).execute()
        return bool(result.data)
    except Exception as e:
        print(f"⚠️ Erreur vérification enregistrement : {e}")
        return False

# Fonction pour traiter les articles en batchs
def traiter_relations_en_batches(batch_size=300, delay=0.5, start_from_id=None):
    skip = 0
    found_start = start_from_id is None

    while True:
        articles = list(collection.find().skip(skip).limit(batch_size))
        if not articles:
            break

        for article in articles:
            article_id = str(article["_id"])
            titre = article.get("titre", "(sans titre)")

            if not found_start:
                if article_id == start_from_id:
                    found_start = True
                    print(f"🚩 Début du traitement à partir de l'article ID : {start_from_id}")
                else:
                    continue

            if relations_deja_enregistrees(article_id):
                print(f"✅ Relations déjà enregistrées pour l'article : {titre}")
                continue

            try:
                print(f"🔍 Traitement de l'article : {titre}")
                relations = extraire_entites_et_relations(article_id)
                if relations:
                    for rel in relations:
                        rel["source_title"] = rel["source_title"]  # Contexte de la relation
                        rel["article_id"] = article_id
                    enregistrer_relations_dans_supabase(relations)
            except Exception as e:
                print(f"⚠️ Erreur traitement article {titre} : {e}")

        skip += batch_size
        print(f"⏸️ Pause de {delay} secondes...")
        time.sleep(delay)

# Exécution du traitement
if __name__ == "__main__":
    print("🔍 Début du traitement des relations...")
    traiter_relations_en_batches()
    print("🎉 Traitement terminé.")
