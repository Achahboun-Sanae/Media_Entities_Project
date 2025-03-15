import os
from supabase import create_client, Client
from supabase.client import ClientOptions
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Vérifier que les variables sont bien chargées
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
print("URL récupérée:", url)

if not url or not key:
    raise ValueError("Les variables d'environnement SUPABASE_URL et SUPABASE_KEY ne sont pas définies.")

# Création du client Supabase
supabase = create_client(
    url, 
    key,
    options=ClientOptions(
        postgrest_client_timeout=10,
        storage_client_timeout=10,
        schema="public",
    )
)

print("Connexion réussie à Supabase !") 