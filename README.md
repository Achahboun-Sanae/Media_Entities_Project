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
    "source": "Le360_fr",
    "categorie": categorie,
    "date": date_publication
}

### 📌 4. Gestion des doublons
   - Avant d'ajouter chaque article dans la base de données, une vérification est effectuée pour éviter les doublons, assurant ainsi une base de données propre et sans redondance.

---

## ⚙️ Technologies Utilisées

- **Python** : Langage de programmation utilisé pour le scraping et le traitement des données.
- **BeautifulSoup** : Bibliothèque pour l'analyse et l'extraction des informations des pages web HTML.
- **Requests** : Bibliothèque pour effectuer des requêtes HTTP et récupérer les pages des articles.
- **MongoDB & MongoDB Atlas** : Base de données NoSQL utilisée pour stocker les articles collectés.
- **MongoDB Atlas** : permet un accès distant sécurisé pour tous les membres de l'équipe.

---
## 📌 Auteur
- 🛠 Projet réalisé par une équipe de 4 personnes
- **Année** : 2025
