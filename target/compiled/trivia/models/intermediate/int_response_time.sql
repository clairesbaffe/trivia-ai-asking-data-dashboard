-- int_response_time.sql
--
-- Modèle intermédiaire préparant les données d'analyse de latence / temps de réponse.
-- Exclut les questions sans modèle ou sans temps de réponse valide, standardise les métriques
-- et enrichit chaque question avec la longueur totale (énoncé + choix de réponses) et l'issue de réponse.

with source as (

    select * from "gold"."main"."stg_questions"

    where model_name is not null
      and response_time is not null

),

calculated_length as (

    select
        *,
        -- Longueur totale du prompt : question + ensemble des réponses proposées
        (
            length(question)
            + coalesce(length(correct_answer), 0)
            + coalesce(length(incorrect_answer_1), 0)
            + coalesce(length(incorrect_answer_2), 0)
            + coalesce(length(incorrect_answer_3), 0)
        )::integer as total_prompt_char_length,

        length(question)::integer as question_char_length

    from source

),

enriched as (

    select
        model_name,
        category,
        difficulty,
        type                                                                as question_type,
        response_time,
        question_char_length,
        total_prompt_char_length,
        -- Paliers de longueur totale recalibrés (Q25 ~ 80, Médiane ~ 100, Q75 ~ 130)
        case
            when total_prompt_char_length < 80 then 'Courte (< 80 car.)'
            when total_prompt_char_length <= 130 then 'Moyenne (80-130 car.)'
            else 'Longue (> 130 car.)'
        end                                                                 as question_length_tier,
        case
            when ai_correct = true then 'Bonne réponse'
            else 'Mauvaise réponse'
        end                                                                 as answer_result,
        ai_correct,
        ai_answer is null or trim(ai_answer) = ''                           as is_unformatted

    from calculated_length

)

select *
from enriched