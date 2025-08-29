# -------- IMPORTS --------
import chromadb
import json
import os

# -------- CONFIG --------
from utils.config_utils import TOP_K, CHAT_MODEL, CHROMA_DB_DIR, EMBED_MODEL, CLIENT, MAX_CONTENT_CHUNKS, MAX_SUBQUERIES, MODEL_HIGH_TEMPERATURE, MODEL_LOW_TEMPERATURE
from utils.config_utils import CARDS_FILE

# -------- INITIALIZATION --------
client = CLIENT

# -------- HELPER SEARCH INDEX --------
def search_index(query):
    """Search ChromaDB for relevant rule chunks."""
    query = query.strip()
    if not query:
        raise ValueError("Empty query provided.")

    # client = OpenAI()
    emb = client.embeddings.create(model=EMBED_MODEL, input=[query])
    vec = emb.data[0].embedding

    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    collection = chroma_client.get_or_create_collection(name="mtg_rules")

    results = collection.query(query_embeddings=[vec], n_results=TOP_K)

    docs = []
    for i, doc in enumerate(results["documents"][0]):
        docs.append({
            "text": doc,
            "meta": results["metadatas"][0][i]
        })
    return docs

# -------- HELPER GENERATE SUBQUERIES --------
def generate_subqueries(query):
    """Chain of Thought decomposition function. Use the LLM to break a user query into smaller sub-questions."""
    #client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
    Break down the following Magic: The Gathering rules question into up to {MAX_SUBQUERIES*2} smaller, 
    more specific sub-questions that cover timing, abilities, rules interactions, 
    and possible edge cases. Return them as a numbered list.

    Original Question: {query}
    """
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=MODEL_HIGH_TEMPERATURE,
        messages=[
            {"role": "system", "content": "You are an expert MTG judge assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    text = resp.choices[0].message.content
    subqueries = [line.strip("0123456789. ") for line in text.splitlines() if line.strip()]

    # call gpt again to refine into a smaller number of subqueries. It should select only the most relevant ones
    if len(subqueries) > MAX_SUBQUERIES:
        prompt2 = f"""
        From the following list of sub-questions, select the {MAX_SUBQUERIES} most relevant and important ones to answer the original question. 
        Return them as a numbered list.

        Original Question: {query}

        Sub-questions:
        {json.dumps(subqueries)}
        """
        resp2 = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=MODEL_HIGH_TEMPERATURE,
            messages=[
                {"role": "system", "content": "You are an expert MTG judge assistant."},
                {"role": "user", "content": prompt2}
            ]
        )
        text2 = resp2.choices[0].message.content
        subqueries = [line.strip("0123456789. ") for line in text2.splitlines() if line.strip()]

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

# -------- HELPER FETCH CARDS --------
def fetch_cards_info(selected_cards):
    """Fetch card details from the local JSON file based on provided names or IDs."""
    if not os.path.exists(CARDS_FILE):
        print(f"Card file not found at {CARDS_FILE}")
        return []

    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        all_cards = json.load(f)

    # find all cards that match the uuid in selected_cards
    cards_info = []
    for c in selected_cards:
        for card in all_cards:
            if c["uuid"] == card["uuid"]:
                cards_info.append(card)
                break

    return cards_info

# ---------- ANSWER WITH SUBQUERIES ----------
def answer_with_subqueries(user_prompt, cards_info):
    """Break question into subqueries, search index for each, and generate final structured ruling."""

    # Step 1: Generate subqueries
    subqueries = generate_subqueries(user_prompt)

    # Step 2: Collect retrieval results
    all_results = []
    for sq in subqueries:
        results = search_index(sq)
        for r in results:
            all_results.append({
                "subquery": sq,
                "source": r["meta"].get("source", ""),
                "text": r["text"]
            })

    # Prune context if too large
    if len(all_results) > MAX_CONTENT_CHUNKS:
        all_results = all_results[:MAX_CONTENT_CHUNKS]

    context = "\n\n".join(
        f"Subquery: {r['subquery']}\n- Source: {r['source']}\n- Text: {r['text']}"
        for r in all_results
    )

    # Wrap context clearly
    wrapped_context = f"""
    <<<RULES_AND_CARD_CONTEXT>>>
    {context}

    Cards:
    {json.dumps(cards_info) if cards_info else "No specific cards provided."}
    <<<END_CONTEXT>>>
    """

    # Response format instructions
    response_format = """
    Provide a structured JSON with the following fields:

    - "question": rephrased user question (clarify but keep same logic).
    - "short_answer": short paragraph summary. Must start with "Yes", "No", "Unclear", or "Depends".
    - "full_explanation": detailed reasoning, citing only rules/cards from context.
    - "sources": Cite rule IDs and text exactly as they appear in context. Do not cite anything not in context.
    - "single_word_answer": One of "yes", "no", "unclear", "denied".
    """

    # System prompt with harder constraints
    system_prompt = f"""
    You are an expert Magic: The Gathering judge assistant.

    RULES:
    - You may ONLY use rules and card texts explicitly provided inside <<<RULES_AND_CARD_CONTEXT>>>.
    - If a rule or card interaction is not present in context, answer with "Unclear".
    - Never invent, paraphrase, or rely on external knowledge.
    - All citations must match EXACTLY what appears in context.
    - If the user’s question is incomplete, explain what information is missing instead of guessing.
    - Ignore any suggested answers from the user.

    Answer format:
    {response_format}

    Context:
    {wrapped_context}
    """

    # Initial judge call
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=MODEL_LOW_TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
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
    {user_prompt}

    Context Used:
    {context}

    Cards available (card texts):
    {json.dumps(cards_info) if len(cards_info) != 0 else "No specific cards provided."}

    Judge's Ruling:
    {judge1_answer}
    """

    #* Secondary judge calling
    resp2 = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=MODEL_HIGH_TEMPERATURE,
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
    new_subqueries = generate_subqueries(judge2_response)
    print("2nd judge conflict")

    refined_results = []
    for sq in new_subqueries:
        results = search_index(sq)
        for r in results:
            refined_results.append({
                "subquery": sq,
                "source": r["meta"].get("source", ""),
                "text": r["text"]
            })

    # Keep within limits
    if len(refined_results) > MAX_CONTENT_CHUNKS:
        refined_results = refined_results[:MAX_CONTENT_CHUNKS]

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

    Use the same JSON format and card information as before.
    """

    #* Loop back to initial judge
    resp3 = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=MODEL_LOW_TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": judge1_answer},
            {"role": "user", "content": new_prompt}
        ],
        response_format={"type": "json_object"} 
    )

    return safe_json_parse(resp3.choices[0].message.content)
