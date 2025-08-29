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
CHROMA_DB_DIR = "./chroma_db"
INDEX_BATCH_SIZE = 100
CHUNK_SIZE = 700 # words approximation
MAX_CONTENT_CHUNKS = 20
CHUNK_OVERLAP = 100

# QUESTION MODEL VARIABLES
CHAT_MODEL = "gpt-4o-mini"
MAX_SUBQUERIES = 5
TOP_K = 6
MODEL_HIGH_TEMPERATURE = 0.3 # for the subqueries steps and judge ruling validation reasoning.
MODEL_LOW_TEMPERATURE = 0 # for judge and context analysis. Initial and final answer.

