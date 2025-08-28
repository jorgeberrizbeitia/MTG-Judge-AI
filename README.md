
# MTG Judge AI

AI-powered Magic: The Gathering rules and card Q&A API using Embeddings and RAC.

# Technologies used

- OpenAI gpt and embedding models
- Retrieval-Augmented Composition (RAC)
- ChromaDB & SQLite3
- Flask Server

## Requirements

Install all dependencies:

```bash
pip install -r requirements.txt
```

## Setup

1. Create a `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your-key-here
   ```
2. Download the complete MTG card data (AllPrintings) from [MTGJSON](https://mtgjson.com/downloads/all-files/) and save as `data/clean-all-printings.json`.
3. Download the txt MTG comprehensive rules from the [Wizards official site](https://magic.wizards.com/en/rules) and save as `data/comprehensive-rules.txt`.

## Usage

1. Build the index:
   ```bash
   python scripts/index_utils.py
   ```
2. Convert card data:
   ```bash
   python scripts/convert-cards-data.py
   ```
3. Start the server:
   ```bash
   python app.py
   ```
4. Access the API via Postman or run the frontend.

## Project Structure

- `app.py` - Main Flask API server
- `utils/` - Utility modules (main logic functions and config variables)
- `data/` - Card and rules data files
- `scripts/` - Executables for building index and formatting data
- `original_code/` - Code from initial attempts and tests (initial benchmarks)

## Extras

- [Presentation](https://www.canva.com/design/DAGxWgk3XE4/3Pv1_2CPKRj1pU2cWt35lA/edit?utm_content=DAGxWgk3XE4&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

---
Minimal, clear, and ready to use.

