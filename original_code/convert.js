const cardData = require("../old-data/AllPrintings.json")
// const cardData = require("../old-data/Standard.json")
const fs = require("fs");


const allCards = []

for (let cardSection in cardData.data) {
  allCards.push(...cardData.data[cardSection].cards)
}

console.log(`Total cards in original data: ${allCards.length}`);

const seenNames = new Set();
const output = allCards
.filter((card) => {
  // filter out duplicates by name
  if (seenNames.has(card.name)) {
    return false;
  } else {
    seenNames.add(card.name);
    return true;
  }
})
.map((card) => {
    // map the card data to the desired output format
    return {
      uuid: card.uuid,                                    // unique id
      borderColor: card.borderColor,                      // string like black, white, red
      colors: card.colors,                                // array with ["W", "R"] etc
      convertedManaCost: card.convertedManaCost,          // number
      legalities: card.legalities,                        // dict with formats and Legal or not
      manaCost: card.manaCost,                            // example: "{1}{W}"
      manaValue: card.manaValue,                          // number
      name: card.name,                                    // string with name
      keywords: card.keywords,                            // abilities
      originalText: card.originalText,                    // complete text information
      rarity: card.rarity,                                // string with common, mythic, etc...
      rulings: card.rulings,                              // array of objects with date and text of special ruling. BIG chunk of data but important
      types: card.types,                                  // array of all types like artifact, creature, land, etc...
      subtypes: card.subtypes,                            // for example, creature types like human, cleric, etc...
      toughness: card.toughness,                          // string for toughness
      power: card.power,                                  // string for power
      multiverseId: card.identifiers.multiverseId || ""   // special id used for image fetching from gatherer
    };
  });

console.log(`Total cards in cleaned data: ${output.length}`);

fs.writeFileSync("./clean-all-printings.json", JSON.stringify(output, null, 2), "utf8");
// fs.writeFileSync("./clean-standard-cards.json", JSON.stringify(output, null, 2), "utf8");