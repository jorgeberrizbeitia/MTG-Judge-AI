import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# GENERAL VARIABLES
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLIENT = OpenAI(api_key=OPENAI_API_KEY)

# DIST VARIABLES
RULES_FILE = "./data/comprehensive-rules.txt"
# CARDS_FILE = "./data/clean-standard-cards.json"
CARDS_FILE = "./data/clean-all-printings.json"

# EMBEDINGS MODEL VARIABLES
EMBED_MODEL = "text-embedding-3-large" # OpenAI’s most accurate embedding model.
CHROMA_DB_DIR = os.path.join(os.getcwd(), "chroma_db")
INDEX_BATCH_SIZE = 100 # how many chunks to embed in each batch. lower means less RAM (API tokens) usage but more time. higher means more RAM (API tokens) usage but less time.
CHUNK_SIZE = 500 # approximate max number of words per chunk. Smaller chunks means more chunks to embed (bigger DB size), but more precise matching. Larger chunks means less chunks to embed (smaller DB size), but less precise matching.
CHUNK_OVERLAP = 100  # The number of words carried over from the end of one chunk into the next (to prevent cutting important context).
MAX_CONTENT_CHUNKS = 25 # total content chunks to use for final answer

# QUESTION MODEL VARIABLES
CHAT_MODEL = "gpt-4o-mini"
MAX_SUBQUERIES = 5 # amount of subqueries to break down the initial query. From an initial amount of MAX_SUBQUERIES*2 into MAX_SUBQUERIES.
TOP_K = 8 # X most relevant rule chunks that are semantically closest to my query.
MODEL_HIGH_TEMPERATURE = 0.3 # for the subqueries steps and judge ruling validation reasoning.
MODEL_LOW_TEMPERATURE = 0 # for judge and context analysis. Initial and final answer.

