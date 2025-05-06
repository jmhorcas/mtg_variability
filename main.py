import os
import csv
import json
from typing import Any
from mtgsdk import Card, Set

# Directorios base para organizar la salida
MTG_VARIANTS_DIR = 'variants/'
MTG_CARD_COLLECTION_DIR = 'products/'
MTG_STATS_DIR = 'stats/'
MTG_GLOBAL_STATS_DIR = 'global-stats/'

# Cabecera del CSV para exportar datos de cartas
CARD_HEADER = [
    'Name', 'CMC', 'Colors', 'Color identity', 'Supertypes',
    'Types', 'Subtypes', 'Rarity', 'Set', 'Power', 'Toughness', 'Loyalty', 'Text'
]

# Asegura que existen los directorios necesarios
def ensure_directories():
    for path in [MTG_CARD_COLLECTION_DIR, MTG_VARIANTS_DIR, MTG_STATS_DIR, MTG_GLOBAL_STATS_DIR]:
        os.makedirs(path, exist_ok=True)

# Carga las expansiones desde caché local o desde la API si no existe
def get_all_expansions_cached(path="all_sets.json") -> list[dict]:
    """
    Retorna una lista de expansiones como diccionarios.
    Si el archivo existe, lo carga desde JSON.
    Si no, descarga desde la API y guarda en JSON.
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    sets = Set.all()
    sets_data = [s.__dict__ for s in sets]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sets_data, f)
    return sets_data

# Función principal que extrae los productos de cada expansión
def extract_products():
    ensure_directories()

    all_expansions = get_all_expansions_cached()
    total_expansions = len(all_expansions)
    print(f'#Expansions: {total_expansions}')

    # Inicializa estadísticas globales
    global_stats = {
        'Total Expansions': total_expansions,
        'Global Card Stats': {
            'Total Cards': 0,
            'CMC': {}, 'Colors': {}, 'ColorIdentity': {}, 'Supertypes': {},
            'Types': {}, 'Subtypes': {}, 'Rarity': {}, 'Power': {}, 'Toughness': {}, 'Loyalty': {},
        }
    }

    for i, set_exp in enumerate(all_expansions):
        name = set_exp['name']
        code = set_exp['code']
        release_date = set_exp.get('release_date', 'unknown')

        # Limpieza del nombre para usar en nombres de archivo
        if '/' in name:
            name = name.split('/')[-1]
        name = name.replace(':', '_')

        # Construcción de rutas de salida
        filename = f"{MTG_CARD_COLLECTION_DIR}{code}-{name}.csv"
        variants_filename = f"{MTG_VARIANTS_DIR}{code}-{name}_variants.dat"
        stats_filename = f"{MTG_STATS_DIR}{code}-{name}_stats.json"

        # Si ya existen los archivos, saltar la expansión
        if os.path.exists(filename) and os.path.exists(variants_filename) and os.path.exists(stats_filename):
            print(f'({i}/{total_expansions})|-{set_exp["name"]}: ya procesado. Saltando...')
            continue

        # Inicializa estadísticas por expansión
        stats = {
            'Expansion': set_exp['name'],
            'Releasing year': release_date,
            'Number of cards': 0,
            'CMC': {}, 'Colors': {}, 'ColorIdentity': {}, 'Supertypes': {},
            'Types': {}, 'Subtypes': {}, 'Rarity': {}, 'Power': {}, 'Toughness': {}, 'Loyalty': {},
        }

        # Extrae cartas y variantes
        cards_list = extract_cards_from_expansion(code)
        variants = extract_variants_from_cards(cards_list, stats)

        print(f'({i}/{total_expansions})|-{set_exp["name"]}: {len(cards_list)} cartas')

        # Guarda variantes
        with open(variants_filename, 'w', encoding='utf-8') as file:
            for k, v in variants.items():
                file.write(f'{k}: {v}\n')

        # Guarda productos en CSV
        with open(filename, 'w', encoding='utf-8', newline='') as file:
            csv_writer = csv.writer(file, delimiter=',')
            csv_writer.writerow(CARD_HEADER)
            for card in cards_list:
                product_features = extract_product_features_from_card(card)
                csv_writer.writerow(product_features)

        # Guarda estadísticas por expansión
        with open(stats_filename, 'w', encoding='utf-8') as file:
            json.dump(stats, file, indent=4, ensure_ascii=False)

        # Actualiza estadísticas globales
        update_global_stats(global_stats['Global Card Stats'], stats)

    # Guarda estadísticas globales al final del proceso
    with open(os.path.join(MTG_GLOBAL_STATS_DIR, 'global_stats.json'), 'w', encoding='utf-8') as file:
        json.dump(global_stats, file, indent=4, ensure_ascii=False)

# Extrae todas las cartas de una expansión
def extract_cards_from_expansion(set_exp_code: str) -> list[Card]:
    cards = Card.where(set=set_exp_code).all()
    no_duplicate_cards = set()
    seen_names = set()

    for card in cards:
        if 'Land' in card.types and card.supertypes and 'Basic' in card.supertypes:
            no_duplicate_cards.add(card)
            seen_names.add(card.name)
        elif card.name not in seen_names:
            no_duplicate_cards.add(card)
            seen_names.add(card.name)
    return no_duplicate_cards

# Procesa cada carta y recolecta estadísticas por tipo
def extract_variants_from_cards(cards: list[Card], stats) -> dict[str, list[Any]]:
    result = {key: set() for key in [
        'CMC', 'Colors', 'ColorIdentity', 'Supertypes', 'Types',
        'Subtypes', 'Rarity', 'Power', 'Toughness', 'Loyalty'
    ]}

    for card in cards:
        stats['Number of cards'] += 1

        if card.cmc:
            result['CMC'].add(card.cmc)
            stats['CMC'][card.cmc] = stats['CMC'].get(card.cmc, 0) + 1

        if card.colors:
            result['Colors'].update(card.colors)
            for color in card.colors:
                stats['Colors'][color] = stats['Colors'].get(color, 0) + 1

        if card.color_identity:
            result['ColorIdentity'].update(card.color_identity)
            for cid in card.color_identity:
                stats['ColorIdentity'][cid] = stats['ColorIdentity'].get(cid, 0) + 1

        if card.supertypes:
            result['Supertypes'].update(card.supertypes)
            for sup in card.supertypes:
                stats['Supertypes'][sup] = stats['Supertypes'].get(sup, 0) + 1

        if card.types:
            result['Types'].update(card.types)
            for typ in card.types:
                stats['Types'][typ] = stats['Types'].get(typ, 0) + 1

        if card.subtypes:
            result['Subtypes'].update(card.subtypes)
            for sub in card.subtypes:
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

# Extrae los atributos que se exportarán al CSV
def extract_product_features_from_card(card: Card) -> list[str]:
    text = card.text.replace('\n', '\\n') if card.text else ''
    return list(map(str, [
        card.name, card.cmc, card.colors, card.color_identity, card.supertypes,
        card.types, card.subtypes, card.rarity, card.set, card.power, card.toughness,
        card.loyalty, text
    ]))

# Acumula las estadísticas globales a partir de las estadísticas individuales
def update_global_stats(global_stats, expansion_stats):
    global_stats['Total Cards'] += expansion_stats['Number of cards']
    for attr in global_stats:
        if attr == 'Total Cards':
            continue
        for key, value in expansion_stats[attr].items():
            global_stats[attr][key] = global_stats[attr].get(key, 0) + value

# Ejecuta el script si se ejecuta directamente
if __name__ == "__main__":
    extract_products()
