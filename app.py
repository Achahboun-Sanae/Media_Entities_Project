from io import BytesIO
import os
import streamlit as st
st.set_page_config(page_title="📊 Dashboard Entités Relationnelles", layout="wide")

import numpy as np
import plotly.express as px
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import altair as alt
from streamlit_option_menu import option_menu
from datetime import datetime
import community as community_louvain
import json
import sys
from pathlib import Path
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
from geopy.geocoders import Nominatim
import time
import tempfile
import plotly.graph_objects as go
from st_aggrid import  GridUpdateMode , AgGrid as ag_grid 
import seaborn as sns
from streamlit_folium import folium_static
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from folium.plugins import MarkerCluster, HeatMap

# Configuration du chemin
sys.path.append(str(Path(__file__).parent.parent))
from utils.supabase_config import get_supabase_manager

# ======== Initialisation Supabase ========
@st.cache_resource
def init_supabase():
    try:
        manager = get_supabase_manager()
        return manager
    except Exception as e:
        st.error(f"Erreur de connexion à Supabase: {str(e)}")
        st.stop()

manager = init_supabase()

# ======== Interface ========
# Appliquer le thème initial par défaut
if "theme_selector" not in st.session_state:
    st.session_state.theme_selector = "Clair"

def set_theme(theme):
    if theme == "Sombre":
        st.markdown("""
            <style>
            .stApp { 
                background-color: #0E1117;
                color: #FAFAFA;
            }
            .metric-card {
                background: rgba(255,255,255,0.1) !important;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            .stApp { 
                background-color: #FFFFFF;
                color: #000000;
            }
            </style>
        """, unsafe_allow_html=True)

# Appliquer le thème au chargement
set_theme(st.session_state.theme_selector)

with st.sidebar:
    theme = st.selectbox("🎨 Thème", ["Clair", "Sombre"], 
                         key="theme_selector")
    lang = st.selectbox("🌐 Langue", ["en", "fr", "ar"], 
                        format_func=lambda x: {"en": "Anglais", "fr": "Français", "ar": "Arabe"}[x])

# ======== Chargement des Données ========
@st.cache_data(ttl=3600)
def load_data(lang):
    try:
        table_name = f'relations_{lang}'
        relations = manager.get_table(table_name)
        
        if relations.empty:
            st.warning(f"Aucune donnée dans la table {table_name}")
            return None
            
        #st.success(f"✅ Données chargées : {len(relations)} relations")
        #st.write(f"🔹 Aperçu des données :")
        #st.dataframe(relations.head(3))

        # Vérification des colonnes requises
        required_columns = {
            'fr': ['nom_source', 'type_source', 'nom_cible', 'type_cible', 'relation'],
            'en': ['nom_source', 'type_source', 'nom_cible', 'type_cible', 'relation'],
            'ar': ['nom_source', 'type_source', 'nom_cible', 'type_cible', 'relation']
        }
        
        missing_cols = [col for col in required_columns[lang] if col not in relations.columns]
        if missing_cols:
            st.error(f"Colonnes manquantes dans {table_name}: {missing_cols}")
            return None

        # Normalisation des noms de colonnes spécifique au français
        if lang == 'fr':
            relations = relations.rename(columns={
                'type_source': 'type_entite_source',
                'type_cible': 'type_entite_cible'
            })

        # Traitement des entités avec vérification des colonnes
        source_cols = ['nom_source', 'type_source'] if 'type_source' in relations.columns else ['nom_source', 'type_entite_source']
        target_cols = ['nom_cible', 'type_cible'] if 'type_cible' in relations.columns else ['nom_cible', 'type_entite_cible']
        
        sources = relations[source_cols].rename(
            columns={source_cols[0]: 'Nom', source_cols[1]: 'Type'})
        targets = relations[target_cols].rename(
            columns={target_cols[0]: 'Nom', target_cols[1]: 'Type'})
        
        entities = pd.concat([sources, targets]).drop_duplicates()

        # Comptage des occurrences avec vérification
        if 'nom_source' in relations.columns and 'nom_cible' in relations.columns:
            source_counts = relations['nom_source'].value_counts()
            target_counts = relations['nom_cible'].value_counts()
            entities = entities.set_index('Nom')
            entities['Occurrences'] = source_counts.add(target_counts, fill_value=0)
            entities = entities.reset_index()
        else:
            st.warning("Impossible de calculer les occurrences - colonnes manquantes")
            entities['Occurrences'] = 0

        return {
            'entities': entities,
            'relations': list(zip(relations['nom_source'], 
                                relations['nom_cible'], 
                                relations['relation'])),
            'relations_full': relations
        }

    except Exception as e:
        st.error(f"Erreur critique ({lang}) : {str(e)}", icon="🚨")
        st.exception(e)
        return None

# Chargement des données
data = load_data(lang)


# ======== Traitement des Données ========
if data:
    # Extraction des données avec vérifications sécurisées
    entities_data = data.get('entities', pd.DataFrame())
    entity_relations = data.get('relations', [])
    relations_full = data.get('relations_full', pd.DataFrame())
    
    # Gestion robuste des dates
    if not relations_full.empty and 'date' in relations_full.columns:
        try:
            # Essai de conversion ISO8601 avec gestion des fractions de seconde
            relations_full['date'] = pd.to_datetime(
                relations_full['date'],
                format='ISO8601',
                errors='raise'
            )
        except ValueError as e:
            st.warning(f"Conversion des dates partiellement échouée : {str(e)}")
            try:
                # Fallback 1 : Essaye le format mixte
                relations_full['date'] = pd.to_datetime(
                    relations_full['date'],
                    format='mixed',
                    errors='coerce'
                )
            except Exception:
                # Fallback 2 : Conversion en string si tout échoue
                relations_full['date'] = relations_full['date'].astype(str)
                st.error("Certaines dates n'ont pu être converties et ont été conservées en texte")
            
            # Affiche les lignes problématiques pour débogage
            if relations_full['date'].isna().any():
                problematic_dates = relations_full[relations_full['date'].isna()]
                st.write("Lignes avec dates non converties :", problematic_dates.head())
