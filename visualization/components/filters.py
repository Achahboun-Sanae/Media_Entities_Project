import streamlit as st
from datetime import datetime
from pymongo import MongoClient

def source_filter(collection, default_sources=None):
    """
    Filtre multi-sélection des sources médiatiques
    avec gestion des erreurs et valeurs par défaut
    """
    try:
        sources = collection.distinct("source")
        if not sources:
            st.warning("Aucune source disponible dans la collection")
            return []
            
        return st.multiselect(
            "Sources médiatiques",
            options=sources,
            default=default_sources if default_sources else sources,
            key="source_filter"
        )
    except Exception as e:
        st.error(f"Erreur lors du chargement des sources: {str(e)}")
        return []

def date_range_selector(collection):
    """
    Sélecteur de plage de dates avec conversion automatique
    pour MongoDB et gestion des erreurs
    """
    try:
        # Récupération des dates min/max
        min_date = collection.find_one(sort=[("date", 1)])["date"]
        max_date = collection.find_one(sort=[("date", -1)])["date"]
        
        # Interface utilisateur
        selected = st.date_input(
            "Période d'analyse",
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date,
            key="date_range_selector"
        )
        
        # Conversion pour MongoDB
        if isinstance(selected, (list, tuple)) and len(selected) == 2:
            return [
                datetime.combine(selected[0], datetime.min.time()),
                datetime.combine(selected[1], datetime.max.time())
            ]
        return [min_date, max_date]
        
    except Exception as e:
        st.error(f"Erreur de sélection de date: {str(e)}")
        # Retourne une plage par défaut large
        return [datetime(2020, 1, 1), datetime.now()]