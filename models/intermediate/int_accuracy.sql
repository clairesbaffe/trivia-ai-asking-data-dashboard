-- int_accuracy.sql
--
-- Modèle intermédiaire centralisant le calcul de l'accuracy et le suivi du formattage.
-- Agrège les questions évaluées par toutes les dimensions analytiques :
--   - model_name    : modèle IA
--   - category      : domaine thématique
--   - difficulty    : niveau de difficulté (easy, medium, hard)
--   - question_type : format de la question (boolean, multiple)
--
-- Règle métier importante :
-- Les réponses non formatées (ai_answer IS NULL ou vide) sont comptabilisées
-- dans le total des questions mais PAS dans les bonnes réponses (ai_correct = true).
-- Elles sont donc automatiquement comptées comme des réponses fausses / échouées.

with source as (

    select * from {{ ref('stg_questions') }}

    -- Exclure les questions sans réponse de modèle IA
    where model_name is not null

),

aggregated as (

    select
        model_name,
        category,
        difficulty,
        type                                                                as question_type,
        count(*)::bigint                                                    as total_questions,
        count(*) filter (ai_correct = true)::bigint                         as correct_answers,
        count(*) filter (ai_answer is null or trim(ai_answer) = '')::bigint as unformatted_answers,
        count(*) filter (
            ai_correct = false and ai_answer is not null and trim(ai_answer) != ''
        )::bigint                                                           as incorrect_answers,
        round(
            100.0 * count(*) filter (ai_correct = true) / count(*),
            2
        )                                                                   as accuracy_pct

    from source
    group by model_name, category, difficulty, type

)

select *
from aggregated
