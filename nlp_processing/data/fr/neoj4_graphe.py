import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Ajouter le chemin du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from config.supabasedb import supabase
from config.neoj4 import Neo4jConnection  # Import de la connexion Neo4j

# Initialiser la connexion Neo4j
neo4j_conn = Neo4jConnection()

# Fonction pour récupérer tous les article_id distincts depuis la table relations_fr
import os

def get_all_article_ids():
    """Récupère tous les article_id distincts depuis la table relations_fr et ignore ceux déjà traités."""
    
    # Fichier où les article_id traités sont enregistrés
    processed_file = "processed_article_ids.txt"
    
    # Lire les article_id déjà traités depuis le fichier
    if os.path.exists(processed_file):
        with open(processed_file, "r") as f:
            processed_article_ids = set(f.read().splitlines())
    else:
        processed_article_ids = set()

    # Récupérer les article_id depuis Supabase
    response = supabase.table("relations_fr").select("article_id").execute()

    if not hasattr(response, "data") or not response.data:
        print("⚠️ Aucune donnée trouvée pour les article_id.")
        return []
    
    # Extraire les article_id distincts
    article_ids = {item["article_id"] for item in response.data}

    # Filtrer pour ignorer les article_id déjà traités
    new_article_ids = list(article_ids - processed_article_ids)
    
    print(f"Article IDs récupérés (non traités) : {new_article_ids}")  # Débogage pour vérifier les nouveaux article_ids
    return new_article_ids

def mark_article_as_processed(article_id):
    """Marque un article_id comme traité en l'ajoutant dans le fichier."""
    processed_file = "processed_article_ids.txt"
    
    with open(processed_file, "a") as f:
        f.write(f"{article_id}\n")
    print(f"Article ID {article_id} marqué comme traité.")

# Fonction pour récupérer les relations depuis Supabase, avec les noms des entités source et cible
def get_relations_from_supabase(article_id):
    """Récupère les relations associées à un article avec les noms des entités source et cible."""
    response = supabase.table("relations_fr").select("*").eq("article_id", article_id).execute()

    if not hasattr(response, "data") or not response.data:
        print(f"⚠️ Aucune relation trouvée pour l'article {article_id}.")
        return []
    
    print(f"Relations récupérées : {response.data}")  # Débogage pour vérifier les données récupérées
    relations = []
    
    for relation in response.data:
        id_source = relation["id_source"]
        id_cible = relation["id_cible"]

        # Récupérer les noms des entités source et cible en fonction de leur type
        source_data = None
        cible_data = None
        
        if relation["type_source"] == "personne":
            source_data = supabase.table("entite_fr_pers").select("nom").eq("id", id_source).execute()
        elif relation["type_source"] == "organisation":
            source_data = supabase.table("entite_fr_org").select("nom").eq("id", id_source).execute()
        elif relation["type_source"] == "lieu":
            source_data = supabase.table("entite_fr_loc").select("nom").eq("id", id_source).execute()
        elif relation["type_source"] == "evenement":
            source_data = supabase.table("entite_fr_event").select("nom").eq("id", id_source).execute()

        if relation["type_cible"] == "personne":
            cible_data = supabase.table("entite_fr_pers").select("nom").eq("id", id_cible).execute()
        elif relation["type_cible"] == "organisation":
            cible_data = supabase.table("entite_fr_org").select("nom").eq("id", id_cible).execute()
        elif relation["type_cible"] == "lieu":
            cible_data = supabase.table("entite_fr_loc").select("nom").eq("id", id_cible).execute()
        elif relation["type_cible"] == "evenement":
            cible_data = supabase.table("entite_fr_event").select("nom").eq("id", id_cible).execute()

        # Vérification si les noms existent et sont récupérés
        nom_source = source_data.data[0]["nom"] if source_data and source_data.data else "Inconnu"
        nom_cible = cible_data.data[0]["nom"] if cible_data and cible_data.data else "Inconnu"

        # Ajouter la relation avec les noms des entités
        relations.append({
            "id_source": id_source,
            "nom_source": nom_source,
            "id_cible": id_cible,
            "nom_cible": nom_cible,
            "relation": relation["relation"],
            "article_id": relation["article_id"]
        })
    
    return relations

# Fonction pour insérer les relations dans Neo4j
def inserer_relations_dans_neo4j(relations):
    """Insère toutes les relations dans Neo4j."""
    with neo4j_conn.session() as session:
        print("Connexion à Neo4j établie")  # Débogage de la connexion
        for relation in relations:
            session.execute_write(creer_relation, relation)

# Fonction pour créer une relation entre deux entités dans Neo4j
def creer_relation(tx, relation):
    """Crée une relation entre deux entités dans Neo4j."""
    id_source = relation.get("id_source")
    id_cible = relation.get("id_cible")
    nom_source = relation.get("nom_source", "Inconnu")
    nom_cible = relation.get("nom_cible", "Inconnu")
    relation_type = relation.get("relation", "ASSOCIE_A")

    print(f"Insertion relation : {id_source} -> {id_cible}, {nom_source} -> {nom_cible}")  # Débogage

    if id_source and id_cible:
        # Créer les entités si elles n'existent pas et ajouter la relation
        tx.run("""
        MERGE (e1:Entite {id: $id1, nom: $nom_source})
        MERGE (e2:Entite {id: $id2, nom: $nom_cible})
        MERGE (e1)-[r:RELATION {type: $type, article_id: $article_id}]->(e2)
        """, id1=id_source, id2=id_cible, type=relation_type, nom_source=nom_source, nom_cible=nom_cible, article_id=relation["article_id"])
    else:
        print(f"❌ Relation ignorée : ID manquant {relation}")

# Fonction principale pour traiter tous les articles
def main():
    # Récupérer tous les article_id
    article_ids = get_all_article_ids()

    if not article_ids:
        print("Aucun article à traiter.")
        return

    # Traiter chaque article
    for article_id in article_ids:
        # Récupérer les relations depuis Supabase
        relations = get_relations_from_supabase(article_id)

        if relations:
            # Insérer les relations dans Neo4j
            inserer_relations_dans_neo4j(relations)
        else:
            print(f"Aucune relation à insérer pour l'article {article_id}.")

    # Fermer la connexion Neo4j
    neo4j_conn.close()

# Appel à la fonction principale
if __name__ == "__main__":
    main()
