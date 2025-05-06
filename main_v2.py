import os
import csv
import json
from typing import Any
from mtgsdk import Card, Set
from tqdm import tqdm

# Directorios base
MTG_VARIANTS_DIR = 'variants/'
MTG_CARD_COLLECTION_DIR = 'products/'
MTG_STATS_DIR = 'stats/'
MTG_GLOBAL_STATS_DIR = '1-global-stats/'

CARD_HEADER = [
    'Name', 'CMC', 'Colors', 'Color identity', 'Supertypes',
    'Types', 'Subtypes', 'Rarity', 'Set', 'Power', 'Toughness', 'Loyalty', 'Text'
]

def ensure_directories():
    for path in [MTG_CARD_COLLECTION_DIR, MTG_VARIANTS_DIR, MTG_STATS_DIR, MTG_GLOBAL_STATS_DIR]:
        os.makedirs(path, exist_ok=True)

def get_all_expansions_cached(path="all_sets.json") -> list[dict]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    sets = Set.all()
    sets_data = [s.__dict__ for s in sets]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sets_data, f)
    return sets_data

def extract_products():
    ensure_directories()
    all_expansions = get_all_expansions_cached()
    total_expansions = len(all_expansions)

    global_stats = {
        'Total Expansions': total_expansions,
        'Global Card Stats': {
            'Total Cards': 0,
            'CMC': {}, 'Colors': {}, 'ColorIdentity': {}, 'Supertypes': {},
            'Types': {}, 'Subtypes': {}, 'Rarity': {}, 'Power': {}, 'Toughness': {}, 'Loyalty': {},
        }
    }

    for i, set_exp in enumerate(tqdm(all_expansions, desc="Procesando expansiones")):
        name = set_exp['name'].replace(':', '_').split('/')[-1]
        code = set_exp['code']
        release_date = set_exp.get('release_date', 'unknown')

        filename = f"{MTG_CARD_COLLECTION_DIR}{code}-{name}.csv"
        variants_filename = f"{MTG_VARIANTS_DIR}{code}-{name}_variants.dat"
        stats_filename = f"{MTG_STATS_DIR}{code}-{name}_stats.json"

        if os.path.exists(filename) and os.path.exists(variants_filename) and os.path.exists(stats_filename):
            continue

        stats = {
            'Expansion': set_exp['name'],
            'Releasing year': release_date,
            'Number of cards': 0,
            'CMC': {}, 'Colors': {}, 'ColorIdentity': {}, 'Supertypes': {},
            'Types': {}, 'Subtypes': {}, 'Rarity': {}, 'Power': {}, 'Toughness': {}, 'Loyalty': {},
        }

        try:
            cards_list = extract_cards_from_expansion(code)
        except Exception as e:
            print(f"Error al obtener cartas de {code}: {e}")
            continue

        variants = extract_variants_from_cards(cards_list, stats)

        # Ajuste explícito del número de cartas reales
        stats['Number of cards'] = len(cards_list)

        with open(variants_filename, 'w', encoding='utf-8') as file:
            for k, v in variants.items():
                file.write(f'{k}: {sorted(v)}\n')

        with open(filename, 'w', encoding='utf-8', newline='') as file:
            csv_writer = csv.writer(file, delimiter=',')
            csv_writer.writerow(CARD_HEADER)
            for card in cards_list:
                product_features = extract_product_features_from_card(card)
                csv_writer.writerow(product_features)

        with open(stats_filename, 'w', encoding='utf-8') as file:
            json.dump(stats, file, indent=4, ensure_ascii=False)

        update_global_stats(global_stats['Global Card Stats'], stats)

    with open(os.path.join(MTG_GLOBAL_STATS_DIR, 'global_stats.json'), 'w', encoding='utf-8') as file:
        json.dump(global_stats, file, indent=4, ensure_ascii=False)

def extract_cards_from_expansion(set_exp_code: str) -> list[Card]:
    cards = Card.where(set=set_exp_code).all()
    no_duplicate_cards = set()
    seen_names = set()

    for card in cards:
        if 'Land' in (card.types or []) and 'Basic' in (card.supertypes or []):
            no_duplicate_cards.add(card)
            seen_names.add(card.name)
        elif card.name not in seen_names:
            no_duplicate_cards.add(card)
            seen_names.add(card.name)
    return list(no_duplicate_cards)

def extract_variants_from_cards(cards: list[Card], stats) -> dict[str, set]:
    result = {key: set() for key in [
        'CMC', 'Colors', 'ColorIdentity', 'Supertypes', 'Types',
        'Subtypes', 'Rarity', 'Power', 'Toughness', 'Loyalty'
    ]}

    for card in cards:
        if card.cmc is not None:
            result['CMC'].add(card.cmc)
            stats['CMC'][card.cmc] = stats['CMC'].get(card.cmc, 0) + 1

        for color in (card.colors or []):
            result['Colors'].add(color)
            stats['Colors'][color] = stats['Colors'].get(color, 0) + 1

        for cid in (card.color_identity or []):
            result['ColorIdentity'].add(cid)
            stats['ColorIdentity'][cid] = stats['ColorIdentity'].get(cid, 0) + 1

        for sup in (card.supertypes or []):
            result['Supertypes'].add(sup)
            stats['Supertypes'][sup] = stats['Supertypes'].get(sup, 0) + 1

        for typ in (card.types or []):
            result['Types'].add(typ)
            stats['Types'][typ] = stats['Types'].get(typ, 0) + 1

        for sub in (card.subtypes or []):
            if sub:
                result['Subtypes'].add(sub)
                stats['Subtypes'][sub] = stats['Subtypes'].get(sub, 0) + 1

        if card.rarity:
            result['Rarity'].add(card.rarity)
            stats['Rarity'][card.rarity] = stats['Rarity'].get(card.rarity, 0) + 1

        if card.power:
            result['Power'].add(card.power)
            stats['Power'][card.power] = stats['Power'].get(card.power, 0) + 1

        if card.toughness:
            result['Toughness'].add(card.toughness)
            stats['Toughness'][card.toughness] = stats['Toughness'].get(card.toughness, 0) + 1

        if card.loyalty:
            result['Loyalty'].add(card.loyalty)
            stats['Loyalty'][card.loyalty] = stats['Loyalty'].get(card.loyalty, 0) + 1

    return result

def extract_product_features_from_card(card: Card) -> list[str]:
    def safe_json(value):
        return json.dumps(value if value is not None else [])

    text = card.text.replace('\n', '\\n') if card.text else ''
    return [
        card.name,
        card.cmc,
        safe_json(card.colors),
        safe_json(card.color_identity),
        safe_json(card.supertypes),
        safe_json(card.types),
        safe_json(card.subtypes),
        card.rarity,
        card.set,
        card.power,
        card.toughness,
        card.loyalty,
        text
    ]

def update_global_stats(global_stats, expansion_stats):
    global_stats['Total Cards'] += expansion_stats['Number of cards']
    for attr in global_stats:
        if attr == 'Total Cards':
            continue
        for key, value in expansion_stats[attr].items():
            global_stats[attr][key] = global_stats[attr].get(key, 0) + value

if __name__ == "__main__":
    extract_products()
