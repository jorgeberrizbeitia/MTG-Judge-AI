# -------- IMPORTS --------
import os
import re
import json
import chromadb

# -------- CONFIG --------
from utils.config_utils import CHUNK_SIZE, CHROMA_DB_DIR, RULES_FILE, CARDS_FILE, EMBED_MODEL, CLIENT

# -------- INITIALIZATION --------
os.makedirs(CHROMA_DB_DIR, exist_ok=True) # to create folder if it doesn't exist
client = CLIENT

# -------- HELPER LOAD RULES --------
def load_rules(path):
    """Load the MTG comprehensive rules from a text file."""
    if not os.path.exists(path):
        print(f"Rules file not found at {path}")
        return []

    docs = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Rules usually like: 603.1. Some text
            match = re.match(r"^(\d{1,3}(?:\.\d+)+)\s+(.*)$", line)
            if match:
                rule_id, body = match.groups()
                docs.append({
                    "id": f"CR:{rule_id}",
                    "text": f"{rule_id} {body}",
                    "rule_id": rule_id,
                    "source": "Comprehensive Rules"
                })
    return docs

# -------- HELPER LOAD CARDS -------- #! removed loading cards as they will be fetch from an id
def load_cards(path):
    """Load MTG card data from your JSON export."""
    if not os.path.exists(path):
        print(f"Card file not found at {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        cards = json.load(f)

    docs = []
    for c in cards:
        # Skip cards without names or text
        if "name" not in c or not c.get("originalText"):
            continue

        # Construct a searchable text block for embedding
        text_parts = [
            f"Name: {c['name']}",
            f"Mana Cost: {c.get('manaCost', '')}",
            f"Types: {' '.join(c.get('types', []))}",
            f"Subtypes: {' '.join(c.get('subtypes', []))}",
            f"Abilities/Keywords: {', '.join(c.get('keywords', []))}",
            f"Text: {c['originalText']}"
        ]

        # Add rulings (big chunk but useful)
        rulings = c.get("rulings", [])
        if rulings:
            rulings_text = " | ".join(r["text"] for r in rulings if "text" in r)
            text_parts.append(f"Rulings: {rulings_text}")

        full_text = "\n".join(text_parts)

        docs.append({
            "id": f"CARD:{c['uuid']}",   # use UUID for uniqueness
            "text": full_text,
            "source": "Card Database",
            "card_name": c["name"],
            "manaCost": c.get("manaCost", ""),
            "types": ", ".join(c.get("types", [])),       # FIXED: stringify list
            "subtypes": ", ".join(c.get("subtypes", [])), # FIXED: stringify list
            "keywords": ", ".join(c.get("keywords", [])), # FIXED: stringify list
            "rarity": c.get("rarity", "")
        })

    print(f"Loaded {len(docs)} cards from {path}")
    return docs

# -------- HELPER CHUNK TEXT --------
def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Split text into smaller chunks so embeddings don't get too big."""
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current = []
    length = 0

    for s in sentences:
        tokens = len(s.split())
        if length + tokens > chunk_size:
            chunks.append(" ".join(current))
            current = [s]
            length = tokens
        else:
            current.append(s)
            length += tokens
    if current:
        chunks.append(" ".join(current))

    return chunks

# -------- HELPER BUILD INDEX --------
def build_index():
    """Create ChromaDB collection from rules + card data."""
    # client = OpenAI(api_key=OPENAI_API_KEY)

    print("Loading rules...")
    rules = load_rules(RULES_FILE)

    #! removed loading cards as they will be fetch from an id
    # print("Loading cards...")
    # cards = load_cards(CARDS_FILE)  # add this

    # all_docs = rules + cards  # merge datasets #! removed loading cards as they will be fetch from an id
    all_docs = rules  # merge datasets

    texts, metas, ids = [], [], []

    for d in all_docs:
        chunks = chunk_text(d["text"])
        for i, ch in enumerate(chunks):
            texts.append(ch)
            metas.append(d)
            ids.append(f"{d['id']}_{i}")

    if not texts:
        raise ValueError("No valid chunks found to embed.")

    print(f"Total chunks: {len(texts)}")

    # Create embeddings
    embeddings = client.embeddings.create(model=EMBED_MODEL, input=texts)
    vecs = [d.embedding for d in embeddings.data]

    # Initialize Chroma client
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

    # Drop old collection (clean rebuild)
    try:
        chroma_client.delete_collection("mtg_data")
    except:
        pass

    collection = chroma_client.get_or_create_collection(name="mtg_data")

    # Add to Chroma
    collection.add(
        ids=ids,
        embeddings=vecs,
        documents=texts,
        metadatas=metas
    )

    print("Index built and saved with ChromaDB!")


