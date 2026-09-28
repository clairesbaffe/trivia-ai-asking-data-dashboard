-- mart_response_time_by_model.sql
--
-- Temps de réponse moyen et statistiques de latence par modèle IA.
-- Dérivé de int_response_time.

with source as (

    select * from "gold"."main"."int_response_time"

),

aggregated as (

    select
        model_name,
        count(*)::bigint                                    as total_questions,
        round(avg(response_time), 3)                        as avg_response_time,
        round(median(response_time), 3)                     as median_response_time,
        round(min(response_time), 3)                        as min_response_time,
        round(max(response_time), 3)                        as max_response_time

    from source
    group by model_name

)

select *
from aggregated
order by avg_response_time asc