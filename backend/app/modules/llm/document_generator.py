from app.modules.llm.llm_client import LLMClient
from app.modules.rag.vector_store import load_vector_store

def generate_compliance_narrative(document_type, ai_system, risk_assessment, company_name, user_id: int | None = None):
    """
    Generates a professional compliance narrative using LLM + RAG.
    """
    # 1. Build the search query based on system context
    query = f"EU AI Act requirements for {document_type.value} regarding an AI system used for {ai_system.use_case} in the {ai_system.sector} sector."
    
    # 2. Retrieve context using RAG
    try:
        vector_store = load_vector_store(user_id=user_id)
        docs = vector_store.similarity_search(query, k=5)
        rag_context = "\n\n".join([doc.page_content for doc in docs])
    except FileNotFoundError:
        # Fallback if the vector store hasn't been initialized yet
        rag_context = "No specific regulation context available in the vector store."
    
    # 3. Build the prompt
    system_prompt = (
        "You are an expert legal compliance officer specializing in the EU AI Act. "
        "Write a formal, comprehensive, and professional narrative compliance document. "
        "Do NOT output a simple filled-in template or form. The output should read like "
        "a professional legal assessment grounded in the actual regulation text."
    )
    
    risk_assessment_details = "None available"
    if risk_assessment:
        risk_level = risk_assessment.risk_level.value if hasattr(risk_assessment.risk_level, 'value') else str(risk_assessment.risk_level)
        risk_assessment_details = f"Assessed Risk Level: {risk_level}\nFindings: {risk_assessment.findings}\nRecommendations: {risk_assessment.recommendations}"

    prompt = f"""
    Please write a {document_type.value} report for the following AI system.
    
    === SYSTEM CONTEXT ===
    - Name: {ai_system.name}
    - Company: {company_name or "Not Specified"}
    - Version: {ai_system.version or "1.0"}
    - Use Case: {ai_system.use_case or "Not Specified"}
    - Sector: {ai_system.sector or "Not Specified"}
    - Declared Risk Level: {ai_system.risk_level.value if ai_system.risk_level else "Not assessed"}
    - Description: {ai_system.description or "No description provided"}
    
    === RISK ASSESSMENT DETAILS ===
    {risk_assessment_details}
    
    === RELEVANT EU AI ACT REGULATION (RAG CONTEXT) ===
    {rag_context}
    
    Ensure the document is structured logically with headings, bullet points where appropriate, and a concluding statement.
    """
    
    # 4. Call the LLM
    client = LLMClient()
    final_document = client.call(prompt=prompt, system_prompt=system_prompt, max_tokens=2500, response_format={"type": "text"})
    
    return final_document