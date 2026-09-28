import lmstudio as lms
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
import os
import time
from rich.progress import Progress

OUTPUT_FOLDER = "./silver"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
WRITE_OPTS = dict(compression="zstd", compression_level=1)

QUESTIONS_NUMBER = 5298

model_name = "ibm/granite-3.2-8b"

model = lms.llm(model_name, config={
            "gpu": {
                "ratio": "max"
            }
        })
df = pd.read_parquet('silver/questions.parquet')

progress = Progress()
progress.start()

task = progress.add_task(f'Asking AI model {model_name}...', total=QUESTIONS_NUMBER)

for i in range(QUESTIONS_NUMBER):
  answers = np.array([
    df.loc[i].correct_answer, 
    df.loc[i].incorrect_answer_1
  ])

  is_multiple_choice_answer = df.loc[i].type == "multiple"

  if(is_multiple_choice_answer):
    answers = np.append(answers, [
      df.loc[i].incorrect_answer_2, 
      df.loc[i].incorrect_answer_3
    ])

  np.random.shuffle(answers)

  prompt_propositions = f'1 - {answers[0]}\n2 - {answers[1]}\n'
  if(is_multiple_choice_answer):
    prompt_propositions += f'3 - {answers[2]}\n4 - {answers[3]}\n'

  prompt = f'Please answer to the following question : {df.loc[i].question} by choosing between the following propositions : \n{prompt_propositions}Answer only with the number of the proposition you think is the right answer, nothing else.'

  # print(prompt, "\n")

  start = time.time()
  result = model.respond(prompt)
  end = time.time()

  progress.update(task, advance=1)

  if(result.content.strip() not in ["1", "2", "3", "4"]):
    print(f'AI result is not valid, skipping question : "{result.content.strip()}"')
    continue

  ai_answer = answers[int(result.content) - 1]
  ai_correct = ai_answer == df.loc[i].correct_answer
  response_time = round(end - start, 3)

  # print(ai_answer, ai_correct, response_time)
  # print(result, ai_answer, ai_correct, "\n\n")

  # print(i+1, df.loc[i].question, ai_correct, response_time)

  df.at[i, 'ai_answer'] = ai_answer
  df.at[i, 'ai_correct'] = ai_correct
  df.at[i, 'response_time'] = response_time

progress.stop()

print("AI is done answering, saving data...")

# print(df)

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

table = pa.Table.from_pandas(df, schema=schema)
safe_model_name = model_name.replace("/", "--")
pq.write_table(table, os.path.join(OUTPUT_FOLDER, f"questions-{safe_model_name}.parquet"), **WRITE_OPTS,) 
