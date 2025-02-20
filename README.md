# Media_Entities_Project

## Projet SD : Extraction et Visualisation des Entités Médiatiques Marocaines

Ce projet a pour objectif d'extraire et de visualiser des entités médiatiques marocaines à partir de sites d'actualités. La première phase du projet est centrée sur la collecte des données médiatiques, en utilisant des techniques de *web scraping* pour récupérer des articles en arabe et en français à partir de sources d'actualités en ligne.

---

## Fonctionnalités principales

### 1. **Collecte des URLs d'articles**
   - L'extraction des URLs des articles se fait à partir des pages de catégories spécifiques sur les sites d'actualités marocains.
   - Les catégories concernées incluent, par exemple, la culture et d'autres sections pertinentes du site.

### 2. **Scraping du contenu des articles**
   - Une fois les URLs des articles extraites, chaque article est scrappé pour en récupérer les éléments suivants :
     - **Titre** de l'article
     - **Auteur** de l'article
     - **Contenu** complet de l'article
   - Le contenu est ensuite structuré et nettoyé pour être stocké dans une base de données.

### 3. **Stockage dans MongoDB et MongoDB Atlas**
   - Les articles collectés et analysés sont stockés dans une base de données **MongoDB**, ce qui permet une gestion flexible et évolutive des données.
   - **MongoDB Atlas** est utilisé pour offrir un accès sécurisé et distant à tous les membres de l'équipe, permettant une collaboration efficace et un accès aux données depuis n'importe où.
   - La base de données permet de gérer efficacement les articles collectés et de garantir des performances élevées lors de l'accès aux informations.

### 4. **Gestion des doublons**
   - Avant d'ajouter chaque article dans la base de données, une vérification est effectuée pour éviter les doublons, assurant ainsi une base de données propre et sans redondance.

---

## Technologies utilisées

- **Python** : Langage de programmation utilisé pour le scraping et le traitement des données.
- **BeautifulSoup** : Bibliothèque pour l'analyse et l'extraction des informations des pages web HTML.
- **Requests** : Bibliothèque pour effectuer des requêtes HTTP et récupérer les pages des articles.
- **MongoDB & MongoDB Atlas** : Base de données NoSQL utilisée pour stocker les articles collectés. **MongoDB Atlas** permet un accès distant sécurisé pour tous les membres de l'équipe.

---
