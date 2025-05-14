import re
import sys 
import os 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from config.supabasedb import supabase

def clean_text(text):
    """Remplacer les caractères ':', ',', ';' et '@' par un espace."""
    if not text:
        return text

    # Remplace chaque caractère ciblé par un espace
    return re.sub(r'[:;,@]', '', text)

def update_entite_en_event_by_id(article_id_target):
    # Récupérer l'article par ID
    rows = supabase.table("entite_en_event").select("id, nom").eq("article_id", article_id_target).execute().data

    if not rows:
        print(f"Aucune donnée trouvée pour l'article ID {article_id_target}.")
        return

    total_updated = 0
    for row in rows:
        article_id = row["id"]
        nom = row["nom"]

        if nom:
            cleaned_nom = clean_text(nom)

            if cleaned_nom != nom:
                supabase.table("entite_en_event").update({"nom": cleaned_nom}).eq("id", article_id).execute()
                print(f"🔄 Mise à jour de l'article {article_id}: '{nom}' → '{cleaned_nom}'")
                total_updated += 1
            else:
                print(f"ℹ️ Aucun changement nécessaire pour l'article {article_id}.")
    
    print(f"\n✅ Terminé : {total_updated} nom mis à jour.")

if __name__ == "__main__":
    update_entite_en_event_by_id("6808994c23ce73c099952b7f")
