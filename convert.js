const cardData = require("./Standard.json")
const fs = require("fs");

const output = cardData.data.BIG.cards.map((card) => {
    return {
      borderColor: card.borderColor,              // string like black, white, red
      colors: card.colors,                        // array with ["W", "R"] etc
      convertedManaCost: card.convertedManaCost,  // number
      legalities: card.legalities,                // dict with formats and Legal or not
      manaCost: card.manaCost,                    // example: "{1}{W}"
      manaValue: card.manaValue,                  // number
      name: card.name,                            // string with name
      keywords: card.keywords,                    // abilities
      originalText: card.originalText,            // complete text information
      rarity: card.rarity,                        // string with common, mythic, etc...
      rulings: card.rulings,                      // array of objects with date and text of special ruling. BIG chunk of data but important
      // type: card.type,                            // string for main type. needed?
      types: card.types,                          // array of all types
    };
  });

fs.writeFileSync("./output.json", JSON.stringify(output, null, 2), "utf8");