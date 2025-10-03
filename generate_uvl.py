import os
import csv
import ast
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


import argparse
import pathlib

from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.configuration_metamodel.transformations import (
    ConfigurationJSONReader, 
    UVLSJSONReader
)
from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
from flamapy.metamodels.pysat_metamodel.operations import (
    PySATSatisfiable,
    PySATSatisfiableConfiguration
)


BASE_UVL_MODEL = 'uvl_models/base.uvl'
EXPANSION_VARIANTS_CSV = 'variants/LEA-Limited Edition Alpha_variants.dat'


def generate_uvl() -> None:
    fm = UVLReader(BASE_UVL_MODEL).transform()
    print(fm)



    data = {}

    with open(EXPANSION_VARIANTS_CSV, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                # Convierte la lista (texto) en un objeto Python real
                data[key] = ast.literal_eval(value)

    # Ahora tienes un diccionario Python
    print(data.keys())  # dict_keys(['name', 'mana_cost', 'cmc', 'colors', ...])
    print(len(data["mana_cost"]))  # número de cartas
    print(data["mana_cost"])

    # Variation points and their possible values for mana cost
    mana_cost_variations: dict[str, set[int]] = {}
    for mana_cost in data["mana_cost"]:
        mana_dict = parse_mana_cost(mana_cost)
        for mana_type, count in mana_dict.items():
            if mana_type not in mana_cost_variations:
                mana_cost_variations[mana_type] = set()
            mana_cost_variations[mana_type].add(count)
    print(mana_cost_variations)
    for mana_type, values in mana_cost_variations.items():
        constraint = restrict_values(mana_type, values)
        if constraint:
            fm.get_constraints().append(constraint)
    print(fm)




def parse_mana_cost(mana_cost: str) -> dict[str, int]:
    """Parse the mana cost string into a dictionary of mana types and their counts.

    Args:
        mana_cost (str): The mana cost string (e.g., "{2}{G}{G}{U}").
    Returns:
        dict[str, int]: A dictionary with mana types as keys and their counts as values.
    """
    mana_dict = {  # Keys are the same name as features in the UVL model
        "Colorless mana": 0,
        "White mana": 0,
        "Blue mana": 0,
        "Black mana": 0,
        "Red mana": 0,
        "Green mana": 0
    }
    if not mana_cost:
        return mana_dict
    mana_symbols = mana_cost.replace('{', '').split('}')  # Remove curly braces and split
    for symbol in mana_symbols:
        if symbol.isdigit():
            mana_dict["Colorless mana"] += int(symbol)
        elif symbol == 'W':
            mana_dict["White mana"] += 1
        elif symbol == 'U':
            mana_dict["Blue mana"] += 1
        elif symbol == 'B':
            mana_dict["Black mana"] += 1
        elif symbol == 'R':
            mana_dict["Red mana"] += 1
        elif symbol == 'G':
            mana_dict["Green mana"] += 1
    return mana_dict


def restrict_values(identifier: str, values: set[int]) -> str | None:
    if not values:
        return None  # The identifier cannot take any value
    
    values = sorted(values)
    intervals = []
    start = prev = values[0]
    for v in values[1:]:
        if v == prev + 1:  # sigue la secuencia
            prev = v
        else:  # cerramos intervalo
            intervals.append((start, prev))
            start = prev = v
    intervals.append((start, prev))  # último intervalo
    
    parts = []
    for a, b in intervals:
        if a == b:
            parts.append(f"({identifier} == {a})")
        else:
            parts.append(f"({identifier} >= {a} & {identifier} <= {b})")
    return " | ".join(parts)



if __name__ == "__main__":
    generate_uvl()
