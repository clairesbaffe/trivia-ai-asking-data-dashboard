-- mart_response_time_by_question_length.sql
--
-- Temps de réponse moyen par modèle et par niveau de longueur/complexité de la question.
-- Temps de réponse moyen par modèle et par palier de longueur totale (énoncé + choix de réponses).
-- Dérivé de int_response_time.

with source as (

    select * from "gold"."main"."int_response_time"

),

aggregated as (

    select
        model_name,
        question_length_tier,
        count(*)::bigint                                    as total_questions,
        round(avg(total_prompt_char_length), 1)             as avg_prompt_length,
        round(avg(response_time), 3)                        as avg_response_time,
        round(median(response_time), 3)                     as median_response_time

    from source
    group by model_name, question_length_tier

)

select *
from aggregated
order by model_name, question_length_tier