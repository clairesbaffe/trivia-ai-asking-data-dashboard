import os
import time
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from dotenv import load_dotenv
import csv

load_dotenv()

OUTPUT_FOLDER = "./silver"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

WRITE_OPTS = dict(compression="zstd", compression_level=1)

def process_csv():
    try:
        questions = []
        with open(f'questions_raw.csv', "r", encoding="utf-8") as file_obj:
            questions_csv = csv.reader(file_obj)
            for row in questions_csv:
                if " | " in row[-1]:
                    wrong_answers = row[-1].split(" | ")
                    del row[-1]
                    row.append(wrong_answers[0])
                    row.append(wrong_answers[1])
                    row.append(wrong_answers[2])
                else:
                    row.append(None)
                    row.append(None)
                questions.append(row)
            questions.pop(0)

        categories = []
        types = []
        difficulties = []
        str_questions = []
        correct_answers = []
        incorrect_answers_1 = []
        incorrect_answers_2 = []
        incorrect_answers_3 = []

        ai_answers = []
        ai_corrects = []
        response_times = []

        for q in questions:
            categories.append(q[0])
            types.append(q[1])
            difficulties.append(q[2])
            str_questions.append(q[3])
            correct_answers.append(q[4])
            incorrect_answers_1.append(q[5])
            incorrect_answers_2.append(q[6])
            incorrect_answers_3.append(q[7])
            ai_answers.append(None)
            ai_corrects.append(None)
            response_times.append(None)


        schema = pa.schema([ 
            pa.field("category", pa.string()),
            pa.field("type", pa.string()),
            pa.field("difficulty", pa.string()),
            pa.field("question", pa.string()),
            pa.field("correct_answer", pa.string()),
            pa.field("incorrect_answer_1", pa.string()),
            pa.field("incorrect_answer_2", pa.string(), nullable=True),
            pa.field("incorrect_answer_3", pa.string(), nullable=True),
            pa.field("ai_answer", pa.string(), nullable=True),
            pa.field("ai_correct", pa.bool_(), nullable=True),
            pa.field("response_time", pa.float16(), nullable=True),
        ]) 

        batch = pa.record_batch([ 
            pa.array(categories),
            pa.array(types),
            pa.array(difficulties),
            pa.array(str_questions),
            pa.array(correct_answers),
            pa.array(incorrect_answers_1),
            pa.array(incorrect_answers_2),
            pa.array(incorrect_answers_3),
            pa.array(ai_answers),
            pa.array(ai_corrects),
            pa.array(response_times),
        ], schema=schema)

        table = pa.Table.from_batches([batch], schema=schema) 
        pq.write_table(table, os.path.join(OUTPUT_FOLDER, f"questions.parquet"), **WRITE_OPTS,) 

    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    # num_workers = max(cpu_count() // 2, 1)
    num_workers = max(cpu_count() -1 , 1)

    print(f"Utilisation de {num_workers} processus...")
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_csv)}
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Questions en traitement"):
            pass
    print(f"Termine en {time.perf_counter() - start:.2f}s")
