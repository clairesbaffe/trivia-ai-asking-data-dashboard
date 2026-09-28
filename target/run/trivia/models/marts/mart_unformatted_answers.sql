
  
  create view "gold"."main"."mart_unformatted_answers__dbt_tmp" as (
    -- mart_unformatted_answers.sql
--
-- Métriques sur les réponses non formatées (ai_answer IS NULL ou vide) par modèle IA.
-- Ces cas correspondent aux échecs de formatage/parsing où l'IA n'a pas respecté le gabarit attendu.
-- Elles sont comptabilisées comme des réponses fausses dans le calcul global de l'accuracy.
--
-- Dérivé du modèle intermédiaire int_accuracy.

with source as (

    select * from "gold"."main"."int_accuracy"

),

aggregated as (

    select
        model_name,
        sum(total_questions)::bigint                                        as total_questions,
        sum(total_questions - unformatted_answers)::bigint                  as formatted_answers,
        sum(unformatted_answers)::bigint                                    as unformatted_answers,
        round(
            100.0 * sum(unformatted_answers) / sum(total_questions),
            2
        )                                                                   as unformatted_pct,
        round(
            100.0 * sum(total_questions - unformatted_answers) / sum(total_questions),
            2
        )                                                                   as compliance_pct

    from source
    group by model_name

)

select *
from aggregated
order by unformatted_pct asc, model_name
  );
