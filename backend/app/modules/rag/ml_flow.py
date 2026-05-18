import mlflow


def log_query(question: str, answer: str, sources: list):
    with mlflow.start_run():
        mlflow.log_param("question", question)
        mlflow.log_metric("source_count", len(sources))
        mlflow.log_text(answer, "answer.txt")
