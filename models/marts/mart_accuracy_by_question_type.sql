-- mart_accuracy_by_question_type.sql
--
-- Précision de chaque modèle IA par format de question (boolean ou multiple).
-- Dérivé du modèle intermédiaire int_accuracy.

with source as (

    select * from {{ ref('int_accuracy') }}

),

aggregated as (

    select
        model_name,
        question_type,
        sum(total_questions)::bigint                        as total_questions,
        sum(correct_answers)::bigint                        as correct_answers,
        round(
            100.0 * sum(correct_answers) / sum(total_questions),
            2
        )                                                   as accuracy_pct

    from source
    group by model_name, question_type

)

select *
from aggregated
order by model_name, question_type