else:
    # Valeurs par défaut si data est None ou vide
    entities_data = pd.DataFrame()
    entity_relations = []
    relations_full = pd.DataFrame()

# ======== Navigation ========
st.title("Dashboard Entités Relationnelles")

# Ajoute un petit espace entre le titre et le menu
st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)

# Barre de navigation avec styles ajustés
page = option_menu(
    menu_title=None,
    options=["Tableau de bord", "Entités", "Graphe", "Statistiques", "Articles", "Carte", "Export"],
    icons=["bar-chart", "search", "diagram-3", "graph-up", "newspaper", "map", "download"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0!important",
            "margin": "0!important",
            "background-color": "#f8f9fa",
        },
        "nav-link": {
            "font-size": "13px",
            "margin": "0px",
            "--hover-color": "#eee",
            "padding": "8px 12px",
        },
        "nav-link-selected": {
            "background-color": "#ff6600",
            "font-weight": "normal",
        },
    }
)  

# ======== Pages ========
if page == "Tableau de bord":
    # Style CSS personnalisé avec support complet des thèmes
    st.markdown("""
    <style>
        :root {
            --card-bg-light: #ffffff;
            --card-border-light: #e0e0e0;
            --card-text-light: #2c3e50;
            --card-icon-light: #3498db;
            --divider-light: #eeeeee;
            
            --card-bg-dark: #1e2229;
            --card-border-dark: #2d3746;
            --card-text-dark: #f0f2f6;
            --card-icon-dark: #25d0ab;
            --divider-dark: #2d3746;
        }
        
        .metric-card {
            border-radius: 10px;
            padding: 20px;
            background-color: var(--card-bg);
            border-left: 4px solid var(--card-icon);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            border: 1px solid var(--card-border);
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
        }
        
        .metric-title {
            font-size: 14px;
            color: var(--card-text);
            opacity: 0.8;
            font-weight: 500;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 28px;
            font-weight: 700;
            color: var(--card-text);
            line-height: 1.2;
        }
        
        .metric-icon {
            font-size: 24px;
            margin-bottom: 10px;
            color: var(--card-icon);
        }
        
        .divider {
            margin: 25px 0 !important;
            border-color: var(--divider) !important;
            opacity: 0.5;
        }
        
        /* Light theme */
        [data-theme="light"] {
            --card-bg: var(--card-bg-light);
            --card-border: var(--card-border-light);
            --card-text: var(--card-text-light);
            --card-icon: var(--card-icon-light);
            --divider: var(--divider-light);
        }
        
        /* Dark theme */
        [data-theme="dark"] {
            --card-bg: var(--card-bg-dark);
            --card-border: var(--card-border-dark);
            --card-text: var(--card-text-dark);
            --card-icon: var(--card-icon-dark);
            --divider: var(--divider-dark);
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("Tableau de bord général")

    st.markdown("### 📈 Statistiques globales")
    cols = st.columns(4)
    
    
    # Calcul du nombre d'articles uniques (en supposant que 'article_id' existe)
    if not relations_full.empty and 'article_id' in relations_full.columns:
        nb_articles = relations_full['article_id'].nunique()
    else:
        nb_articles = relations_full['url'].nunique() if 'url' in relations_full.columns else 0

    # Icônes et couleurs unifiées avec le nombre d'articles
    metrics = [
        {"icon": "🔎", "title": "Entités uniques", "value": len(entities_data), "color": "#4285F4"},
        {"icon": "⛓️", "title": "Relations", "value": len(entity_relations), "color": "#34A853"}, 
        {"icon": "📄", "title": "Articles analysés", "value": nb_articles, "color": "#EA4335"},
        {"icon": "🏷️", "title": "Types d'entités", "value": entities_data['Type'].nunique(), "color": "#FBBC05"}
    ]
    
    for i, col in enumerate(cols):
        with col:
            metric = metrics[i]
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">{metric['icon']}</div>
                <div class="metric-title">{metric['title']}</div>
                <div class="metric-value">{metric['value']:,}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Détection du thème
    theme = "dark" if st._config.get_option("theme.base") == "dark" else "light"
    
    # Configuration des couleurs en fonction du thème
    if theme == "dark":
        plotly_template = "plotly_dark"
        altair_theme = "dark"
        mapbox_style = "carto-darkmatter"
        color_sequence = px.colors.qualitative.Dark24
        heatmap_scheme = "greys"
    else:
        plotly_template = "plotly_white"
        altair_theme = "default"
        mapbox_style = "carto-positron"
        color_sequence = px.colors.qualitative.Pastel
        heatmap_scheme = "tealblues"

    # ======== Intégration du code #1 ========
    # 1. Filtres globaux (à placer avant les visualisations)
    with st.expander("🔎 Filtres globaux", expanded=True):
        cols = st.columns(3)
        with cols[0]:
            date_range = st.date_input(
                "Période",
                value=[relations_full['date'].min(), relations_full['date'].max()],
                min_value=relations_full['date'].min(),
                max_value=relations_full['date'].max()
            )
        with cols[1]:
            selected_sources = st.multiselect(
                "Sources médias",
                options=sorted(relations_full['source'].unique()),
                default=relations_full['source'].unique()[:3],
                key='global_source_filter'
            )
        with cols[2]:
            selected_types = st.multiselect(
                "Types d'entités",
                options=sorted(entities_data['Type'].unique()),
                default=entities_data['Type'].unique()
            )

    # Appliquer les filtres globaux
    filtered_relations = relations_full[
        (relations_full['date'].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))) &
        (relations_full['source'].isin(selected_sources))
    ]

    filtered_entities = entities_data[entities_data['Type'].isin(selected_types)]
    filtered_entity_relations = [
        (s, t, r) for s, t, r in entity_relations 
        if s in filtered_entities['Nom'].values and t in filtered_entities['Nom'].values
    ]

    # 1. Évolution temporelle (avec données filtrées)
    st.subheader("📅 Activité temporelle")

    with st.expander("🔎 Options d'affichage", expanded=False):
        aggregation = st.selectbox(
            "Granularité",
            options=['Journalière', 'Hebdomadaire', 'Mensuelle'],
            index=2,
            key='time_agg'
        )
        freq = {'Journalière': 'D', 'Hebdomadaire': 'W', 'Mensuelle': 'ME'}[aggregation]

    if not filtered_relations.empty:
        timeline_agg = filtered_relations.groupby([pd.Grouper(key='date', freq=freq), 'source']).size().reset_index(name='count')

        fig = px.area(
            timeline_agg,
            x='date',
            y='count',
            color='source',
            title=f"Volume de relations par source ({aggregation.lower()})",
            template=plotly_template,
            color_discrete_sequence=color_sequence,
            labels={'count': 'Nombre de relations', 'date': 'Date'}
        )
        fig.update_layout(
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend_title_text='Source média'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Aucune donnée disponible pour les filtres sélectionnés.")

    # 2. Matrice des relations (avec données filtrées)
    if filtered_entity_relations and not filtered_entities.empty:
        st.subheader("🧩 Matrice de cooccurrence")
        
        relations_df = pd.DataFrame(filtered_entity_relations, columns=["Source", "Target", "Type"])
        matrix_data = relations_df.groupby(['Source', 'Target']).size().reset_index(name='count')
        
        threshold = st.slider(
            "Seuil minimal de cooccurrences", 
            min_value=1, 
            max_value=matrix_data['count'].max() if not matrix_data.empty else 1, 
            value=2,
            help="Filtrer pour ne montrer que les relations fréquentes",
            key='matrix_threshold'
        )
        
        matrix_data = matrix_data[matrix_data['count'] >= threshold]
        
        if not matrix_data.empty:
            scatter = alt.Chart(matrix_data).mark_circle(size=60).encode(
                x=alt.X('Source:N', title="Entité source", sort='-y'),
                y=alt.Y('Target:N', title="Entité cible"),
                size=alt.Size('count:Q', title="Poids de la relation"),
                color=alt.Color('count:Q', title="Nombre de cooccurrences", scale=alt.Scale(scheme="tealblues")),
                tooltip=['Source', 'Target', 'count']
            ).properties(
                width=800,
                height=600
            ).interactive()

            st.altair_chart(scatter, use_container_width=True)
        else:
            st.info("Aucune relation ne correspond au seuil sélectionné.")     

    # 3. Types de relation (avec données filtrées)
    if filtered_entity_relations:
        st.subheader("🔗 Types de relations")
            
        relation_types = [rel[2] for rel in filtered_entity_relations]
        freq_df = pd.DataFrame(Counter(relation_types).items(), columns=['Relation', 'Fréquence'])
        freq_df = freq_df.sort_values(by='Fréquence', ascending=False).head(20)
            
        fig = px.bar(
            freq_df,
            x='Fréquence',
            y='Relation',
            orientation='h',
            title="Top 20 des types de relations",
            template=plotly_template,
            color='Fréquence',
            color_continuous_scale='teal',
            labels={'Fréquence': 'Nombre d\'occurrences'}
        )
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)

    # 4. Répartition des types d'entités (avec données filtrées)
    if not filtered_entities.empty:
        st.subheader("📦 Types d'entités")
            
        entity_counts = filtered_entities['Type'].value_counts().reset_index()
        entity_counts.columns = ['Type', 'Nombre']
            
        fig = px.pie(
            entity_counts,
            names='Type',
            values='Nombre',
            title="Distribution des types d'entités",
            template=plotly_template,
            color_discrete_sequence=color_sequence,
            hole=0.3
        )
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate="<b>%{label}</b><br>%{value} entités (%{percent})",
            marker_line_color='rgba(0,0,0,0.2)' if theme == "light" else 'rgba(255,255,255,0.1)',
            marker_line_width=0.5
        )
        fig.update_layout(
            uniformtext_minsize=12,
            uniformtext_mode='hide',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    
    # ======== Fin de l'intégration du code #1 ========

elif page == "Entités":
    st.title("🔍 Exploration des Entités")

    if entities_data.empty:
        st.warning("Aucune entité n'a été trouvée dans les données.")
    else:
        # --- Filtres Avancés ---
        with st.expander("🔎 Filtres avancés", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                entity_types = ["Tous"] + sorted(entities_data['Type'].unique())
                selected_type = st.selectbox("Type d'entité", entity_types)
            with col2:
                search_term = st.text_input("Recherche par nom")
            with col3:
                min_occurrences = st.slider(
                    "Occurrences min",
                    min_value=0,
                    max_value=int(entities_data['Occurrences'].max()),
                    value=0
                )

        # --- Application des filtres ---
        filtered = entities_data.copy()
        if selected_type != "Tous":
            filtered = filtered[filtered['Type'] == selected_type]
        if search_term:
            filtered = filtered[filtered['Nom'].str.contains(search_term, case=False, na=False)]
        filtered = filtered[filtered['Occurrences'] >= min_occurrences]

        st.subheader(f"📋 Entités filtrées ({len(filtered)} résultats)")

        # --- Options de tri et pagination ---
        sort_option = st.selectbox("Trier par", ["Occurrences (décroissant)", "Nom (A-Z)"])
        if sort_option == "Occurrences (décroissant)":
            filtered = filtered.sort_values("Occurrences", ascending=False)
        else:
            filtered = filtered.sort_values("Nom", ascending=True)

        page_size = st.slider("Entités par page", 10, 100, 25)
        max_page = max(1, (len(filtered) - 1) // page_size + 1)
        page_number = st.number_input("Page", min_value=1, max_value=max_page, value=1)

        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size

        st.dataframe(
            filtered.iloc[start_idx:end_idx],
            use_container_width=True,
            height=min(600, page_size * 25)
        )

        # --- Graphique de répartition des types ---
        if not filtered.empty:
            st.subheader("📊 Répartition des types d'entités")

            # Correction ici
            type_counts = filtered['Type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Occurrences']  # renommage explicite

            fig = px.bar(
                type_counts,
                x='Type',
                y='Occurrences',
                title="Répartition des types d'entités",
                labels={'Type': 'Type', 'Occurrences': 'Occurrences'},
                color='Type'
            )
            st.plotly_chart(fig, use_container_width=True)


        # --- Analyse d'une entité spécifique ---
        st.divider()
        st.subheader("🔬 Analyse d'une entité spécifique")

        selected_entity = st.selectbox(
            "Sélectionner une entité", filtered['Nom'].unique(), index=None
        )

        if selected_entity:
            st.markdown(f"### 🧩 Analyse de : `{selected_entity}`")
            source_relations = relations_full[relations_full['nom_source'] == selected_entity]
            target_relations = relations_full[relations_full['nom_cible'] == selected_entity]

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Relations sortantes", len(source_relations))
            with col2:
                st.metric("Relations entrantes", len(target_relations))

            if not source_relations.empty or not target_relations.empty:
                tab1, tab2 = st.tabs(["📤 Sortantes", "📥 Entrantes"])

                with tab1:
                    if not source_relations.empty:
                        st.dataframe(source_relations, use_container_width=True)
                        rel_counts = source_relations['relation'].value_counts()
                        fig = px.pie(rel_counts, values=rel_counts.values, names=rel_counts.index,
                                     title="Types de relations sortantes")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Aucune relation sortante trouvée.")

                with tab2:
                    if not target_relations.empty:
                        st.dataframe(target_relations, use_container_width=True)
                        rel_counts = target_relations['relation'].value_counts()
                        fig = px.pie(rel_counts, values=rel_counts.values, names=rel_counts.index,
                                     title="Types de relations entrantes")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Aucune relation entrante trouvée.")

# ======== Nouvelle section pour les articles ========
elif page == "Articles":
    st.title("📰 Analyse des Articles Sources")
    
    if not relations_full.empty and 'source' in relations_full.columns:
        import warnings
        warnings.filterwarnings('ignore', message='.*pyplot.*')
        
        # ========== 1. STATISTIQUES GLOBALES ==========
        st.header("📊 Statistiques globales des sources")
        with st.spinner('Calcul des statistiques...'):
            if 'article_id' in relations_full.columns:
                article_stats = relations_full.groupby('source')['article_id'].nunique().reset_index()
                article_stats.columns = ['Source', "Nombre d'articles"]
            else:
                article_stats = relations_full['source'].value_counts().reset_index()
                article_stats.columns = ['Source', "Nombre d'articles"]
            
            source_stats = relations_full['source'].value_counts().reset_index()
            source_stats.columns = ['Source', 'Nombre de relations']
            
            stats_df = pd.merge(article_stats, source_stats, on='Source')
            stats_df['Relations/article'] = stats_df['Nombre de relations'] / stats_df["Nombre d'articles"]
            stats_df = stats_df.sort_values("Nombre d'articles", ascending=False).dropna()

        # Calcul dynamique de la hauteur en fonction du nombre de lignes
        num_rows = len(stats_df)
        row_height = 35  # Hauteur par ligne en pixels
        header_height = 70  # Hauteur de l'en-tête
        min_height = 200  # Hauteur minimale
        table_height = min(max(num_rows * row_height + header_height, min_height), 600)  # Limité à 600px max

        st.dataframe(
            stats_df,
            column_config={
                "Source": st.column_config.TextColumn("Source médiatique"),
                "Nombre d'articles": st.column_config.NumberColumn("Articles"),
                "Nombre de relations": st.column_config.NumberColumn("Relations"),
                "Relations/article": st.column_config.NumberColumn(
                    "Relations/article",
                    format="%.1f",
                    help="Ratio moyen de relations par article"
                )
            },
            height=table_height,  # Hauteur dynamique
            use_container_width=True
        )
        st.download_button("📥 Télécharger les données", stats_df.to_csv(index=False), "statistiques_sources.csv")

        # ========== 2. ANALYSE DÉTAILLÉE PAR SOURCE ==========
        st.header("🔍 Analyse détaillée d'une source")
        selected_source = st.selectbox("Sélectionnez une source", options=stats_df['Source'].unique())

        source_data = relations_full[relations_full['source'] == selected_source].copy()

        if not source_data.empty:
            # Chronologie des publications
            if 'date' in source_data.columns:
                st.subheader("📅 Chronologie des publications")   
                source_data['date'] = pd.to_datetime(source_data['date'])
                timeline = source_data.set_index('date').resample('ME').size()
                fig = px.area(
                    timeline.reset_index(),
                    x='date', y=0,
                    title=f"Publications mensuelles – {selected_source}",
                    labels={'0': "Nombre d'articles"}
                )
                st.plotly_chart(fig, use_container_width=True)

            # Entités mentionnées
            st.subheader("🏷 Entités les plus citées")
            sources = source_data['nom_source'].value_counts().fillna(0)
            targets = source_data['nom_cible'].value_counts().fillna(0)
            top_entities = (sources + targets).sort_values(ascending=False).head(20)

            entities_df = top_entities.reset_index()
            entities_df.columns = ['Entité', 'Nombre']

            fig = px.treemap(
                entities_df,
                path=['Entité'], values='Nombre',
                title=f"Entités les plus citées dans {selected_source}",
                color='Nombre', color_continuous_scale='Blues'
            )
            fig.update_traces(
                textinfo="label+value+percent parent",
                hovertemplate="<b>%{label}</b><br>Mentions: %{value}<br>Part: %{percentParent:.1%}"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Types de relations
            st.subheader("🔗 Répartition des types de relations")
            rel_counts = source_data['relation'].value_counts()

            fig = px.pie(
                rel_counts,
                names=rel_counts.index,
                values=rel_counts.values,
                title="Types de relations dans les articles"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Détails des articles
            st.subheader("📝 Détails des articles")
            if 'article_id' in source_data.columns:
                articles_to_show = source_data.drop_duplicates('article_id').dropna()
            else:
                articles_to_show = source_data.dropna()

            # Hauteur dynamique pour le tableau des articles
            article_rows = len(articles_to_show)
            article_table_height = min(max(article_rows * row_height + header_height, min_height), 600)

            st.dataframe(
                articles_to_show,
                column_config={
                    "date": "Date",
                    "title": "Titre",
                    "url": st.column_config.LinkColumn("URL")
                },
                height=article_table_height,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("Aucune donnée disponible pour cette source sélectionnée.")
    else:
        st.warning("Aucune donnée sur les sources n'est disponible.")

elif page == "Graphe":
    st.title("🌍 Réseau Relationnel Intelligent")
    
    if not entities_data.empty and entity_relations:
        # ========== CONFIGURATION ==========
        # Couleurs pour les types d'entités
        NODE_COLORS = {
            'PER': '#FF6B6B', 'LOC': '#4ECDC4', 
            'ORG': '#45B7D1', 'EVENT': '#A593E0',
            'MISC': '#FFA5A5'
        }

        EDGE_COLORS = {
            'relation': '#9BE3DE',
            'partnership': '#81BECE',
            'membership': '#FFAA85'
        }

        # ========== SIDEBAR ==========
        with st.sidebar:
            st.header("⚙️ Paramètres Avancés")
            
            # Filtres intelligents
            selected_types = st.multiselect(
                "Types d'entités",
                options=sorted(entities_data['Type'].unique()),
                default=list(entities_data['Type'].unique())
            )
            
            # Sélection des entités avec recherche
            entity_options = entities_data[
                (entities_data['Type'].isin(selected_types))
            ]['Nom'].unique()
            
            selected_entities = st.multiselect(
                "Entités clés",
                options=sorted(entity_options),
                default=entity_options[:10] if len(entity_options) > 10 else entity_options,
                placeholder="Sélectionnez des entités..."
            )
            
            # Options avancées
            with st.expander("🎨 Options de style"):
                dark_mode = st.checkbox("Mode sombre", value=st.session_state.theme_selector == "Sombre")
                show_labels = st.checkbox("Afficher les étiquettes", True)
                node_size = st.slider("Taille des nœuds", 5, 50, 15)
                edge_width = st.slider("Épaisseur des liens", 0.1, 5.0, 1.0)
                font_size = st.slider("Taille du texte", 10, 30, 14)
                
            with st.expander("⚙️ Configuration avancée"):
                physics = st.checkbox("Physique dynamique", True)
                community_detection = st.checkbox("Détection de communautés", True)
                layout_choice = st.selectbox("Disposition", [
                    "Force Atlas", 
                    "Hiérarchique", 
                    "Circulaire"
                ])
                physics_algo = st.selectbox("Algorithme", [
                    "forceAtlas2Based", 
                    "barnesHut", 
                    "repulsion"
                ])

        if not selected_entities:
            st.warning("Veuillez sélectionner au moins une entité")
            st.stop()

        # ========== CONSTRUCTION DU GRAPHE ==========
        G = nx.Graph()
        
        # Préparation des nœuds
        node_data = entities_data[
            (entities_data['Nom'].isin(selected_entities)) &
            (entities_data['Type'].isin(selected_types))
        ].drop_duplicates('Nom').set_index('Nom')
        
        # Ajout des nœuds avec style adaptatif
        for entity in node_data.index:
            entity_type = node_data.at[entity, 'Type']
            occurrences = int(node_data.at[entity, 'Occurrences'])
            
            G.add_node(
                entity,
                label=entity if show_labels else "",
                title=f"{entity} ({entity_type}) - {occurrences} connexions",
                group=entity_type,
                size=node_size + occurrences**0.5,
                color=NODE_COLORS.get(entity_type, '#999999'),
                shape='dot',
                borderWidth=2,
                font={
                    'size': font_size,
                    'face': 'Arial',
                    'color': 'white' if dark_mode else '#2d3746'
                }
            )
        
        # Ajout des relations avec comptage
        relation_counts = Counter()
        for source, target, rel_type in entity_relations:
            if source in G.nodes and target in G.nodes:
                relation_counts[(source, target, rel_type)] += 1
                
        for (source, target, rel_type), count in relation_counts.items():
            G.add_edge(
                source, target,
                title=f"{rel_type}\n────────────\nConnections: {count}",
                label=rel_type if show_labels else "",
                width=edge_width * min(3, count**0.5),
                color=EDGE_COLORS.get(rel_type.split('_')[0], '#cccccc'),
                smooth={'type': 'continuous'},
                font={
                    'size': font_size - 2,
                    'face': 'Arial',
                    'align': 'middle'
                }
            )

        # Détection de communautés
        if community_detection and len(G.nodes) > 0:
            partition = community_louvain.best_partition(G)
            nx.set_node_attributes(G, partition, 'group')

        # ========== VISUALISATION ==========
        # Configuration du réseau
        net = Network(
            height="800px",
            width="100%",
            bgcolor="#1a1a1a" if dark_mode else "#ffffff",
            font_color="white" if dark_mode else "#333333",
            select_menu=True,
            filter_menu=True,
            cdn_resources='remote',
            notebook=False
        )
        
        net.from_nx(G)
        
        # Options dynamiques
        options = {
            "nodes": {
                "scaling": {
                    "min": 10,
                    "max": 50
                },
                "font": {
                    "size": font_size,
                    "face": "Arial",
                    "strokeWidth": 2,
                    "strokeColor": "#000000" if dark_mode else "#ffffff"
                }
            },
            "edges": {
                "smooth": {
                    "type": "continuous",
                    "roundness": 0.2
                },
                "selectionWidth": 2
            },
            "physics": {
                "enabled": physics,
                "solver": physics_algo,
                "stabilization": {
                    "iterations": 100
                }
            },
            "interaction": {
                "hover": True,
                "tooltipDelay": 200,
                "hideEdgesOnDrag": True,
                "multiselect": True,
                "navigationButtons": True,
                "keyboard": True
            }
        }
        
        if layout_choice == "Hiérarchique":
            options["layout"] = {
                "hierarchical": {
                    "enabled": True,
                    "direction": "UD",
                    "sortMethod": "hubsize"
                }
            }
        
        net.set_options(json.dumps(options))
        
        # Génération et affichage du graphe
        try:
            html = net.generate_html()
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", encoding="utf-8", delete=False) as f:
                f.write(html)
                temp_path = f.name
            
            with open(temp_path, "r", encoding="utf-8") as f:
                components.html(f.read(), height=850, scrolling=True)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        # ========== ANALYSE AVANCÉE ==========
        st.divider()
        st.header("📊 Analyse du Réseau")
        
        # Métriques clés
        col1, col2, col3 = st.columns(3)
        degrees = dict(G.degree())
        col1.metric("Nœuds", len(G.nodes))
        col2.metric("Arêtes", len(G.edges))
        col3.metric("Densité", f"{nx.density(G):.3f}")
        
        # Visualisations complémentaires
        tab1, tab2 = st.tabs(["🔗 Distribution des connexions", "📌 Top relations"])
        
        with tab1:
            fig = px.histogram(
                x=list(degrees.values()),
                nbins=20,
                title="Nombre de connexions par entité",
                labels={'x': 'Connexions', 'y': 'Nombre d\'entités'},
                color_discrete_sequence=['#4ECDC4'] if dark_mode else ['#45B7D1']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            top_relations = pd.Series([rel[2] for rel in entity_relations]).value_counts().head(10)
            fig = px.bar(
                top_relations,
                orientation='h',
                title="Top 10 des relations",
                labels={'value': 'Occurrences', 'index': 'Type de relation'},
                color_discrete_sequence=['#FF6B6B'] if dark_mode else ['#A593E0']
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Aucune donnée disponible pour générer le graphe")
        st.image("https://via.placeholder.com/800x400?text=No+Data+Available", use_column_width=True)

elif page == "Statistiques":
    st.title("📈 Tableau de bord analytique")
    
    if not entities_data.empty or entity_relations:
        # Configuration des onglets avec icônes modernes
        tab1, tab2 = st.tabs(["🔠 Entités", "🔄 Relations"])

        # ================================
        # TAB 1 — ENTITÉS (Optimisé)
        # ================================
        with tab1:
            st.subheader("Analyse des entités", divider="rainbow")
            
            if not entities_data.empty:
                # Filtres en colonne pour meilleure organisation
                with st.expander("🔧 Filtres avancés", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        entity_types = entities_data['Type'].unique().tolist()
                        selected_types = st.multiselect(
                            "Types d'entités à inclure :",
                            options=entity_types,
                            default=entity_types,
                            help="Sélectionnez un ou plusieurs types d'entités à analyser"
                        )
                    
                    with col2:
                        min_occurrences = st.slider(
                            "Seuil minimum d'occurrences :",
                            min_value=1,
                            max_value=int(entities_data['Occurrences'].max()),
                            value=1,
                            help="Filtrer les entités avec au moins ce nombre d'occurrences"
                        )

                # Appliquer les filtres
                filtered_entities = entities_data[
                    (entities_data['Type'].isin(selected_types)) & 
                    (entities_data['Occurrences'] >= min_occurrences)
                ].copy()

                # Visualisations en grille responsive
                st.markdown("### 📊 Distribution des entités")
                
                col1, col2 = st.columns([3, 2])
                with col1:
                    # Top entités avec barres horizontales
                    top_n = st.slider("Nombre d'entités à afficher :", 5, 30, 15)
                    top_entities = filtered_entities.nlargest(top_n, 'Occurrences')
                    
                    fig = px.bar(
                        top_entities, 
                        x='Occurrences', 
                        y='Nom', 
                        color='Type',
                        orientation='h',
                        title=f"Top {top_n} des entités",
                        template='plotly_white'
                    )
                    fig.update_layout(
                        height=500,
                        yaxis={'categoryorder': 'total ascending'},
                        hovermode='y unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    # Camembert des types avec légende interactive
                    type_counts = filtered_entities['Type'].value_counts().reset_index()
                    fig = px.pie(
                        type_counts, 
                        names='Type', 
                        values='count',
                        hole=0.35,
                        title="Répartition par type"
                    )
                    fig.update_traces(
                        textposition='inside',
                        textinfo='percent+label',
                        hovertemplate="<b>%{label}</b><br>%{value} entités (%{percent})"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Histogramme avec options interactives
                st.markdown("### 📈 Distribution des fréquences")
                with st.expander("Options d'affichage"):
                    show_log = st.toggle("Échelle logarithmique", False)
                    bin_size = st.slider("Taille des intervalles :", 1, 20, 5)

                fig = px.histogram(
                    filtered_entities,
                    x='Occurrences',
                    nbins=bin_size,
                    log_y=show_log,
                    color='Type',
                    marginal='box',
                    title="Histogramme des occurrences"
                )
                st.plotly_chart(fig, use_container_width=True)

        # ================================
        # TAB 2 — RELATIONS (Optimisé)
        # ================================
        with tab2:
            st.subheader("Analyse des relations", divider="rainbow")
            
            if entity_relations:
                relations_df = pd.DataFrame(entity_relations, columns=["Source", "Target", "Type"])
                
                # Section de filtrage
                with st.expander("🔎 Options d'analyse", expanded=True):
                    relation_types = sorted(relations_df['Type'].unique())
                    selected_rel_types = st.multiselect(
                        "Types de relations à inclure :",
                        options=relation_types,
                        default=relation_types[:3] if len(relation_types) > 3 else relation_types
                    )
                    filtered_relations = relations_df[relations_df['Type'].isin(selected_rel_types)]

                # Visualisations en grille
                col1, col2 = st.columns(2)
                
                with col1:
                    # Graphique des relations les plus fréquentes
                    rel_counts = filtered_relations['Type'].value_counts().reset_index()
                    fig = px.bar(
                        rel_counts,
                        x='count',
                        y='Type',
                        orientation='h',
                        title="Relations les plus fréquentes",
                        color='count',
                        color_continuous_scale='deep'
                    )
                    fig.update_layout(
                        yaxis={'categoryorder': 'total ascending'},
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    # Sunburst des relations par type d'entité
                    try:
                        rel_with_types = filtered_relations.merge(
                            entities_data[['Nom', 'Type']].rename(columns={'Nom': 'Source', 'Type': 'SourceType'}),
                            on='Source', how='left'
                        ).merge(
                            entities_data[['Nom', 'Type']].rename(columns={'Nom': 'Target', 'Type': 'TargetType'}),
                            on='Target', how='left'
                        )
                        type_pairs = rel_with_types.groupby(['SourceType', 'TargetType']).size().reset_index(name='count')
                        
                        fig = px.sunburst(
                            type_pairs,
                            path=['SourceType', 'TargetType'],
                            values='count',
                            title="Relations par types d'entités",
                            color='count',
                            color_continuous_scale='blues'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning("Données insuffisantes pour cette visualisation")

                # Analyse temporelle si disponible
                if not relations_full.empty and 'date' in relations_full.columns:
                    st.markdown("### ⏳ Analyse temporelle")
                    
                    try:
                        rel_temp = relations_full.copy()
                        rel_temp['date'] = pd.to_datetime(rel_temp['date'])
                        rel_temp['période'] = rel_temp['date'].dt.to_period('M').astype(str)
                        
                        # Sélection dynamique des relations à afficher
                        rel_to_show = st.multiselect(
                            "Relations à visualiser :",
                            options=sorted(rel_temp['relation'].unique()),
                            default=sorted(rel_temp['relation'].unique())[:3]
                        )
                        
                        if rel_to_show:
                            monthly_data = rel_temp[rel_temp['relation'].isin(rel_to_show)]
                            monthly_data = monthly_data.groupby(['période', 'relation']).size().reset_index(name='volume')
                            
                            fig = px.area(
                                monthly_data,
                                x='période',
                                y='volume',
                                color='relation',
                                title="Évolution mensuelle des relations",
                                line_shape='spline'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erreur dans l'analyse temporelle : {str(e)}")

    else:
        # Message d'erreur plus engageant
        st.error("🔍 Aucune donnée disponible pour l'analyse")
        st.markdown("""
        <div style="background:#f0f2f6;padding:20px;border-radius:10px">
            <h4 style="color:#2c3e50">Conseils :</h4>
            <ul>
                <li>Vérifiez que des documents ont été chargés</li>
                <li>Assurez-vous que l'extraction d'entités a été exécutée</li>
                <li>Essayez d'ajuster les paramètres de traitement</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

elif page == "Carte":
    st.title("🗺️ Visualisation cartographique des entités")
    
    if not entities_data.empty and 'Nom' in entities_data.columns:
        # Configuration CSS pour une carte plus large
        st.markdown("""
        <style>
            .map-container {
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                overflow: hidden;
                margin-bottom: 20px;
                width: 100%;
            }
            .stProgress > div > div > div > div {
                background-color: #4CAF50;
            }
            /* Élargissement de la carte */
            .folium-map {
                width: 100% !important;
                height: 600px !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # Initialisation du cache
        if 'location_cache' not in st.session_state:
            st.session_state.location_cache = {
                "Paris": (48.8566, 2.3522),
                "New York": (40.7128, -74.0060),
                "Londres": (51.5074, -0.1278),
                "Berlin": (52.5200, 13.4050),
                "Tokyo": (35.6762, 139.6503)
            }

        # Configuration de la carte
        with st.expander("⚙️ Paramètres cartographiques", expanded=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                map_type = st.selectbox("Type de carte", 
                                      ["OpenStreetMap", "Stamen Terrain", "CartoDB positron"],
                                      index=2)
                zoom = st.slider("Niveau de zoom", 1, 15, 5)
            with col2:
                cluster = st.checkbox("Regrouper les marqueurs", True)
                heatmap = st.checkbox("Afficher heatmap", False)

        # Filtrage des entités géographiques
        @st.cache_data
        def filter_geo_entities(data):
            geo_types = ['ville', 'city', 'pays', 'country', 'lieu', 'location', 'loc', 'place', 'region']
            return data[data['Type'].str.lower().isin(geo_types)].copy()

        geo_entities = filter_geo_entities(entities_data)

        if geo_entities.empty:
            st.warning("Aucune entité géographique trouvée dans les données.")
            st.stop()

        # Géocodage avec barre de progression
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        valid_entities = []
        missing_entities = []
        
        geolocator = Nominatim(user_agent="geo_dashboard", timeout=5)
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=0.5, max_retries=2)

        for i, row in geo_entities.iterrows():
            clean_name = str(row['Nom']).strip().split('(')[0].split('-')[0].strip()
            
            if clean_name in st.session_state.location_cache:
                coord = st.session_state.location_cache[clean_name]
            else:
                try:
                    location = geocode(clean_name, exactly_one=True, language='fr')
                    coord = (location.latitude, location.longitude) if location else None
                    if coord:
                        st.session_state.location_cache[clean_name] = coord
                except:
                    coord = None
            
            if coord:
                valid_entities.append({
                    'name': clean_name,
                    'type': row['Type'],
                    'count': row.get('Occurrences', 1),
                    'lat': coord[0],
                    'lon': coord[1]
                })
            else:
                missing_entities.append(clean_name)
            
            progress = (i + 1) / len(geo_entities)
            progress_bar.progress(min(progress, 1.0))
            status_text.text(f"Traitement {i+1}/{len(geo_entities)} - Trouvées: {len(valid_entities)}")

        progress_bar.empty()
        status_text.empty()

        if not valid_entities:
            st.error("Aucune localisation n'a pu être déterminée")
            st.stop()

        # Création de la carte élargie
        m = folium.Map(
            location=[valid_entities[0]['lat'], valid_entities[0]['lon']],
            zoom_start=zoom,
            tiles=map_type,
            control_scale=True,
            prefer_canvas=True
        )

        # Cluster de marqueurs
        if cluster and len(valid_entities) > 10:
            marker_cluster = MarkerCluster().add_to(m)

        # Ajout des marqueurs
        for loc in valid_entities:
            popup = f"<b>{loc['name']}</b><br>Type: {loc['type']}<br>Mentions: {loc['count']}"
            icon_color = 'red' if loc['count'] > 10 else 'blue' if loc['count'] > 5 else 'green'
            
            marker = folium.Marker(
                [loc['lat'], loc['lon']],
                popup=popup,
                icon=folium.Icon(color=icon_color, icon='info-sign')
            )
            
            if cluster and len(valid_entities) > 10:
                marker.add_to(marker_cluster)
            else:
                marker.add_to(m)

        # Heatmap
        if heatmap:
            heat_data = [[loc['lat'], loc['lon'], loc['count']] for loc in valid_entities]
            HeatMap(heat_data, radius=15).add_to(m)

        # Contrôles
        folium.plugins.Fullscreen(position="topright").add_to(m)

        # Affichage de la carte élargie
        with st.container():
            st.markdown("<div class='map-container'>", unsafe_allow_html=True)
            folium_static(m, width=1200, height=600)  # Carte plus large
            st.markdown("</div>", unsafe_allow_html=True)

        # Section statistiques améliorée
        st.subheader("📊 Statistiques de géolocalisation")
        
        # Calcul des indicateurs
        success_rate = len(valid_entities) / len(geo_entities) * 100
        avg_mentions = sum(loc['count'] for loc in valid_entities) / len(valid_entities) if valid_entities else 0
        top_entity = max(valid_entities, key=lambda x: x['count']) if valid_entities else None
        
        # Affichage en colonnes
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Entités analysées", len(geo_entities))
        col2.metric("Localisations trouvées", len(valid_entities), f"{success_rate:.1f}%")
        col3.metric("Mentions moyennes", f"{avg_mentions:.1f}")
        
        if top_entity:
            col4.metric("Entité la plus mentionnée", 
                       f"{top_entity['name']}",
                       f"{top_entity['count']} mentions")

        # Graphique supplémentaire
        st.markdown("### 📈 Répartition par type d'entité")
        type_counts = pd.DataFrame(valid_entities)['type'].value_counts()
        fig = px.pie(type_counts, 
                    names=type_counts.index, 
                    values=type_counts.values,
                    hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

        # Export des données
        with st.expander("💾 Exporter les données", expanded=False):
            if valid_entities:
                df = pd.DataFrame(valid_entities)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Télécharger les localisations (CSV)",
                    data=csv,
                    file_name="localisations_trouvees.csv",
                    mime="text/csv"
                )
    else:
        st.warning("Aucune donnée géographique disponible")

elif page == "Export":
    st.title("📤 Export des données")
    
    # Export des entités
    if not entities_data.empty:
        st.subheader("Export des entités")
        
        csv = entities_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Télécharger en CSV",
            data=csv,
            file_name="entites.csv",
            mime="text/csv"
        )
        
        # Option JSON
        json_data = entities_data.to_json(orient='records', force_ascii=False)
        st.download_button(
            label="💾 Télécharger en JSON",
            data=json_data,
            file_name="entites.json",
            mime="application/json"
        )
    
    # Export des relations
    if entity_relations:
        st.subheader("Export des relations")
        
        relations_df = pd.DataFrame(entity_relations, columns=["Source", "Cible", "Type"])
        csv = relations_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Télécharger en CSV",
            data=csv,
            file_name="relations.csv",
            mime="text/csv"
        )
    
    # Export complet
    if not relations_full.empty:
        st.subheader("Export complet")
        
        csv = relations_full.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Télécharger toutes les données (CSV)",
            data=csv,
            file_name="donnees_completes.csv",
            mime="text/csv"
        )
        
        # Option Excel
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            entities_data.to_excel(writer, sheet_name='Entités', index=False)
            pd.DataFrame(entity_relations, columns=["Source", "Cible", "Type"]).to_excel(writer, sheet_name='Relations', index=False)
            relations_full.to_excel(writer, sheet_name='Données complètes', index=False)
        
        st.download_button(
            label="💾 Télécharger en Excel",
            data=excel_buffer.getvalue(),
            file_name="export_complet.xlsx",
            mime="application/vnd.ms-excel"
        )