from app.modules.llm.llm_client import LLMClient


def generate_report(metadata, risk, answers, retriever):
    # create LLM client inside function (safe)
    llm_client = LLMClient()

    # Step 1: build query
    query = f"{metadata} {risk} {answers}"

    # Step 2: use EXISTING FAISS retriever
    docs = retriever.get_relevant_documents(query)

    # Step 3: build context
    if not docs:
        context = "No relevant regulatory context found."
    else:
        context = "\n".join(doc.page_content for doc in docs)

    # Step 4: prompt
    prompt = f"""
    You are a compliance expert.

    System Metadata: {metadata}
    Risk Classification: {risk}
    Questionnaire Answers: {answers}

    Regulatory Context:
    {context}

    Generate a structured compliance report with:
    - Overview
    - Risk Analysis
    - Recommendations
    """

    # Step 5: use project LLM (NOT OpenAI directly)
    response = llm_client.call(prompt)

    return response

