-- mart_model_accuracy.sql
--
-- Précision globale de chaque modèle IA (toutes catégories et difficultés confondues).
-- Dérivé du modèle intermédiaire int_accuracy.

with source as (

    select * from {{ ref('int_accuracy') }}

),

aggregated as (

    select
        model_name,
        sum(total_questions)::bigint                        as total_questions,
        sum(correct_answers)::bigint                        as correct_answers,
        round(
            100.0 * sum(correct_answers) / sum(total_questions),
            2
        )                                                   as accuracy_pct

    from source
    group by model_name

)

select *
from aggregated
order by accuracy_pct desc
