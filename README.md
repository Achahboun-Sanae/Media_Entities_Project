## 📌 Projet SD : Extraction et Visualisation des Entités Médiatiques Marocaines
Ce projet vise à extraire et visualiser des entités médiatiques marocaines à partir de sites d'actualités.

🔹 **Cette première étape du projet** est consacrée à **la collecte et au stockage des articles**. Elle comprend les phases suivantes :

- **Collecte des URLs des articles**
- **Scraping du contenu des articles**
- **Stockage structuré dans MongoDB**
- **Élimination des doublons**

Les prochaines étapes incluront **le traitement NLP**, **la structuration des données** et **la visualisation des résultats**.

---

## 🔍 Fonctionnalités  

### 📌 1. Collecte des URLs des articles  
- Extraction des liens des articles à partir des pages de catégories des sites d'actualités marocains  
- Les catégories concernées incluent, par exemple, la culture et d'autres sections pertinentes du site

### 📌 2. Scraping du contenu des articles  
- Extraction des informations clés des articles :  
  - **Titre**  
  - **Auteur**  
  - **Contenu**  
  - **Date de publication**  
  - **Catégorie**  
- Vérification et nettoyage des données avant stockage 

### 📌 3. Stockage des données 
- Les articles collectés et analysés sont stockés dans une base de données **MongoDB**, ce qui permet une gestion flexible et évolutive des données
- **MongoDB Atlas** est utilisé pour offrir un accès sécurisé et distant à tous les membres de l'équipe
- Structure de stockage :

```python
article_data = {
    "url": url,
    "titre": titre,
    "auteur": auteur,
    "contenu": contenu,
    "source": source,  # "ChoufTv", "Hespress", "Akhbarona" ou "Le360"
    "categorie": categorie,
    "date": date_publication
}
```

### 📌 4. Gestion des doublons
- Vérification avant chaque ajout pour éviter les doublons
- Base de données propre et sans redondance

---

## ⚙️ Technologies Utilisées (Phase 1)
- **Python** : Langage principal
- **BeautifulSoup** : Extraction des informations HTML
- **Requests** : Requêtes HTTP
- **MongoDB & MongoDB Atlas** : Stockage des données

---

## Description de la Deuxième Étape : Traitement NLP

Ce projet se concentre sur l'application du traitement automatique du langage naturel (NLP) pour nettoyer et structurer des données textuelles.

### Fonctionnalités Clés
- **Traitement NLP** : 
  - Nettoyage des textes (ponctuations, stopwords)
  - Tokenisation et lemmatisation
  - Reconnaissance d'entités nommées (NER)
  
- **Structuration des données** : 
  - Stockage dans PostgreSQL (relationnel)
  - Stockage dans Neo4j (graphique)

- **Fonctionnalités Générales** :
  - Extraction des entités (personnes, lieux, organisations)
  - Analyse des relations entre entités

### Technologies Utilisées (Phase 2)
- **SpaCy**, **BERT**, **nltk** : Traitement NLP
- **Stanza** : Modèles NLP de Stanford
- **transformers** : Modèles de deep learning
- **PostgreSQL** : Base relationnelle
- **Supbase** : Alternative à Firebase
- **Neo4j** : Base de données graphique

---

## 📊 Phase 3 : Visualisation des Données

### Fonctionnalités de Visualisation

#### Tableau de Bord Interactif
- **Statistiques globales** : Nombre d'entités, relations, articles analysés
- **Filtres avancés** : Par période, source média, type d'entité
- **Visualisations** :
  - Évolution temporelle des relations
  - Matrice de cooccurrence
  - Répartition des types de relations
  - Distribution des types d'entités

#### Exploration des Entités
- Recherche et filtrage des entités
- Analyse détaillée par entité (relations entrantes/sortantes)
- Graphiques de répartition

#### Réseau Relationnel
- Visualisation interactive des relations entre entités
- Paramètres de style personnalisables
- Détection de communautés
- Analyse des connexions (degrés, densité)

#### Analyse des Articles
- Statistiques par source médiatique
- Chronologie des publications
- Entités les plus citées
- Détails des articles

#### Cartographie
- Visualisation géographique des entités
- Clustering des marqueurs
- Heatmap des mentions
- Statistiques de géolocalisation

#### Export des Données
- Formats supportés : CSV, JSON, Excel
- Export des entités, relations ou données complètes

### Technologies de Visualisation
- **Streamlit** : Interface interactive
- **Plotly** : Visualisations avancées
- **NetworkX** : Analyse de réseaux
- **PyVis** : Visualisation de graphes
- **Folium** : Cartographie interactive
- **Altair** : Visualisations déclaratives

---

## 📌 Auteurs
- 🛠 Projet réalisé par une équipe de 4 personnes
- **Année** : 2025
