import os
import sys
import time
import datetime
from bson import ObjectId
import spacy
from itertools import combinations
from collections import defaultdict

# Configuration des chemins
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from config.mongo_atlass import get_mongo_atlass_collection
from config.supabasedb import supabase

# Chargement du modèle français
nlp = spacy.load("fr_core_news_lg")

# Connexion à MongoDB
collection = get_mongo_atlass_collection("articles_fr")

def get_entites_from_supabase(article_id):
    """Récupère les entités depuis Supabase"""
    entites = defaultdict(list)
    tables = {
        "personnes": "entite_fr_pers",
        "lieux": "entite_fr_loc",
        "organisations": "entite_fr_org",
        "evenements": "entite_fr_event"
    }

    try:
        for categorie, table in tables.items():
            reponse = supabase.table(table).select("nom").eq("article_id", article_id).execute()
            entites[categorie] = [entite['nom'] for entite in reponse.data if 'nom' in entite]
    except Exception as e:
        print(f"Erreur lors de la récupération des entités : {str(e)}")

    return entites

def extraire_relations(titre, contenu, entites, source_media, date):
    """Extrait les relations entre les entités et ajoute source et date"""
    doc = nlp(f"{titre} {contenu}")
    relations = []
    seen_relations = set()  # Set pour vérifier les doublons

    # On normalise les entités récupérées depuis Supabase pour comparer avec les entités extraites du texte
    entites_normalisees = {ent.lower() for categorie in entites.values() for ent in categorie}

    # On ne garde que les entités présentes dans Supabase et excluons 'MISC' et autres catégories non pertinentes
    entites_doc = {ent.text.lower(): ent for ent in doc.ents if ent.text.lower() in entites_normalisees and ent.label_ in ["ORG", "PER", "LOC", "EVENT"]}

    for sent in doc.sents:
        entites_phrase = [entites_doc[ent.text.lower()] for ent in sent.ents if ent.text.lower() in entites_doc]
        
        for ent1, ent2 in combinations(entites_phrase, 2):
            relation = obtenir_relation_par_verbe(ent1, ent2, sent)
            
            if relation:
                # Crée une clé unique pour la relation (source, cible, relation)
                relation_key = (ent1.text.lower(), ent2.text.lower(), relation)
                if relation_key not in seen_relations:
                    relations.append({
                        "nom_source": ent1.text,
                        "type_source": ent1.label_,
                        "nom_cible": ent2.text,
                        "type_cible": ent2.label_,
                        "relation": relation,
                        "source_title": sent.text,
                        "source": source_media,         # ✅ Champ source média
                        "date": date      # ✅ Champ date
                    })
                    seen_relations.add(relation_key)

    return relations

def obtenir_relation_par_verbe(ent1, ent2, sent):
    """Trouve une relation entre deux entités à partir d'un verbe"""
    for token in sent:
        if token.pos_ == "VERB":
            if ent1.root in token.subtree or ent2.root in token.subtree:
                phrase_verbe = [token.text]
                for child in token.children:
                    if child.dep_ in {"aux", "aux:tense", "advmod", "mark"}:
                        phrase_verbe.insert(0, child.text)
                    elif child.dep_ in {"obj", "xcomp", "obl"}:
                        phrase_verbe.append(child.text)
                phrase = " ".join(phrase_verbe[:3])
                return phrase.lower()
    return None

def enregistrer_relations_supabase(article_id, relations, batch_size=300, delay=0.5):
    """Enregistre les relations dans la table Supabase relations_fr par batchs sans doublons"""
    total = len(relations)
    print(f"Enregistrement de {total} relations pour l'article {article_id}...")

    for i in range(0, total, batch_size):
        batch = relations[i:i + batch_size]

        # Vérification des doublons avant d'ajouter chaque relation
        for rel in batch:
            rel["article_id"] = article_id

            # Vérification si la relation existe déjà
            existing_relation = supabase.table("relations_fr").select("id").eq("nom_source", rel["nom_source"]).eq("nom_cible", rel["nom_cible"]).eq("relation", rel["relation"]).eq("article_id", article_id).execute()
            if existing_relation.data:
                print(f"⚠️ Relation déjà existante pour {rel['nom_source']} → {rel['relation']} → {rel['nom_cible']}, sautée.")
                continue  # Ignorer cette relation si elle existe déjà

        try:
            response = supabase.table("relations_fr").insert(batch).execute()
            if response.error:
                print(f"⚠️ Erreur lors de l'insertion du batch {i // batch_size + 1}: {response.error.message}")
            else:
                print(f"✅ Batch {i // batch_size + 1} inséré. Pause de {delay} seconde(s)...")
        except Exception as e:
            print(f"Erreur inattendue lors de l'insertion du batch {i // batch_size + 1}: {e}")

        time.sleep(delay)
def traiter_tous_les_articles(start_id=None):
    """Point d'entrée principal pour traiter tous les articles"""
    # Vérifie si start_id est fourni, sinon récupère tous les articles
    if start_id:
        article_id = ObjectId(start_id)
    else:
        article_id = None

    # Construction du filtre de recherche : on cherche tous les articles à partir de start_id
    query = {}
    if article_id:
        query["_id"] = {"$gte": article_id}  # Récupère tous les articles à partir de start_id

    # Récupère tous les articles correspondant au filtre
    articles = collection.find(query)

    count = 0

    # Traiter chaque article
    for article in articles:
        article_id = str(article["_id"])
        titre = article.get("titre", "")
        contenu = article.get("contenu", "")
        source_media = article.get("source", "")   # ✅ Récupération champ "source"
        date = article.get("date", None)

        if isinstance(date, (datetime.datetime, datetime.date)):
            date = date.isoformat()

        entites = get_entites_from_supabase(article_id)
        if not any(entites.values()):
            print(f"⚠️ Aucune entité trouvée pour l'article {article_id}, skipping...")
            continue
        
        relations = extraire_relations(titre, contenu, entites, source_media, date)
        if not relations:
            print(f"⚠️ Aucune relation trouvée pour l'article {article_id}, skipping...")
            continue

        
        # Enregistrement des relations dans Supabase
        enregistrer_relations_supabase(article_id, relations)

        print(f"\n📰 Article : {titre}")
        print("🔗 Relations extraites :")
        for relation in relations:
            print(f"{relation['nom_source']} → {relation['relation']} → {relation['nom_cible']}")
            print(f"Contexte : '{relation['source_title']}'\n")
        
        count += 1

    print(f"\n✅ Traitement terminé : {count} article(s) traité(s).")

if __name__ == "__main__":
    # Utiliser un start_id spécifique, ou None pour traiter tous les articles
    traiter_tous_les_articles()  # Remplacer par votre start_id ou None
