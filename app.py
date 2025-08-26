# -------- IMPORTS --------
from flask import Flask, request
from flask_cors import CORS
import os
import json

# -------- UTILS --------
from utils.index_utils import build_index
from utils.model_utils import answer_with_subqueries
from utils.config_utils import CARDS_FILE

# -------- INITIALIZATION --------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
build_index()

@app.get('/cards')
def cards():
  if not os.path.exists(CARDS_FILE):
    print(f"Card file not found at {CARDS_FILE}")
    return []

  with open(CARDS_FILE, "r", encoding="utf-8") as f:
    cards = json.load(f)

    # extract only names and ids
    print(f"Loaded {len(cards)} cards")
    card_list = [{"uuid": c.get("uuid", ""), "name": c.get("name", ""), "multiverseId": c.get("multiverseId", "")} for c in cards if "name" in c]
  
    return {"cards": card_list}

@app.post('/ask')
def ask():

  #!TEST
  return {
     "question": "question test",
     "short_answer": "short answer test",
     "full_explanation": "full explanation test",
     "sources": "sources test",
     "single_word_answer": "single word test",
  }

  # if the request is not JSON, return an error
  if not request.is_json:
    return {"error": "Request must include a JSON in the body with the question parameter"}, 400
  
  # if the request does not contain the required parameters, return an error
  data = request.get_json()

  if 'question' not in data:
    return {"error": "Missing input data: 'question' is required."}, 400

  response = answer_with_subqueries(data["question"])
        
  return response

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5005, debug=True)