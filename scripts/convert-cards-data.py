import json

# Load card data
with open("../data/AllPrintings.json", "r", encoding="utf-8") as f:
    cardData = json.load(f)

allCards = []

# collect all cards from the sections
for cardSection in cardData["data"]:
    allCards.extend(cardData["data"][cardSection]["cards"])

print(f"Total cards in original data: {len(allCards)}")

seenNames = set()
output = []

for card in allCards:
    # filter out duplicates by name
    if card["name"] in seenNames:
        continue
    else:
        seenNames.add(card["name"])
    
    # map the card data to the desired output format
    output.append({
        "uuid": card.get("uuid"),                                  # unique id
        "borderColor": card.get("borderColor"),                    # string like black, white, red
        "colors": card.get("colors"),                              # array with ["W", "R"] etc
        "convertedManaCost": card.get("convertedManaCost"),        # number
        "legalities": card.get("legalities"),                      # dict with formats and Legal or not
        "manaCost": card.get("manaCost"),                          # example: "{1}{W}"
        "manaValue": card.get("manaValue"),                        # number
        "name": card.get("name"),                                  # string with name
        "keywords": card.get("keywords"),                          # abilities
        "originalText": card.get("originalText"),                  # complete text information
        "rarity": card.get("rarity"),                              # string with common, mythic, etc...
        "rulings": card.get("rulings"),                            # array of objects with date and text of special ruling. BIG chunk of data but important
        "types": card.get("types"),                                # array of all types like artifact, creature, land, etc...
        "subtypes": card.get("subtypes"),                          # for example, creature types like human, cleric, etc...
        "toughness": card.get("toughness"),                        # string for toughness
        "power": card.get("power"),                                # string for power
        "multiverseId": card.get("identifiers", {}).get("multiverseId", "")  # special id used for image fetching from gatherer
    })

print(f"Total cards in cleaned data: {len(output)}")

# write to JSON
with open("./clean-all-printings.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
