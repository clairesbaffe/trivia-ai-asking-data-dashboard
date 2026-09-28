
  
  create view "gold"."main"."stg_questions__dbt_tmp" as (
    -- stg_questions.sql
--
-- Vue de staging unifiée pour tous les fichiers questions-*.parquet.
--
-- Stratégie : schéma long (long format)
--   - Une ligne = une paire (question, modèle IA)
--   - Les colonnes communes à la question (category, type, difficulty, etc.)
--     ne sont pas dupliquées dans des colonnes séparées par modèle.
--   - La colonne `model_name` identifie le modèle, extraite du nom de fichier.
--   - `questions.parquet` (sans suffixe modèle) reçoit la valeur NULL dans
--     `model_name`, indiquant l'absence de réponse IA.
--
-- Extensibilité : tout nouveau fichier `questions-<modele>.parquet` déposé
-- dans le dossier silver est automatiquement inclus grâce au glob *.parquet
-- déclaré dans sources.yml. Aucune modification SQL n'est nécessaire.

with source as (

    select
        category,
        type,
        difficulty,
        question,
        correct_answer,
        incorrect_answer_1,
        incorrect_answer_2,
        incorrect_answer_3,
        ai_answer,
        ai_correct,
        response_time,

        replace(regexp_extract(filename, 'questions-(.+)\.parquet$', 1), '--', '/') as model_name,

        filename as source_file

    from read_parquet('./silver/questions-*.parquet')

)

select *
from source
  );
