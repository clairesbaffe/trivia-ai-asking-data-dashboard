import csv
import html
import time
import requests

BASE_URL = "https://opentdb.com/api.php"
TOKEN_URL = "https://opentdb.com/api_token.php?command=request"
BATCH_SIZE = 50
TARGET_TOTAL = 5298
OUTPUT_FILE = "opentdb_questions.csv"


def get_session_token(session: requests.Session) -> str:
    """Recupère un token de session pour eviter les doublons."""
    resp = session.get(TOKEN_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("response_code") == 0:
        return data["token"]
    raise RuntimeError(f"Impossible d'obtenir un token: {data}")


def clean_text(raw_text: str) -> str:
    """Decode les entites HTML (ex: &quot; -> \")."""
    return html.unescape(raw_text) if raw_text else ""


def main():
    session = requests.Session()
    token = get_session_token(session)

    fieldnames = [
        "category",
        "type",
        "difficulty",
        "question",
        "correct_answer",
        "incorrect_answers",
    ]

    total_saved = 0

    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        while total_saved < TARGET_TOTAL:
            amount = min(BATCH_SIZE, TARGET_TOTAL - total_saved)
            params = {
                "amount": amount,
                "token": token,
            }

            try:
                resp = session.get(BASE_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as err:
                print(f"Erreur reseau : {err}. Nouvelle tentative dans 5s...")
                time.sleep(5)
                continue

            code = data.get("response_code")

            # 0 = Succès
            if code == 0:
                results = data.get("results", [])
                for item in results:
                    writer.writerow(
                        {
                            "category": clean_text(item.get("category")),
                            "type": item.get("type"),
                            "difficulty": item.get("difficulty"),
                            "question": clean_text(item.get("question")),
                            "correct_answer": clean_text(item.get("correct_answer")),
                            # Liste convertie en chaîne separee par des pipes
                            "incorrect_answers": " | ".join(
                                clean_text(ans)
                                for ans in item.get("incorrect_answers", [])
                            ),
                        }
                    )
                total_saved += len(results)
                print(f"Progression : {total_saved}/{TARGET_TOTAL}")

            # 4 = La base a epuise les questions uniques associees au token
            elif code == 4:
                print("Toutes les questions uniques de la base ont ete extraites.")
                break

            # 5 = Rate limit depasse (trop de requetes par seconde)
            elif code == 5:
                print("Limite de debit atteinte, pause prolongee...")
                time.sleep(10)
                continue

            else:
                print(f"Code API inattendu : {code}. Arret.")
                break

            # Respect du rate-limit strict d'OpenTDB (1 requete / 5s recommandee)
            time.sleep(5)

    print(f"Termine : {total_saved} questions enregistrees dans {OUTPUT_FILE}")


if __name__ == "__main__":
    main()