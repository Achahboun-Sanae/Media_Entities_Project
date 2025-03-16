## 📌 Projet SD : Extraction et Visualisation des Entités Médiatiques Marocaines
Ce projet vise à extraire et visualiser des entités médiatiques marocaines à partir de sites d’actualités.

🔹 **Cette première étape du projet** est consacrée à **la collecte et au stockage des articles**. Elle comprend les phases suivantes :

- **Collecte des URLs des articles**.
- **Scraping du contenu des articles**.
- **Stockage structuré dans MongoDB**.
- **Élimination des doublons**.
  
Les prochaines étapes incluront **le traitement NLP**, **la structuration des données** et **la visualisation des résultats**.

---

## 🔍 Fonctionnalités  

### 📌 1. Collecte des URLs des articles  
- Extraction des liens des articles à partir des pages de catégories des sites d'actualités marocains.  
- Les catégories concernées incluent, par exemple, la culture et d'autres sections pertinentes du site.


### 📌 2. Scraping du contenu des articles  
- Extraction des informations clés des articles :  
  - **Titre**  
  - **Auteur**  
  - **Contenu**  
  - **Date de publication**  
  - **Catégorie**  

- Vérification et nettoyage des données avant stockage. 


### 📌 3. Stockage des données 
   - Les articles collectés et analysés sont stockés dans une base de données **MongoDB**, ce qui permet une gestion flexible et évolutive des données.
   - **MongoDB Atlas** est utilisé pour offrir un accès sécurisé et distant à tous les membres de l'équipe, permettant une collaboration efficace et un accès aux données depuis n'importe où.
   - La base de données permet de gérer efficacement les articles collectés et de garantir des performances élevées lors de l'accès aux informations.
   - Les articles collectés sont stockés dans **MongoDB Atlas**, avec la structure suivante :  

```python
article_data = {
    "url": url,
    "titre": titre,
    "auteur": auteur,
    "contenu": contenu,
    "source": source,  # où 'source' peut être "ChoufTv", "Hespress", ou "Akhbarona", ou "Le360" 
    "categorie": categorie,
    "date": date_publication
}
  ```

### 📌 4. Gestion des doublons
   - Avant d'ajouter chaque article dans la base de données, une vérification est effectuée pour éviter les doublons, assurant ainsi une base de données propre et sans redondance.

---

## ⚙️ Technologies Utilisées

- **Python** : Langage de programmation utilisé pour le scraping et le traitement des données.
- **BeautifulSoup** : Bibliothèque pour l'analyse et l'extraction des informations des pages web HTML.
- **Requests** : Bibliothèque pour effectuer des requêtes HTTP et récupérer les pages des articles.
- **MongoDB & MongoDB Atlas** : Base de données NoSQL utilisée pour stocker les articles collectés.
- **MongoDB Atlas** : permet un accès distant sécurisé pour tous les membres de l'équipe.

## Description de la deuxieme Etape : 

Ce projet se concentre sur l'application du traitement automatique du langage naturel (NLP) pour nettoyer et structurer des données textuelles. Il utilise des techniques avancées telles que la **tokenisation**, la **lemmatisation**, et la **reconnaissance d'entités nommées (NER)** à l'aide de modèles NLP comme SpaCy, BERT et Stanford NLP.

### Fonctionnalités Clés

- **Traitement NLP** : 
  - **Nettoyage des textes** : Suppression des ponctuations et des stopwords.
  - **Tokenisation** : Division des textes en mots ou tokens individuels.
  - **Lemmatisation** : Réduction des mots à leur forme de base.
  - **Application de NER** : Identification des entités telles que les personnes, lieux, organisations et événements.

- **Structuration des données** : 
  - **Enregistrement dans une base SQL (PostgreSQL)** : Stockage structuré des entités et relations pour faciliter les requêtes.
  - **Enregistrement dans une base graphique (Neo4j)** : Modélisation des relations complexes entre entités.

- **Fonctionnalités Générales du Système** :
  - **Extraction des entités** : Identification automatique des noms de personnes, lieux, organisations et événements.
  - **Stockage structuré** : Organisation des données en bases relationnelles et graphiques.
  - **Analyse des relations** : Etablissement des liens entre les entités détectées.
---

### Technologies Utilisées

- **SpaCy** : Pour la tokenisation et la reconnaissance d'entités.
- **BERT** : Pour des analyses plus avancées du langage.
- **nltk** : Bibliothèque de traitement du langage naturel en Python, utilisée pour la tokenisation, la lemmatisation, l'analyse syntaxique et la reconnaissance d'entités nommées.
- **Stanza** : Bibliothèque NLP de Stanford offrant des modèles pré-entraînés pour plusieurs langues, utilisée pour l'analyse morphologique, syntaxique et la reconnaissance d'entités nommées.
- **transformers** : Bibliothèque de Hugging Face permettant d'utiliser des modèles de deep learning pour le NLP, 
- **PostgreSQL** : Pour le stockage relationnel.
- **Supbase** : Pour le stockage relationnelAlternative open-source à Firebase, basée sur PostgreSQL, offrant base de données, authentification, stockage et fonctions serverless..
- **Neo4j** : Pour le stockage graphique.

---
## 📌 Auteur
- 🛠 Projet réalisé par une équipe de 4 personnes
- **Année** : 2025
