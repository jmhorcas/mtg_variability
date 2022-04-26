import os
import csv
from typing import Any

from mtgsdk import Card
from mtgsdk import Set
from mtgsdk import Type
from mtgsdk import Supertype
from mtgsdk import Subtype
from mtgsdk import Changelog


MTG_VARIANTS_DIR = 'variants/'
MTG_CARD_COLLECTION_DIR = 'products/'
CARD_HEADER = ['Name', 'CMC', 'Colors', 'Color identity', 'Supertypes',
               'Types', 'Subtypes', 'Rarity', 'Set', 'Power', 'Toughness', 'Loyalty', 'Text']

def extract_products():
    """Extract all cards information from the expansion of all time.

    Generates a .csv file for each expansion.
    """
    all_expansions = Set.all()
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
            csv_writer.writerow(CARD_HEADER)
            for card in cards_list:
                product_features = extract_product_features_from_card(card)
                csv_writer.writerow(product_features)


def extract_variants_from_cards(cards: list[Card]) -> dict[str, list[Any]]:
    result = {}
    result['CMC'] = set()
    result['Colors'] = set()
    result['ColorIdentity'] = set()
    result['Supertypes'] = set()
    result['Types'] = set()
    result['Subtypes'] = set()
    result['Rarity'] = set()
    result['Power'] = set()
    result['Toughness'] = set()
    result['Loyalty'] = set()

    for card in cards:
        if card.cmc:
            result['CMC'].add(card.cmc)
        if card.colors:
            result['Colors'].update(card.colors)  
        if card.color_identity:
            result['ColorIdentity'].update(card.color_identity)  
        if card.supertypes:
            result['Supertypes'].update(card.supertypes)  
        if card.types:
            result['Types'].update(card.types)  
        if card.subtypes:
            result['Subtypes'].update(card.subtypes) 
        if card.rarity:
            result['Rarity'].add(card.rarity) 
        if card.power:
            result['Power'].add(card.power) 
        if card.toughness:
            result['Toughness'].add(card.toughness) 
        if card.loyalty:
            result['Loyalty'].add(card.loyalty) 
    return result


def extract_cards_from_expansion(set_exp_code: str) -> list[Card]:
    cards = Card.where(set=set_exp_code).all()
    # Remove duplicate cards
    no_duplicate_cards = set()
    for card in cards:
        # print(f'{card.type} -> {card.supertypes} -> {card.subtypes} -> {card.types}')
        if 'Land' in card.types and card.supertypes is not None and 'Basic' in card.supertypes:
            no_duplicate_cards.add(card)
        elif not any(c.name == card.name for c in no_duplicate_cards):
            no_duplicate_cards.add(card)
    # print(f'#Cards: {len(no_duplicate_cards)}')
    return no_duplicate_cards


def extract_product_features_from_card(card: Card) -> list[str]:
    result = list()
    result.append(card.name)
    result.append(card.cmc)
    result.append(card.colors)
    result.append(card.color_identity)
    result.append(card.supertypes)
    result.append(card.types)
    result.append(card.subtypes)
    result.append(card.rarity)
    result.append(card.set)
    result.append(card.power)
    result.append(card.toughness)
    result.append(card.loyalty)
    text = card.text.replace(
        '\n', '\\n') if card.text is not None else card.text
    result.append(text)
    return list(map(lambda x: str(x), result))


if __name__ == "__main__":
    extract_products()
