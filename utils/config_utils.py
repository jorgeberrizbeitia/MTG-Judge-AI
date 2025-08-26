import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHUNK_SIZE = 700 # words approximation
CHROMA_DB_DIR = "./chroma_db"
RULES_FILE = "./data/comprehensive-rules.txt"
CARDS_FILE = "./data/clean-standard-cards.json"
# CARDS_FILE = "./data/clean-all-printings.json"
EMBED_MODEL = "text-embedding-3-large"
TOP_K = 6
CHAT_MODEL = "gpt-4o-mini"

CLIENT = OpenAI(api_key=OPENAI_API_KEY)