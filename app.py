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
    st.session_state.theme_selector = "Sombre"

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

page = option_menu(
    menu_title=None,
    options=["Tableau de bord", "Entités", "Graphe", "Statistiques", "Articles", "Carte", "Export"],
    icons=["bar-chart", "search", "diagram-3", "graph-up", "newspaper", "map", "download"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important"},
        "nav-link": {"font-size": "14px", "margin": "0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#ff6600"},
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

        # Onglets : Tableau + Visualisations
        tab1, tab2 = st.tabs(["📋 Données tabulaires", "📈 Visualisations"])

        with tab1:
            st.dataframe(
                stats_df.sort_values("Nombre d'articles", ascending=False),
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
                height=400,
                use_container_width=True
            )
            st.download_button("📥 Télécharger les données", stats_df.to_csv(index=False), "statistiques_sources.csv")

        with tab2:
            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(
                    stats_df.nlargest(10, "Nombre d'articles"),
                    x='Source', y="Nombre d'articles",
                    title="Top 10 des sources par nombre d'articles", color='Source'
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.scatter(
                    stats_df,
                    x="Nombre d'articles", y='Nombre de relations',
                    size='Nombre de relations',
                    color='Source',
                    title="Corrélation Articles vs Relations",
                    hover_name='Source',
                    log_x=True, log_y=True
                )
                st.plotly_chart(fig, use_container_width=True)

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
            sources = source_data['nom_source'].value_counts()
            targets = source_data['nom_cible'].value_counts()
            top_entities = (sources + targets).fillna(0).astype(int).sort_values(ascending=False).head(20)

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
                articles_to_show = source_data.drop_duplicates('article_id')
            else:
                articles_to_show = source_data

            st.dataframe(
                articles_to_show,
                column_config={
                    "date": "Date",
                    "title": "Titre",
                    "url": st.column_config.LinkColumn("URL")
                },
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
        # Constantes pour les styles
        TYPE_ICONS = {
            'PER': '👤', 'LOC': '🌍', 
            'ORG': '🏢', 'EVENT': '🎪',
            'MISC': '🔮'
        }

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
                default=list(entities_data['Type'].unique()),
                format_func=lambda x: f"{TYPE_ICONS.get(x, '🔘')} {x}"
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
                title=f"{entity} ({entity_type}) - {occurrences} connexions",  # Tooltip simplifié
                group=entity_type,
                size=node_size + occurrences**0.5,
                color=NODE_COLORS.get(entity_type, '#999999'),  # Couleur par type
                shape='dot',  # Tous les nœuds en cercle
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
                # Remplacer le HTML par du texte simple
                title=f"{rel_type}\n────────────\nConnections: {count}",  # Format texte simple
                label=rel_type if show_labels else "",
                width=edge_width * min(3, count**0.5),
                color=EDGE_COLORS.get(rel_type.split('_')[0], '#cccccc'),
                smooth={'type': 'continuous'},
                # Ajouter ces options pour un meilleur rendu
                font={
                    'size': font_size - 2,  # Taille légèrement plus petite que les nœuds
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
            # Solution robuste pour l'encodage (spécialement pour l'arabe)
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
    st.title("📈 Statistiques avancées")
    
    if not entities_data.empty or entity_relations:
        tab1, tab2, tab3 = st.tabs(["📌 Entités", "🔗 Relations", "🗝️ Mots-clés"])

        # ================================
        # TAB 1 — ENTITÉS
        # ================================
        with tab1:
            st.subheader("Analyse interactive des entités")
            
            if not entities_data.empty:
                entity_types = entities_data['Type'].unique().tolist()
                selected_types = st.multiselect("Filtrer par type d'entité :", entity_types, default=entity_types)

                filtered_entities = entities_data[entities_data['Type'].isin(selected_types)]

                col1, col2 = st.columns(2)

                with col1:
                    top_entities = filtered_entities.sort_values('Occurrences', ascending=False).head(15)
                    fig = px.bar(
                        top_entities, 
                        x='Occurrences', 
                        y='Nom', 
                        color='Type', 
                        orientation='h',
                        title="🎯 Top 15 des entités les plus mentionnées",
                        labels={'Occurrences': 'Nombre d’occurrences', 'Nom': 'Entité'}
                    )
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    type_counts = filtered_entities['Type'].value_counts().reset_index()
                    type_counts.columns = ['Type', 'Nombre']
                    fig = px.pie(type_counts, names='Type', values='Nombre', hole=0.4,
                                 title="📂 Répartition des types d’entités")
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("#### 📊 Distribution des occurrences (log-scale possible)")
                log_scale = st.checkbox("Utiliser l’échelle logarithmique", value=False)
                fig = px.histogram(
                    filtered_entities,
                    x='Occurrences',
                    nbins=40,
                    title="Distribution des occurrences d’entités",
                    log_y=log_scale
                )
                st.plotly_chart(fig, use_container_width=True)

        # ================================
        # TAB 2 — RELATIONS
        # ================================
        with tab2:
            st.subheader("Exploration des relations")

            if entity_relations:
                relations_df = pd.DataFrame(entity_relations, columns=["Source", "Target", "Type"])
                top_relation_types = relations_df['Type'].value_counts().head(10).reset_index()
                top_relation_types.columns = ['Type', 'Nombre']

                col1, col2 = st.columns(2)

                with col1:
                    fig = px.bar(
                        top_relation_types,
                        x='Nombre',
                        y='Type',
                        orientation='h',
                        title="🔗 Top 10 des types de relations",
                        color='Nombre',
                        color_continuous_scale='Viridis'
                    )
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    try:
                        rel_with_types = relations_df.merge(
                            entities_data[['Nom', 'Type']].rename(columns={'Nom': 'Source', 'Type': 'SourceType'}),
                            on='Source'
                        ).merge(
                            entities_data[['Nom', 'Type']].rename(columns={'Nom': 'Target', 'Type': 'TargetType'}),
                            on='Target'
                        )
                        type_pairs = rel_with_types.groupby(['SourceType', 'TargetType']).size().reset_index(name='count')
                        fig = px.sunburst(
                            type_pairs,
                            path=['SourceType', 'TargetType'],
                            values='count',
                            title="🌐 Répartition des relations par type d'entités"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error("Erreur lors de la jointure avec les types d'entités.")

                if not relations_full.empty and 'date' in relations_full.columns:
                    st.markdown("#### ⏳ Évolution temporelle des types de relations")
                    try:
                        rel_temp = relations_full.copy()
                        rel_temp['date'] = pd.to_datetime(rel_temp['date'])
                        rel_temp['mois'] = rel_temp['date'].dt.to_period('M').astype(str)

                        selected_types = st.multiselect("Filtrer les types de relation :", 
                                                        sorted(rel_temp['relation'].unique()), 
                                                        default=rel_temp['relation'].unique())

                        filtered_temp = rel_temp[rel_temp['relation'].isin(selected_types)]
                        monthly_rel = filtered_temp.groupby(['mois', 'relation']).size().reset_index(name='count')

                        fig = px.line(
                            monthly_rel, 
                            x='mois', 
                            y='count', 
                            color='relation',
                            title="📅 Volume mensuel par type de relation"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning("Impossible d’afficher l’évolution temporelle.")

        # ================================
        # TAB 3 — MOTS-CLÉS
        # ================================
        with tab3:
            st.subheader("🧠 Analyse des mots-clés dans les relations")

            if not relations_full.empty and 'relation' in relations_full.columns:
                all_words = ' '.join(relations_full['relation'].astype(str)).split()
                word_freq = Counter(all_words).most_common(40)

                col1, col2 = st.columns([2, 1])

                with col1:
                    fig = px.bar(
                        x=[w[0] for w in word_freq],
                        y=[w[1] for w in word_freq],
                        labels={'x': 'Mot', 'y': 'Fréquence'},
                        title="📌 Fréquence des mots les plus utilisés"
                    )
                    st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Aucune donnée disponible pour les statistiques.")
elif page == "Carte":
    st.title("🗺️ Visualisation cartographique des entités")
    
    if not entities_data.empty and 'Nom' in entities_data.columns:
        from streamlit_folium import folium_static
        import folium
        from geopy.geocoders import Nominatim
        from geopy.extra.rate_limiter import RateLimiter
        from folium.plugins import MarkerCluster, HeatMap
        import time

        # Configuration initiale
        st.markdown("""
        <style>
            .map-container {
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                overflow: hidden;
                margin-bottom: 20px;
            }
        </style>
        """, unsafe_allow_html=True)

        # Dictionnaire de cache pour les localisations déjà trouvées
        if 'location_cache' not in st.session_state:
            st.session_state.location_cache = {
                # Exemple de cache initial
                "Paris": (48.8566, 2.3522),
                "New York": (40.7128, -74.0060),
                "Londres": (51.5074, -0.1278)
            }

        # Configuration de la carte
        with st.expander("⚙️ Paramètres", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                map_type = st.selectbox("Type de carte", 
                                      ["OpenStreetMap", "Stamen Terrain", "CartoDB positron"])
                zoom = st.slider("Niveau de zoom", 1, 15, 5)
            with col2:
                cluster = st.checkbox("Regrouper les marqueurs", True)
                heatmap = st.checkbox("Afficher heatmap", False)
                show_missing = st.checkbox("Afficher les entités non trouvées", False)

        # Filtrer les entités géographiques
        geo_types = ['ville', 'city', 'pays', 'country', 'lieu', 'location', 'loc', 'place', 'region']
        geo_entities = entities_data[
            entities_data['Type'].str.lower().isin(geo_types)
        ].copy()

        if geo_entities.empty:
            st.warning("Aucune entité géographique trouvée dans les données.")
            st.stop()

        # Initialisation du géocodeur
        geolocator = Nominatim(user_agent="geo_dashboard", timeout=10)
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

        # Fonction de géocodage avec cache
        def get_location(entity_name):
            # Vérifier d'abord dans le cache
            if entity_name in st.session_state.location_cache:
                return st.session_state.location_cache[entity_name]
            
            try:
                location = geocode(entity_name)
                if location:
                    coord = (location.latitude, location.longitude)
                    st.session_state.location_cache[entity_name] = coord
                    return coord
            except Exception as e:
                st.warning(f"Erreur de géocodage pour {entity_name}: {str(e)}")
            return None

        # Géocodage des entités
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        valid_entities = []
        missing_entities = []
        
        for i, row in geo_entities.iterrows():
            entity_name = str(row['Nom']).strip()
            coord = get_location(entity_name)
            
            if coord:
                valid_entities.append({
                    'name': entity_name,
                    'type': row['Type'],
                    'count': row.get('Occurrences', 1),
                    'lat': coord[0],
                    'lon': coord[1]
                })
            else:
                missing_entities.append(entity_name)
            
            # Mise à jour de la progression
            progress = (i + 1) / len(geo_entities)
            progress_bar.progress(min(progress, 1.0))
            status_text.text(f"Traitement {i+1}/{len(geo_entities)} - Trouvées: {len(valid_entities)}")

        progress_bar.empty()
        status_text.empty()

        if not valid_entities:
            st.error("Aucune localisation n'a pu être déterminée")
            st.stop()

        # Création de la carte
        m = folium.Map(
            location=[valid_entities[0]['lat'], valid_entities[0]['lon']],
            zoom_start=zoom,
            tiles=map_type,
            control_scale=True
        )

        # Cluster de marqueurs si activé
        if cluster:
            marker_cluster = MarkerCluster().add_to(m)

        # Ajout des marqueurs
        for loc in valid_entities:
            popup_content = f"""
            <div style="width: 250px;">
                <h4 style="margin-bottom: 5px;">{loc['name']}</h4>
                <hr style="margin: 5px 0;">
                <p><b>Type:</b> {loc['type']}</p>
                <p><b>Mentions:</b> {loc['count']}</p>
            </div>
            """
            
            icon = folium.Icon(
                icon='map-marker',
                color='blue' if loc['count'] > 5 else 'green',
                prefix='fa'
            )
            
            marker = folium.Marker(
                [loc['lat'], loc['lon']],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{loc['name']} ({loc['count']})",
                icon=icon
            )
            
            if cluster:
                marker.add_to(marker_cluster)
            else:
                marker.add_to(m)

        # Heatmap si activée
        if heatmap:
            heat_data = [[loc['lat'], loc['lon'], loc['count']] for loc in valid_entities]
            HeatMap(heat_data, radius=15).add_to(m)

        # Contrôles utiles
        folium.plugins.Fullscreen().add_to(m)
        folium.plugins.MousePosition().add_to(m)

        # Affichage de la carte
        with st.container():
            st.markdown("<div class='map-container'>", unsafe_allow_html=True)
            folium_static(m, width=1000, height=600)
            st.markdown("</div>", unsafe_allow_html=True)

        # Statistiques
        st.subheader("📊 Statistiques")
        cols = st.columns(3)
        cols[0].metric("Localisations trouvées", len(valid_entities))
        cols[1].metric("Entités non trouvées", len(missing_entities))
        cols[2].metric("Taux de succès", f"{len(valid_entities)/len(geo_entities)*100:.1f}%")

        # Affichage des entités non trouvées
        if show_missing and missing_entities:
            with st.expander("🔍 Entités non localisées"):
                st.write("Ces entités n'ont pas pu être géolocalisées :")
                st.write(missing_entities)
                
                # Bouton pour ajouter manuellement au cache
                selected_missing = st.selectbox("Sélectionner une entité à ajouter manuellement", 
                                              missing_entities)
                col_lat, col_lon = st.columns(2)
                with col_lat:
                    manual_lat = st.number_input("Latitude", value=0.0)
                with col_lon:
                    manual_lon = st.number_input("Longitude", value=0.0)
                
                if st.button("Ajouter au cache"):
                    st.session_state.location_cache[selected_missing] = (manual_lat, manual_lon)
                    st.success(f"{selected_missing} ajouté au cache avec les coordonnées ({manual_lat}, {manual_lon})")

        # Export des données
        if st.button("💾 Exporter les localisations trouvées"):
            df = pd.DataFrame(valid_entities)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Télécharger CSV",
                data=csv,
                file_name="localisations_trouvees.csv",
                mime="text/csv"
            )
            
        if st.button("💾 Exporter le cache des localisations"):
            cache_df = pd.DataFrame.from_dict(st.session_state.location_cache, 
                                            orient='index',
                                            columns=['Latitude', 'Longitude'])
            cache_df.reset_index(inplace=True)
            cache_df.rename(columns={'index': 'Nom'}, inplace=True)
            csv = cache_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Télécharger Cache",
                data=csv,
                file_name="cache_localisations.csv",
                mime="text/csv"
            )
    else:
        st.warning("Aucune donnée géographique disponible")

