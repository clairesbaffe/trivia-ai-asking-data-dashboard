
  
  create view "gold"."main"."mart_response_time_by_correctness__dbt_tmp" as (
    -- mart_response_time_by_correctness.sql
--
-- Temps de réponse moyen par modèle selon l'issue de la réponse (bonne ou mauvaise réponse).
-- Dérivé de int_response_time.

with source as (

    select * from "gold"."main"."int_response_time"

),

aggregated as (

    select
        model_name,
        answer_result,
        count(*)::bigint                                    as total_questions,
        round(avg(response_time), 3)                        as avg_response_time,
        round(median(response_time), 3)                     as median_response_time

    from source
    group by model_name, answer_result

)

select *
from aggregated
order by model_name, answer_result
  );
