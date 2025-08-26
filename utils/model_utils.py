# -------- IMPORTS --------
import chromadb
import json

# -------- CONFIG --------
from utils.config_utils import TOP_K, CHAT_MODEL, CHROMA_DB_DIR, EMBED_MODEL, CLIENT

# -------- INITIALIZATION --------
client = CLIENT

# -------- HELPER SEARCH INDEX --------
def search_index(query, top_k=TOP_K):
    """Search ChromaDB for relevant rule chunks."""
    query = query.strip()
    if not query:
        raise ValueError("Empty query provided.")

    # client = OpenAI()
    emb = client.embeddings.create(model=EMBED_MODEL, input=[query])
    vec = emb.data[0].embedding

    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    collection = chroma_client.get_or_create_collection(name="mtg_rules")

    results = collection.query(query_embeddings=[vec], n_results=top_k)

    docs = []
    for i, doc in enumerate(results["documents"][0]):
        docs.append({
            "text": doc,
            "meta": results["metadatas"][0][i]
        })
    return docs

# -------- HELPER GENERATE SUBQUERIES --------
def generate_subqueries(query, n=10):
    """Chain of Thought decomposition function. Use the LLM to break a user query into smaller sub-questions."""
    #client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
    Break down the following Magic: The Gathering rules question into {n} smaller, 
    more specific sub-questions that cover timing, abilities, rules interactions, 
    and possible edge cases. Return them as a numbered list.

    Original Question: {query}
    """
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You are an expert MTG judge assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    text = resp.choices[0].message.content
    subqueries = [line.strip("0123456789. ") for line in text.splitlines() if line.strip()]
    return subqueries

# -------- HELPER JSON PARSE --------
def safe_json_parse(text):
    """Function to safely parse from string to json, even if wrapped in markdown fences. Converts response from gpt to json"""
    fixed = text.strip()

    # Strip markdown fences if present
    if fixed.startswith("```"):
        # Remove the first line (``` or ```json)
        fixed = "\n".join(fixed.split("\n")[1:])
        # Remove trailing fence
        if fixed.strip().endswith("```"):
            fixed = "\n".join(fixed.strip().split("\n")[:-1])

    # Try JSON decode
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON", "raw": text}

# ---------- ANSWER WITH SUBQUERIES ----------
def answer_with_subqueries(query, max_context_chunks=20, max_subqueries=20):
    """Break question into subqueries, search index for each, and generate final structured ruling."""

    # Step 1: Generate subqueries
    subqueries = generate_subqueries(query, n=max_subqueries)

    # Step 2: Collect retrieval results
    all_results = []
    for sq in subqueries:
        results = search_index(sq, top_k=8)
        for r in results:
            all_results.append({
                "subquery": sq,
                "source": r["meta"].get("source", ""),
                "text": r["text"]
            })

    # Prune context if too large (keep only top N chunks by length relevance)
    if len(all_results) > max_context_chunks:
        all_results = all_results[:max_context_chunks]

    context = "\n\n".join(
        f"Subquery: {r['subquery']}\n- Source: {r['source']}\n- Text: {r['text']}"
        for r in all_results
    )

    # Response format instructions
    response_format = """
    Provide a structured JSON with the following fields:

    - "question": rephrased user question for clarity,
    - "single_word_answer": "Yes", "No" or "Unclear",
    - "short_answer": short paragraph summary of the answer, starting with a "Yes" or No" if it applies to the question,
    - "full_explanation": detailed reasoning of the answer with rules and card interactions,
    - "sources": cite the rules used for the decision. Also include any card text that was used for the decision.
    """

    # System + user prompt for judge #1
    system_prompt = f"""
    You are an expert Magic: The Gathering judge assistant.
    You will receive a question from a user and need to answer it as best and accurate as possible, using the provided context.
    Consider that the user might be vague with the question and you might need to rephrase the question if possible.
    If the question doesn't entirely make sense or if you do not have enough information to properly answer it, you can indicate it in your answer.
    
    Sources available (rules + card texts):
    {context}

    Answer format:
    {response_format}
    """

    #* Initial judge calling
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        response_format={"type": "json_object"} 
    )

    judge1_answer = resp.choices[0].message.content

    # ---------- SECONDARY JUDGE ----------
    judge2_system_prompt = f"""
    You are an expert MTG high judge reviewing another judge’s ruling.

    You will be given:
    - User's question
    - Judge’s ruling
    - The context they used

    If you agree: reply only with "Accepted".
    If you disagree: reply with "Denied, [reason + extra context suggestions]".
    """

    judge_prompt = f"""
    User Question:
    {query}

    Context Used:
    {context}

    Judge's Ruling:
    {judge1_answer}
    """

    #* Secondary judge calling
    resp2 = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": judge2_system_prompt},
            {"role": "user", "content": judge_prompt}
        ]
    )

    judge2_response = resp2.choices[0].message.content.strip()

    # ---------- ACCEPTED CASE ----------
    if judge2_response.startswith("Accepted"):
        return safe_json_parse(judge1_answer)

    # ---------- DENIED CASE ----------
    # Generate refined subqueries based on judge2 feedback
    new_subqueries = generate_subqueries(judge2_response, n=max_subqueries)
    print("2nd judge conflict")

    refined_results = []
    for sq in new_subqueries:
        results = search_index(sq, top_k=5)
        for r in results:
            refined_results.append({
                "subquery": sq,
                "source": r["meta"].get("source", ""),
                "text": r["text"]
            })

    # Keep within limits
    if len(refined_results) > max_context_chunks:
        refined_results = refined_results[:max_context_chunks]

    refined_context = "\n\n".join(
        f"Subquery: {r['subquery']}\n- Source: {r['source']}\n- Text: {r['text']}"
        for r in refined_results
    )

    new_prompt = f"""
    A higher judge denied your ruling for lack of context. Use the new context and improve your ruling.

    Higher judge feedback:
    {judge2_response}

    New context:
    {refined_context}

    Use the same JSON format as before.
    """

    #* Loop back to initial judge
    resp3 = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": judge1_answer},
            {"role": "user", "content": new_prompt}
        ],
        response_format={"type": "json_object"} 
    )

    return safe_json_parse(resp3.choices[0].message.content)
