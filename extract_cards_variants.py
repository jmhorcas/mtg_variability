import os
import csv
import re
from collections.abc import Collection
from typing import Any
import json

import mtgsdk


MTG_VARIANTS_DIR = 'variants/'
MTG_CARD_COLLECTION_DIR = 'products/'
MTG_EXPANSION_COLLECTION_DIR = 'expansions/'
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
CARD_PROPERTIES = ["name",
                   "multiverse_id",
                   "layout",
                   "names",
                   "mana_cost",
                   "cmc",
                   "colors",
                   "color_identity",
                   "type",
                   "supertypes",
                   "subtypes",
                   "rarity",
                   "text",
                   "flavor",
                   "artist",
                   "number",
                   "power",
                   "toughness",
                   "loyalty",
                   "variations",
                   "watermark",
                   "border",
                   "timeshifted",
                   "hand",
                   "life",
                   "reserved",
                   "release_date",
                   "starter",
                   "rulings",
                   "foreign_names",
                   "printings",
                   "original_text",
                   "original_type",
                   "legalities",
                   "source",
                   "image_url",
                   "set",
                   "set_name",
                   "id"]

EXPANSION_PROPERTIES = ["code",
                        "name",
                        "gatherer_code",
                        "old_code",
                        "magic_cards_info_code",
                        "release_date",
                        "border",
                        "type",
                        "block",
                        "online_only",
                        "booster",
                        "mkm_id",
                        "mkm_name"]


def _is_base_number(number: str | None) -> bool:
    """True si el number es solo dígitos (sin ★, s, p, †...)."""
    return number is not None and re.fullmatch(r"\d+", number) is not None


def extract_products():
    """Extract all cards information from the expansion of all time.

    Generates a .csv file for each expansion.
    """
    all_expansions = mtgsdk.Set.all()
    total_expansions = len(all_expansions)
    print(f'#Expansions: {total_expansions}')

    if not os.path.exists(MTG_EXPANSION_COLLECTION_DIR):
        os.makedirs(MTG_EXPANSION_COLLECTION_DIR)
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
        expansion_filename = MTG_EXPANSION_COLLECTION_DIR + set_exp.code + '-' + name + '_expansion.csv'

        expansion_info = extract_expansion_info(set_exp)

        # Write expansion info
        with open(expansion_filename, 'w', encoding='utf-8', newline='') as file:
            csv_writer = csv.writer(file, delimiter=',')
            csv_writer.writerow(EXPANSION_PROPERTIES)
            row = [expansion_info.get(field, None) for field in EXPANSION_PROPERTIES]
            csv_writer.writerow(row)

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
        raise SystemExit("Extraction completed. Exiting the program.")


def _to_hashable(value: Any) -> Any:
    """Convierte un valor a algo hashable y con representación estable."""
    if isinstance(value, dict):
        # Serializa el dict de forma determinista (claves ordenadas)
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    if isinstance(value, (list, tuple, set, frozenset)):
        return json.dumps(sorted(map(str, value)), ensure_ascii=False)
    return value


def extract_variants_from_cards(
    cards: Collection[mtgsdk.Card],
    properties: list[str] = CARD_PROPERTIES,
) -> dict[str, list[Any]]:
    """Devuelve, para cada propiedad, los valores distintos que aparecen en las cartas."""
    result: dict[str, set[Any]] = {prop: set() for prop in properties}

    for card in cards:
        for prop in properties:
            value = getattr(card, prop, None)
            if value is None:
                continue

            # Si es una colección (lista, set...), cada elemento es una variante;
            # si es un escalar, el propio valor lo es.
            if isinstance(value, (list, tuple, set, frozenset)):
                items = value
            else:
                items = [value]

            for item in items:
                result[prop].add(_to_hashable(item))

    # key=str evita errores al ordenar tipos mezclados
    return {prop: sorted(values, key=str) for prop, values in result.items()}


def extract_cards_from_expansion(set_exp_code: str) -> list[mtgsdk.Card]:
    cards = mtgsdk.Card.where(set=set_exp_code, language="English").all()
    unique: dict[Any, mtgsdk.Card] = {}
    for card in cards:
        if card.multiverse_id is not None:
            unique.setdefault(("mv", card.multiverse_id), card)
        elif _is_base_number(card.number):
            unique.setdefault(("id", card.id), card)
    return list(unique.values())


def clean_text(text: str) -> str:
    """Clean the card's text to make it more legible."""
    if text is None or not isinstance(text, str):
        return text
    # Format card's text to be in one line
    text = text.replace('\n', '\\n')
    # Remove extra whitespace and tabs
    text = ' '.join(text.split())
    return text

def extract_product_features_from_card(card: mtgsdk.Card) -> dict[str, Any]:
    card_features = {property: clean_text(getattr(card, property, None)) for property in CARD_PROPERTIES}
    return card_features


def extract_expansion_info(set_exp: mtgsdk.Set) -> dict[str, Any]:
    expansion_features = {property: getattr(set_exp, property, None) for property in EXPANSION_PROPERTIES}
    return expansion_features


if __name__ == "__main__":
    extract_products()
