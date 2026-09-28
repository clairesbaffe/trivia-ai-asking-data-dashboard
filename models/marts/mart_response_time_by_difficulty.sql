-- mart_response_time_by_difficulty.sql
--
-- Temps de réponse moyen par modèle et par palier de difficulté (easy, medium, hard).
-- Dérivé de int_response_time.

with source as (

    select * from {{ ref('int_response_time') }}

),

aggregated as (

    select
        model_name,
        difficulty,
        count(*)::bigint                                    as total_questions,
        round(avg(response_time), 3)                        as avg_response_time,
        round(median(response_time), 3)                     as median_response_time

    from source
    group by model_name, difficulty

)

select *
from aggregated
order by model_name, difficulty

