# 🧠 Trivia LLM Benchmark & Analytics

Pipeline de données et tableau de bord décisionnel (BI) pour évaluer et comparer les performances de modèles de langage (LLMs locaux) sur un corpus de questions de culture générale.

---

## 📌 Présentation

Ce projet met en place une chaîne d'ingestion, d'évaluation, de transformation et de visualisation analytique selon une architecture **Medallion (Bronze / Silver / Gold)** :
- **Source** : Ingestion de 5 298 questions issues de l'API [Open Trivia Database](https://opentdb.com/).
- **Évaluation LLM** : Soumission automatisée des questions aux modèles via LM Studio (mesure de la précision, de la conformité du format et du temps d'inférence).
- **Transformation (ELT)** : Modélisation analytique avec **dbt** et stockage colonnaire sous **DuckDB**.
- **Visualisation** : Dashboard interactif développé avec **Streamlit** et **Plotly**.

---

## 🏗️ Architecture du Pipeline

```text
[ Open Trivia DB API ]
        │
        ▼ (open_trivia_scraper.py)
[ questions_raw.csv ] ─── (Bronze)
        │
        ▼ (csv_to_parquet.py & ask_ai.py)
[ silver/*.parquet ]  ─── (Silver : Parquet compressé zstd + inférence LLM)
        │
        ▼ (dbt run avec dbt-duckdb)
[ gold/gold.db ]      ─── (Gold : Staging ➔ Intermediate ➔ Data Marts)
        │
        ▼ (streamlit run app.py)
[ Dashboard Streamlit ]
```

---

## 🛠️ Stack Technique

- **Langage & Traitement** : Python 3.10+, PyArrow, Pandas
- **Inférence LLM** : LM Studio SDK (`lmstudio`)
- **Stockage & Analytics** : Parquet, DuckDB
- **Transformation de Données** : dbt (`dbt-duckdb`)
- **Visualisation / Dataviz** : Streamlit, Plotly

---

## 📁 Structure du Projet

```text
├── open_trivia_scraper.py   # Récupération des questions via l'API OpenTDB
├── csv_to_parquet.py        # Conversion du CSV brut en format Parquet (Silver)
├── ask_ai.py                # Script d'évaluation des LLMs via LM Studio
├── dbt_project.yml          # Configuration du projet dbt
├── profiles.yml             # Connexion dbt vers DuckDB (gold/gold.db)
├── models/                  # Modèles SQL dbt
│   ├── staging/             # stg_questions (lecture dynamique des Parquet)
│   ├── intermediate/        # Calculs de précision, normalisation et latence
│   └── marts/               # Marts de restitution (par catégorie, modèle, etc.)
├── silver/                  # Données nettoyées et résultats d'inférence (.parquet)
├── gold/                    # Base analytique DuckDB (gold.db)
└── app.py                   # Application dashboard interactive Streamlit
```

---

## 🚀 Démarrage Rapide

### 1. Prérequis et Dépendances

Installez les bibliothèques requises :

```bash
pip install requests pandas pyarrow duckdb dbt-duckdb streamlit plotly rich tqdm python-dotenv lmstudio
```

> **Note :** LM Studio doit être en cours d'exécution avec le serveur local activé si vous souhaitez exécuter de nouvelles inférences LLM via `ask_ai.py`.

### 2. Exécution du Pipeline de Données

Les données pré-calculées étant déjà disponibles dans `silver/` et `gold/`, certaines étapes sont facultatives si vous souhaitez simplement explorer les résultats.

1. **(Optionnel) Ingestion des données brutes :**
   ```bash
   python open_trivia_scraper.py
   python csv_to_parquet.py
   ```

2. **(Optionnel) Évaluation d'un modèle :**
   Configurez le modèle souhaité dans `ask_ai.py` puis lancez :
   ```bash
   python ask_ai.py
   ```

3. **Transformation des données avec dbt :**
   ```bash
   dbt run --profiles-dir .
   ```

4. **Lancement du Dashboard Streamlit :**
   ```bash
   streamlit run app.py
   ```

---

## 📊 Modèles Comparés

Le benchmark intègre notamment l'évaluation de :
- `llama-3.2-3b-instruct`
- `google/gemma-3-1b`
- `ibm/granite-3.2-8b`
- `liquid/lfm2.5-1.2b`
- `mistralai/ministral-3-3b`

