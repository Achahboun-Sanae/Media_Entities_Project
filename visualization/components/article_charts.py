import plotly.express as px
import streamlit as st
import pandas as pd
from datetime import datetime
from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import numpy as np
import seaborn as sns

# Configuration
plt.style.use('ggplot')
COLORS = px.colors.qualitative.Plotly
sns.set_palette("husl")

def prepare_data(data):
    """Prépare les données pour l'analyse"""
    if not data:
        st.warning("Aucune donnée disponible")
        return None
    
    try:
        df = pd.DataFrame(data)
        
        # Conversion des dates
        df['date'] = pd.to_datetime(df['date'])
        df['jour'] = df['date'].dt.date
        df['heure'] = df['date'].dt.hour
        df['jour_semaine'] = df['date'].dt.day_name()
        
        if 'date_import' in df.columns:
            df['date_import'] = pd.to_datetime(df['date_import'])
            df['delai_heures'] = (df['date_import'] - df['date']).dt.total_seconds() / 3600
        
        # Analyse textuelle
        if 'contenu' in df.columns:
            df['contenu'] = df['contenu'].str.replace(r'<[^>]*>', '', regex=True)
            df['nb_mots'] = df['contenu'].str.split().str.len()
            df['sentiment'] = df['contenu'].apply(lambda x: TextBlob(str(x)).sentiment.polarity)
            df['sentiment_cat'] = pd.cut(df['sentiment'], 
                                        bins=[-1, -0.1, 0.1, 1],
                                        labels=['Négatif', 'Neutre', 'Positif'])
        
        return df
    
    except Exception as e:
        st.error(f"Erreur de préparation: {str(e)}")
        return None

def display_main_chart(data):
    """Graphique principal pour le français/anglais"""
    df = prepare_data(data)
    if df is None:
        return
    
    df_counts = df.groupby(['date', 'source']).size().reset_index(name='count')
    
    fig = px.bar(
        df_counts,
        x="date",
        y="count",
        color="source",
        title="Publications par source",
        labels={'count': "Nombre d'articles", 'date': "Date"},
        color_discrete_sequence=COLORS
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

def display_rtl_chart(data):
    """Graphique pour l'arabe (RTL)"""
    df = prepare_data(data)
    if df is None:
        st.warning("لا توجد بيانات متاحة")
        return
    
    df_counts = df.groupby(['date', 'source']).size().reset_index(name='count')
    
    fig = px.bar(
        df_counts,
        x="date",
        y="count",
        color="source",
        title="المنشورات حسب المصدر",
        color_discrete_sequence=COLORS
    )
    
    fig.update_layout(
        xaxis_title="التاريخ",
        yaxis_title="عدد المقالات",
        font=dict(size=14, family='Arial'),
        xaxis_tickangle=-45,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

def display_timeseries_chart(df):
    """Graphique temporel avec moyenne mobile"""
    if df is None:
        return
        
    df_daily = df.groupby(['jour', 'source']).size().reset_index(name='count')
    df_daily['moyenne_mobile'] = df_daily.groupby('source')['count'].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )
    
    fig = px.line(
        df_daily,
        x="jour",
        y="moyenne_mobile",
        color="source",
        title="Tendance des publications (moyenne mobile sur 7 jours)",
        labels={'moyenne_mobile': "Nombre moyen d'articles", 'jour': "Date"},
        color_discrete_sequence=COLORS
    )
    
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def display_hourly_distribution(df):
    """Distribution horaire des publications"""
    if df is None:
        return
    
    fig = px.histogram(
        df,
        x="heure",
        color="source",
        nbins=24,
        title="Distribution horaire des publications",
        labels={'heure': "Heure de la journée", 'count': "Nombre d'articles"},
        color_discrete_sequence=COLORS,
        barmode='group'
    )
    
    fig.update_layout(
        xaxis=dict(tickvals=list(range(24))),
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def display_weekday_distribution(df):
    """Distribution par jour de semaine"""
    if df is None:
        return
    
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['jour_semaine'] = pd.Categorical(df['jour_semaine'], categories=weekday_order, ordered=True)
    
    fig = px.histogram(
        df,
        x="jour_semaine",
        color="source",
        title="Activité par jour de semaine",
        labels={'jour_semaine': "Jour de la semaine", 'count': "Nombre d'articles"},
        color_discrete_sequence=COLORS,
        barmode='group'
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def display_sentiment_analysis(df):
    """Analyse de sentiment"""
    if df is None or 'sentiment_cat' not in df.columns:
        return
    
    fig = px.pie(
        df,
        names="sentiment_cat",
        color="sentiment_cat",
        title="Distribution des sentiments",
        color_discrete_map={
            'Positif': '#2CA02C',
            'Neutre': '#FF7F0E',
            'Négatif': '#D62728'
        }
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        showlegend=True
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

def display_word_length_distribution(df):
    """Distribution de la longueur des articles"""
    if df is None or 'nb_mots' not in df.columns:
        return
    
    fig = px.box(
        df,
        x="source",
        y="nb_mots",
        color="source",
        title="Longueur des articles (nombre de mots)",
        labels={'nb_mots': "Nombre de mots", 'source': "Source"},
        color_discrete_sequence=COLORS
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def generate_wordcloud(df, lang='fr'):
    """Génère un nuage de mots"""
    if df is None or 'contenu' not in df.columns:
        return
    
    try:
        text = ' '.join(df['contenu'].astype(str))
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='viridis',
            max_words=100
        ).generate(text)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title('Nuage de mots fréquents', fontsize=16)
        
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Erreur lors de la génération du nuage de mots: {str(e)}")

def display_top_words(df, n=20):
    """Affiche les mots les plus fréquents"""
    if df is None or 'contenu' not in df.columns:
        return
    
    try:
        words = ' '.join(df['contenu'].astype(str)).split()
        common_words = Counter(words).most_common(n)
        words_df = pd.DataFrame(common_words, columns=['Mot', 'Fréquence'])
        
        fig = px.bar(
            words_df,
            x='Fréquence',
            y='Mot',
            orientation='h',
            title=f"Top {n} mots les plus fréquents",
            color='Fréquence',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            height=600,
            yaxis={'categoryorder': 'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur lors de l'analyse des mots: {str(e)}")

def display_source_distribution(df):
    """Répartition par source"""
    if df is None:
        return
    
    source_counts = df['source'].value_counts().reset_index()
    source_counts.columns = ['Source', 'Nombre d\'articles']
    
    fig = px.pie(
        source_counts,
        values='Nombre d\'articles',
        names='Source',
        title='Répartition par source médiatique',
        color_discrete_sequence=COLORS,
        hole=0.3
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

def display_import_delay(df):
    """Délai d'import des articles"""
    if df is None or 'delai_heures' not in df.columns:
        return
    
    fig = px.box(
        df,
        x="source",
        y="delai_heures",
        color="source",
        title="Délai d'import des articles (heures)",
        labels={'delai_heures': "Délai (heures)", 'source': "Source"},
        color_discrete_sequence=COLORS
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def display_sentiment_trend(df):
    """Tendance des sentiments au fil du temps"""
    if df is None or 'sentiment' not in df.columns:
        return
    
    df_daily = df.groupby('jour').agg({'sentiment': 'mean', 'source': 'count'}).reset_index()
    df_daily.columns = ['jour', 'sentiment_moyen', 'nombre_articles']
    
    fig = px.line(
        df_daily,
        x="jour",
        y="sentiment_moyen",
        title="Évolution du sentiment moyen",
        labels={'sentiment_moyen': "Sentiment moyen", 'jour': "Date"},
        color_discrete_sequence=['#636EFA']
    )
    
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)