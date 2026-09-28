-- mart_accuracy_by_difficulty.sql
--
-- Précision de chaque modèle IA par niveau de difficulté (easy, medium, hard).
-- Dérivé du modèle intermédiaire int_accuracy.

with source as (

    select * from {{ ref('int_accuracy') }}

),

aggregated as (

    select
        model_name,
        difficulty,
        sum(total_questions)::bigint                        as total_questions,
        sum(correct_answers)::bigint                        as correct_answers,
        round(
            100.0 * sum(correct_answers) / sum(total_questions),
            2
        )                                                   as accuracy_pct

    from source
    group by model_name, difficulty

)

select *
from aggregated
order by model_name, difficulty
