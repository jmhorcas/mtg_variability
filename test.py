from mtgsdk import Card
from mtgsdk import Set
from mtgsdk import Type
from mtgsdk import Supertype
from mtgsdk import Subtype
from mtgsdk import Changelog

def extract_product_from_card(card: Card) -> str:
    result = list()
    result.append(card.layout)
    result.append(card.cmc)
    result.append(card.colors)
    result.append(card.color_identity)
    result.append(card.supertypes)
    result.append(card.types)
    result.append(card.subtypes)
    result.append(card.rarity)
    result.append(card.power)
    result.append(card.toughness)
    result.append(card.text)

    result = map(lambda x: '\"' + str(x) + '\"', result)
    return ', '.join(result) + '\n'


def main():
    set_exp = Set.find('NEO')
    print(f'Set name: {set_exp.name}')
    print(f'  |-block: {set_exp.block}')
    print(f'  |-code: {set_exp.code}')
    print(f'  |-gatherer_code: {set_exp.gatherer_code}')
    print(f'  |-old_code: {set_exp.old_code}')
    print(f'  |-magic_cards_info_code: {set_exp.magic_cards_info_code}')
    print(f'  |-release_date: {set_exp.release_date}')
    print(f'  |-border: {set_exp.border}')
    if 'expansion' in dir(set_exp):
        print(f'  |-expansion: {set_exp.expansion}')
    print(f'  |-online_only: {set_exp.online_only}')
    print(f'  |-booster: {set_exp.booster}')

    cards = Card.where(set=set_exp.code).all()

    types = list()
    subtypes = list()
    supertypes = list()
    powers = list()
    toughness = list()
    cmcs = list()
    lines = list()
    for i, card in enumerate(cards):
        types.extend(card.types)
        if card.subtypes:
            subtypes.extend(card.subtypes)
        if card.supertypes:
            supertypes.extend(card.supertypes)
        if card.power:
            powers.extend(card.power)
        if card.toughness:
            toughness.extend(card.toughness)
        if card.cmc:
            cmcs.extend(card.cmc)

        card_str = extract_product_from_card(card)
        print(card_str)
        lines.append(card_str)

        if card.name == 'Dragon Whelp':
            print(f'{i} - name: {card.name}')
            print(f'  |-layout: {card.layout}')
            print(f'  |-cmc: {card.cmc}')
            print(f'  |-colors: {card.colors}')
            print(f'  |-color_identity: {card.color_identity}')
            print(f'  |-type: {card.type}')
            print(f'  |-supertypes: {card.supertypes}')
            print(f'  |-types: {card.types}')
            print(f'  |-subtypes: {card.subtypes}')
            print(f'  |-rarity: {card.rarity}')
            print(f'  |-set: {card.set}')
            print(f'  |-set_name: {card.set_name}')
            print(f'  |-text: {card.text}')
            print(f'  |-flavor: {card.flavor}')
            print(f'  |-artist: {card.artist}')
            print(f'  |-number: {card.number}')
            print(f'  |-power: {card.power}')
            print(f'  |-toughness: {card.toughness}')
            print(f'  |-loyalty: {card.loyalty}')
            if 'language' in dir(card):
                print(f'  |-language: {card.language}')
            if 'game_format' in dir(card):
                print(f'  |-game_format: {card.game_format}')
            if 'legality' in dir(card):
                print(f'  |-legality: {card.legality}')
            print(f'  |-id: {card.id}')
            print(f'  |-multiverseid: {card.multiverse_id}')
            print(f'  |-names: {card.names}')
            print(f'  |-variations: {card.variations}')
            print(f'  |-image_url: {card.image_url}')
            print(f'  |-watermark: {card.watermark}')
            print(f'  |-border: {card.border}')
            print(f'  |-timeshifted: {card.timeshifted}')
            print(f'  |-hand: {card.hand}')
            print(f'  |-life: {card.life}')
            if 'reserved' in dir(card):
                print(f'  |-reserved: {card.reserved}')
            print(f'  |-release_date: {card.release_date}')
            print(f'  |-starter: {card.starter}')
            print(f'  |-rulings: {card.rulings}')
            print(f'  |-foreign_names: {card.foreign_names}')
            print(f'  |-printings: {card.printings}')
            print(f'  |-original_text: {card.original_text}')
            print(f'  |-original_type: {card.original_type}')
            print(f'  |-legalities: {card.legalities}')
            print(f'  |-source: {card.source}')

    types = set(types)
    subtypes = set(subtypes)
    supertypes = set(supertypes)
    powers = set(powers)
    toughness = set(toughness)
    print(f'Types: {types}')
    print(f'powers: {powers}')
    print(f'toughness: {toughness}')
    print(f'subtypes: {subtypes}')
    print(f'supertypes: {supertypes}')

    with open(set_exp.name + '.csv', 'w', encoding='utf8') as file:
        file.writelines(lines)

if __name__ == "__main__":
    main()  