import os
import csv
from collections.abc import Collection
from typing import Any

import mtgsdk


MTG_VARIANTS_DIR = 'variants/'
MTG_CARD_COLLECTION_DIR = 'products/'
CARD_PROPERTIES = ["name",
                   "mana_cost",
                   "cmc",
                   "colors",
                   "color_identity",
                   "type",
                   "supertypes",
                   "subtypes",
                   "rarity",
                   "text",
                   "number",
                   "power",
                   "toughness",
                   "loyalty",
                   "set",
                   "set_name"]


def extract_products():
    """Extract all cards information from the expansion of all time.

    Generates a .csv file for each expansion.
    """
    all_expansions = mtgsdk.Set.all()
    total_expansions = len(all_expansions)
    print(f'#Expansions: {total_expansions}')

    if not os.path.exists(MTG_CARD_COLLECTION_DIR):
        os.makedirs(MTG_CARD_COLLECTION_DIR)
    if not os.path.exists(MTG_VARIANTS_DIR):
        os.makedirs(MTG_VARIANTS_DIR)

    for i, set_exp in enumerate(all_expansions):
        name = set_exp.name
        if '/' in name:
            name = name.split('/')[-1]
        name = name.replace(':', '_')
        filename = MTG_CARD_COLLECTION_DIR + set_exp.code + '-' + name + '.csv'
        variants_filename = MTG_VARIANTS_DIR + set_exp.code + '-' + name + '_variants.dat'

        cards_list = extract_cards_from_expansion(set_exp.code)
        variants = extract_variants_from_cards(cards_list)

        print(f'({i}/{total_expansions})|-{set_exp.name}: {len(cards_list)}')

        # Write variants
        with open(variants_filename, 'w', encoding='utf-8') as file:
            for k, v in variants.items():
                file.write(f'{k}: {v}\n')
        
        # Write products
        with open(filename, 'w', encoding='utf-8', newline='') as file:
            csv_writer = csv.writer(file, delimiter=',')
            csv_writer.writerow(CARD_PROPERTIES)
            for card in cards_list:
                product_features = extract_product_features_from_card(card)
                row = [product_features.get(field, None) for field in CARD_PROPERTIES]
                csv_writer.writerow(row)


def extract_variants_from_cards(cards: list[mtgsdk.Card]) -> dict[str, list[Any]]:
    result = {property: set() for property in CARD_PROPERTIES}
    for card in cards:
        for property in CARD_PROPERTIES:
            value = getattr(card, property, None)
            if value is not None:
                if isinstance(value, Collection) and not isinstance(value, (str, bytes, bytearray)):
                    result[property].update(value)
                else:
                    result[property].add(value)
    result = {property: sorted(values) for property, values in result.items()} 
    return result


def extract_cards_from_expansion(set_exp_code: str) -> list[mtgsdk.Card]:
    cards = mtgsdk.Card.where(set=set_exp_code, language="English").all()
    # Remove duplicate cards
    no_duplicate_cards = set()
    for card in cards:
        if not any(c.multiverse_id == card.multiverse_id for c in no_duplicate_cards):
            no_duplicate_cards.add(card)
    return no_duplicate_cards


def extract_product_features_from_card(card: mtgsdk.Card) -> dict[str, Any]:
    card_features = {property: getattr(card, property, None) for property in CARD_PROPERTIES}
    # Format card's text to be in one line
    card_features["text"] = card_features["text"].replace(
        '\n', '\\n') if card_features["text"] is not None else card_features["text"]
    return card_features


if __name__ == "__main__":
    extract_products()
