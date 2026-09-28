
  
  create view "gold"."main"."mart_accuracy_by_category__dbt_tmp" as (
    -- mart_accuracy_by_category.sql
--
-- Précision de chaque modèle IA par catégorie thématique.
-- Dérivé du modèle intermédiaire int_accuracy.

with source as (

    select * from "gold"."main"."int_accuracy"

),

aggregated as (

    select
        model_name,
        category,
        sum(total_questions)::bigint                        as total_questions,
        sum(correct_answers)::bigint                        as correct_answers,
        round(
            100.0 * sum(correct_answers) / sum(total_questions),
            2
        )                                                   as accuracy_pct

    from source
    group by model_name, category

)

select *
from aggregated
order by category, model_name
  );
