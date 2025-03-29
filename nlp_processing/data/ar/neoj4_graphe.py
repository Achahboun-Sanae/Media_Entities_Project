
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from .connect_supabase import supabase  # Assurez-vous que la connexion Supabase est correcte

# Charger les variables d'environnement depuis le fichier .env
load_dotenv(override=True)

# Connexion à Neo4j
URI = os.getenv("NEO4J_URI")  # URI de Neo4j
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))  # Identifiants de connexion Neo4j
print("NEO4J_URI:", URI)
print("NEO4J_USERNAME:", os.getenv("NEO4J_USERNAME"))
print("NEO4J_PASSWORD:", os.getenv("NEO4J_PASSWORD"))

def normalize_relation(relation):
    """
    Fonction pour formater le nom de la relation afin d'être compatible avec Neo4j :
    - Remplace les espaces par des underscores (_)
    - Supprime les caractères non autorisés si nécessaire
    """
    return relation.replace(" ", "_")

def create_relation(tx, nom_source, type_source, nom_cible, type_cible, relation):
    relation = normalize_relation(relation)

    query = (
        "MERGE (a:{type_source} {{name: $nom_source}}) "
        "MERGE (b:{type_cible} {{name: $nom_cible}}) "
        "MERGE (a)-[r:{relation}]->(b) "
        "RETURN a, r, b"
    ).format(type_source=type_source, type_cible=type_cible, relation=relation)
    
    result = tx.run(query, nom_source=nom_source, nom_cible=nom_cible)
    for record in result:
        print(f"Insertion confirmée : {record}")



def insert_relations_into_neo4j():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        # Récupérer les relations depuis Supabase
        response = supabase.table("relations_ar").select("nom_source, type_source, nom_cible, type_cible, relation").execute()
        
        # Vérifier si la réponse est valide
        if response.data is None:
            print("Aucune donnée trouvée dans Supabase.")
            return

        relations = response.data
        
        # Insérer les relations dans Neo4j
        with driver.session() as session:
            for rel in relations:
                rel["relation"] = normalize_relation(rel["relation"])  # Normaliser avant insertion
                session.execute_write(
                    create_relation, rel["nom_source"], rel["type_source"], rel["nom_cible"], rel["type_cible"], rel["relation"]
                )
        print("✅ Relations en arabe insérées avec succès dans Neo4j")
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion dans Neo4j: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    insert_relations_into_neo4j()

