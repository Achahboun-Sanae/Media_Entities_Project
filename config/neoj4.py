from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

# Vérifier si les variables sont bien chargées
print("NEO4J_URI:", os.getenv("NEO4J_URI"))
print("NEO4J_USERNAME:", os.getenv("NEO4J_USERNAME"))

class Neo4jConnection:
    def __init__(self):
        """Initialise la connexion à Neo4j en chargeant les variables d'environnement."""
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        if not uri or not user or not password:
            raise ValueError("Les variables d'environnement Neo4j ne sont pas correctement chargées.")

        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Ferme la connexion."""
        if self._driver:
            self._driver.close()

    def session(self):
        """Retourne une session Neo4j."""
        return self._driver.session()

    def test_connection(self):
        """Teste la connexion en exécutant une requête simple."""
        with self.session() as session:
            result = session.run("RETURN 'Connexion réussie' AS message")
            return result.single()["message"]

# ✅ Tester la connexion avec gestion des erreurs
try:
    neo4j_conn = Neo4jConnection()
    print(neo4j_conn.test_connection())  # Doit afficher "Connexion réussie"
    neo4j_conn.close()
except Exception as e:
    print("❌ Erreur de connexion à Neo4j:", e)
