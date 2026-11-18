import ast
import json
import re
from typing import Any, Collection, Sequence

import mtgsdk

from .taxonomy import (
    KNOWN_SUPERTYPES,
    KNOWN_CARD_TYPES,
    KNOWN_ARTIFACT_SUBTYPES,
    KNOWN_ENCHANTMENT_SUBTYPES,
    KNOWN_LAND_SUBTYPES,
    KNOWN_SPELL_SUBTYPES
)


# --------------------------------------------------------------------------- #
# Schemas / Domain Constants
# --------------------------------------------------------------------------- #
CARD_PROPERTIES = (
    "mana_cost", "cmc", "colors", "color_identity", "type", "supertypes",
    "subtypes", "rarity", "text", "number", "power", "toughness", "loyalty", "set",
)

ALL_CARD_PROPERTIES = (
    "name", "multiverse_id", "layout", "names", "mana_cost", "cmc", "colors",
    "color_identity", "type", "supertypes", "subtypes", "rarity", "text",
    "flavor", "artist", "number", "power", "toughness", "loyalty", "variations",
    "watermark", "border", "timeshifted", "hand", "life", "reserved",
    "release_date", "starter", "rulings", "foreign_names", "printings",
    "original_text", "original_type", "legalities", "source", "image_url",
    "set", "set_name", "id",
)

EXPANSION_PROPERTIES = (
    "code", "name", "gatherer_code", "old_code", "magic_cards_info_code",
    "release_date", "border", "type", "block", "online_only", "booster",
    "mkm_id", "mkm_name",
)

# Fields in the CSV that represent serialized lists in string format (e.g., "['W', 'U']")
LIST_FIELDS = {"colors", "color_identity", "supertypes", "subtypes", "names", "variations", "printings"}

# Diccionario de mapeo estático para subtipos cerrados (evita los if-elif masivos)
SUBTYPE_TAXONOMY_MAP = {
    "artifact": KNOWN_ARTIFACT_SUBTYPES,
    "enchantment": KNOWN_ENCHANTMENT_SUBTYPES,
    "land": KNOWN_LAND_SUBTYPES,
    "spell": KNOWN_SPELL_SUBTYPES,
}

# --------------------------------------------------------------------------- #
# Pure Transformation Functions
# --------------------------------------------------------------------------- #
def is_base_number(number: str | None) -> bool:
    """True if the collector number contains only digits."""
    return number is not None and re.fullmatch(r"\d+", number) is not None


def to_hashable(value: Any) -> Any:
    """Converts complex values into a deterministic hashable representation."""
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    if isinstance(value, (list, tuple, set, frozenset)):
        return json.dumps(sorted(map(str, value)), ensure_ascii=False)
    return value


def clean_text(text: Any) -> Any:
    """Normalizes line breaks and multiple spaces in text strings."""
    if text is None or not isinstance(text, str):
        return text
    return " ".join(text.replace("\n", "\\n").split())


def extract_product_features_from_card(card: mtgsdk.Card) -> dict[str, Any]:
    """Extracts and cleans all properties from an mtgsdk Card object."""
    return {prop: clean_text(getattr(card, prop, None)) for prop in ALL_CARD_PROPERTIES}


def extract_expansion_info(set_exp: mtgsdk.Set) -> dict[str, Any]:
    """Extracts metadata from an mtgsdk Set object."""
    return {prop: getattr(set_exp, prop, None) for prop in EXPANSION_PROPERTIES}


def parse_csv_row(row: dict[str, str]) -> dict[str, Any]:
    """Converts a raw row from csv.DictReader into clean Python types."""
    parsed: dict[str, Any] = {}
    for key, val in row.items():
        if val == "" or val is None:
            parsed[key] = None
        elif key in LIST_FIELDS and val.startswith("["):
            try:
                parsed[key] = ast.literal_eval(val)
            except (ValueError, SyntaxError):
                parsed[key] = val
        else:
            parsed[key] = val
    return parsed


def extract_variants_from_cards(cards: Collection[mtgsdk.Card | dict[str, Any]], properties: Sequence[str] = ALL_CARD_PROPERTIES) -> dict[str, list[Any]]:
    """Returns unique values for each property from a collection of cards (objects or dicts)."""
    result: dict[str, set[Any]] = {prop: set() for prop in properties}

    for card in cards:
        for prop in properties:
            value = card.get(prop) if isinstance(card, dict) else getattr(card, prop, None)
            if value is None or value == "":
                continue

            items = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
            for item in items:
                result[prop].add(to_hashable(item))

    return {prop: sorted(values, key=str) for prop, values in result.items()}


def _classify_subtype(sub_cap: str, main_types: list[str]) -> str:
    """Determina la categoría de un subtipo basándose en las reglas taxonómicas."""
    # 1. Comprobar en los conjuntos cerrados conocidos
    for category, known_set in SUBTYPE_TAXONOMY_MAP.items():
        if sub_cap in known_set:
            return f"{category}_subtypes"
            
    # 2. Categorías contextuales basadas en el tipo principal de la carta
    if "Plane" in main_types:
        return "planar_subtypes"
    if "Dungeon" in main_types:
        return "dungeon_subtypes"
    if "Battle" in main_types:
        return "battle_subtypes"
    if "Planeswalker" in main_types:
        return "planeswalker_subtypes"
        
    # 3. Por defecto (por exclusión según reglas de MTG), es un subtipo de criatura
    return "creature_subtypes"


def extract_types_and_subtypes(raw_type_strings: list[str]) -> dict[str, list[str]]:
    """
    Parse a list of MTG type strings into cleanly separated and categorized structures 
    following Clean Code and Open/Closed Principles.
    """
    extracted_data = {
        "supertypes": set(),
        "types": set(),
        "creature_subtypes": set(),
        "artifact_subtypes": set(),
        "land_subtypes": set(),
        "enchantment_subtypes": set(),
        "spell_subtypes": set(),
        "planeswalker_subtypes": set(),
        "planar_subtypes": set(),
        "dungeon_subtypes": set(),
        "battle_subtypes": set(),
    }
    
    for entry in raw_type_strings:
        if not entry:
            continue
            
        # El formato en MTG es: "[Supertypes] [Types] — [Subtypes]"
        parts = re.split(r'\s+—\s+|\s+-\s+', entry)
        
        # 1. Procesar la parte izquierda (Supertypes y Main Types)
        left_side = parts[0].strip()
        main_types_in_card = []
        
        for word in left_side.split():
            word_cap = word.capitalize()
            if word_cap in KNOWN_SUPERTYPES:
                extracted_data["supertypes"].add(word_cap)
            elif word_cap in KNOWN_CARD_TYPES:
                extracted_data["types"].add(word_cap)
                main_types_in_card.append(word_cap)
                
        # 2. Procesar la parte derecha (Subtipos) si existe
        if len(parts) > 1:
            subtypes_part = parts[1].strip()
            for sub in subtypes_part.split():
                sub_cap = sub.capitalize()
                # Delegamos la clasificación a una función pura especializada
                category_key = _classify_subtype(sub_cap, main_types_in_card)
                extracted_data[category_key].add(sub_cap)
                
    # Convertir todos los sets a listas ordenadas de forma limpia
    return {k: sorted(list(v)) for k, v in extracted_data.items()}