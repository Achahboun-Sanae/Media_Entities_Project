import os
import sys
from dotenv import load_dotenv
import datetime

# Charger les variables d'environnement
load_dotenv()

# Ajouter le chemin du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from config.supabasedb import supabase
from config.neo4j_en import Neo4jConnection  # Import de la connexion Neo4j

def extract_and_create_graph():
    try:
        # Connexion à Neo4j
        neo4j_conn = Neo4jConnection()

        # Pagination : initialisation des variables
        limit = 10000
        offset = 61775
        has_more = True

        while has_more:
            # Récupérer un lot de relations depuis Supabase
            relations_result = supabase.table("relations_en").select("*").range(offset, offset + limit - 1).execute()

            # Vérifier s'il y a des données
            if not relations_result.data:
                print("❌ Aucune donnée trouvée dans relations_en.")
                break

            print(f"🔍 {len(relations_result.data)} relations récupérées à partir de {offset}.")

            # Traiter chaque relation et ajouter des nœuds et relations dans Neo4j
            for relation in relations_result.data:
                required_fields = ['nom_source', 'type_source', 'nom_cible', 'type_cible', 'relation', 'article_id']
                if not all(field in relation for field in required_fields):
                    print(f"⚠️ Relation incomplète ignorée : {relation}")
                    continue

                nom_source = relation['nom_source']
                type_source = relation['type_source']
                nom_cible = relation['nom_cible']
                type_cible = relation['type_cible']
                relation_type = relation['relation']
                article_id = relation['article_id']

                # Créer les entités et relations dans Neo4j
                neo4j_conn.create_entity(nom_source, type_source)
                neo4j_conn.create_entity(nom_cible, type_cible)

                neo4j_conn.create_relation(
                    source_name=nom_source, source_type=type_source,
                    target_name=nom_cible, target_type=type_cible,
                    relation_type=relation_type, article_id=article_id
                )

            # Si moins de 1000 relations récupérées, c'est qu'on est arrivé à la fin
            if len(relations_result.data) < limit:
                has_more = False
            else:
                offset += limit

        print("🎉 Création du graphe Neo4j terminée avec succès.")

    except Exception as e:
        print(f"❌ Erreur lors de la création du graphe : {e}")


if __name__ == "__main__":
    extract_and_create_graph()
