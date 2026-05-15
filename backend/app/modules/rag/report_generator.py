from openai import OpenAI
import numpy as np

# init client
client = OpenAI()


def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding



def split_text(text, chunk_size=200):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)

    return chunks



def create_vector_store(text):
    chunks = split_text(text)

    store = []
    for chunk in chunks:
        emb = get_embedding(chunk)
        store.append({
            "text": chunk,
            "embedding": emb
        })

    return store



def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))



def retrieve_relevant(query, store, top_k=3):
    query_emb = get_embedding(query)

    scores = []
    for item in store:
        score = cosine_similarity(query_emb, item["embedding"])
        scores.append((score, item["text"]))

    scores.sort(reverse=True)

    return [text for _, text in scores[:top_k]]


def load_context():
    try:
        with open("regulations.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "General compliance regulations apply."


def generate_report(metadata, risk, answers, context=None):
    if context is None:
        context = load_context()

    store = create_vector_store(context)

    query = f"{metadata} {risk} {answers}"
    relevant_chunks = retrieve_relevant(query, store)

    final_context = "\n".join(relevant_chunks)

    prompt = f"""
    You are a compliance expert.

    System Metadata: {metadata}
    Risk Classification: {risk}
    Questionnaire Answers: {answers}

    Regulatory Context:
    {final_context}

    Write a professional compliance report with:
    - Overview
    - Risk Analysis
    - Recommendations
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content