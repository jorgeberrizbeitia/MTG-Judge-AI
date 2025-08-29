# -------- IMPORTS --------
import os
import re
import json
import chromadb

# -------- CONFIG --------
from utils.config_utils import CHUNK_SIZE, CHROMA_DB_DIR, RULES_FILE, EMBED_MODEL, CLIENT, CHUNK_OVERLAP, INDEX_BATCH_SIZE

# -------- INITIALIZATION --------
os.makedirs(CHROMA_DB_DIR, exist_ok=True) # to create folder if it doesn't exist
client = CLIENT

# -------- HELPER LOAD RULES --------
def load_rules(path):
    """Load the MTG comprehensive rules from a text file into rule entries."""
    if not os.path.exists(path):
        print(f"Rules file not found at {path}")
        return []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # Matches "603.1a Rule text possibly spanning multiple lines"
    pattern = re.compile(r"^(\d{1,3}(?:\.\d+)*[a-z]?)\s+(.*?)(?=\n\d{1,3}(?:\.\d+)*[a-z]?\s|\Z)", re.S | re.M)
    
    docs = []
    for match in pattern.finditer(text):
        rule_id, body = match.groups()
        body = body.strip().replace("\n", " ")
        docs.append({
            "id": f"CR:{rule_id}",
            "text": f"{rule_id} {body}",
            "rule_id": rule_id,
            "source": "Comprehensive Rules"
        })
    return docs

# -------- HELPER CHUNK TEXT --------
def chunk_text(text):
    """
    Split text into overlapping chunks for embedding. text (str)
    
    Args:
        text (str): The input text to chunk.
        chunk_size (int): Approximate max words per chunk.
        overlap (int): Words to overlap between chunks.

    Returns:
        list[str]: A list of text chunks.
    """

    # Split by sentence endings while keeping coherence
    sentences = re.split(r'(?<=[.!?]) +', text)

    chunks = []
    current = []
    length = 0

    for s in sentences:
        tokens = s.split()
        token_len = len(tokens)

        # If adding this sentence exceeds chunk size
        if length + token_len > CHUNK_SIZE:
            # Save current chunk
            chunks.append(" ".join(current))

            # Start new chunk with overlap from the previous
            overlap_tokens = current[-CHUNK_OVERLAP:] if CHUNK_OVERLAP > 0 else []
            current = overlap_tokens + tokens
            length = len(current)
        else:
            current.extend(tokens)
            length += token_len

    # Add last chunk if non-empty
    if current:
        chunks.append(" ".join(current))

    return chunks

# -------- HELPER BUILD INDEX --------
def build_index():
    """Create ChromaDB collection from rules with batching and optimized metadata."""
    print("Loading rules...")
    
    rules = load_rules(RULES_FILE)
    print(f"Loaded {len(rules)} rules")

    all_docs = rules  # cards now handled separately

    texts, metas, ids = [], [], []

    print("Chunking rules...")
    for d in all_docs:
        chunks = chunk_text(d["text"])
        for i, ch in enumerate(chunks):
            texts.append(ch)
            metas.append({
                "id": d["id"],
                "rule_id": d.get("rule_id", None),
                "source": d.get("source", "Comprehensive Rules")
            })
            ids.append(f"{d['id']}_{i}")

    if not texts:
        raise ValueError("No valid chunks found to embed.")

    print(f"Total chunks: {len(texts)}")

    # Initialize Chroma client
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

    # Drop old collection (safe)
    try:
        chroma_client.delete_collection("mtg_data")
        print("Old collection deleted.")
    except Exception:
        print("No old collection to delete.")

    collection = chroma_client.get_or_create_collection(name="mtg_data")

    # Batch embeddings
    print("Creating embeddings in batches...")
    for i in range(0, len(texts), INDEX_BATCH_SIZE):
        batch_texts = texts[i:i + INDEX_BATCH_SIZE]
        batch_ids = ids[i:i + INDEX_BATCH_SIZE]
        batch_metas = metas[i:i + INDEX_BATCH_SIZE]

        embeddings = client.embeddings.create(
            model=EMBED_MODEL,
            input=batch_texts
        )
        vecs = [d.embedding for d in embeddings.data]

        collection.add(
            ids=batch_ids,
            embeddings=vecs,
            documents=batch_texts,
            metadatas=batch_metas
        )

        print(f"Indexed {i + len(batch_texts)}/{len(texts)} chunks")

    print("Index built and saved with ChromaDB!")
