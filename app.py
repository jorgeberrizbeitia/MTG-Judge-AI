# -------- IMPORTS --------
from flask import Flask, request
from flask_cors import CORS
import os
import json

# -------- UTILS --------
from utils.model_utils import answer_with_subqueries, fetch_cards_info
from utils.config_utils import CARDS_FILE

import time # just for simulating sending a response in 18 seconds

# -------- INITIALIZATION --------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

# build_index() #todo commented out so it doesn't run every time the server runs

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

  # if the request is not JSON, return an error
  if not request.is_json:
    return {"error": "Request must include a JSON in the body with the question parameter"}, 400
  
  # if the request does not contain the required parameters, return an error
  data = request.get_json()

  if 'question' not in data:
    return {"error": "Missing input data: 'question' is required."}, 400
  
  user_prompt = data.get("question", "").strip()
  selected_cards = data.get("cards", [])  # list of card names or ids

  if len(selected_cards) != 0:
    cards_info = fetch_cards_info(selected_cards)


  response = answer_with_subqueries(user_prompt, cards_info)
        
  return response

#!TEST ROUTE without using the OPEN AI API
@app.post('/test')
def test():

  time.sleep(15) 
  return {
     "question": "QUESTION, Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
     "short_answer": "SHORT ANSWER Lorem ipsum dolor sit amet, consectetur adipiscing elit",
     "full_explanation": "FULL EXPLANATION Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
     "sources": "SOURCES Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
  }

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5005, debug=True)