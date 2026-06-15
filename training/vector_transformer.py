"""
Vector transformer module for converting items to feature vectors.
"""
import re
import sys
import os
from typing import List, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Helpers.currencyFetcher import CurrencyFetcher
from parser import parseMod
from field_calculator import FieldDefinitions, get_mod_string, get_stat_strings

REQUIREMENTS_MAP = {
    62: 'level_requirement',
    63: 'str_requirement',
    64: 'dex_requirement',
    65: 'int_requirement'
}

PROGRESS_REPORT_INTERVAL = 1000


def keep_right(text: str) -> str:
    """Extract the rightmost value from bracketed alternatives."""
    return re.sub(r'\s+', ' ', re.sub(r'\[([^\]]+)\]', lambda m: m.group(1).split('|')[-1], text)).strip()


def numerize_prop(value_string: str) -> float:
    """Convert a property value string to a numeric value."""
    if '%' in value_string:
        return float(value_string.replace('%', ''))
    if '-' in value_string:
        vals = value_string.split('-')
        return (float(vals[0]) + float(vals[1])) / 2
    if ' or ' in value_string:
        vals = value_string.split(' or ')
        return (float(vals[0]) + float(vals[1])) / 2
    if 'Large' in value_string:
        return 3
    if 'Medium' in value_string:
        return 2
    if 'Small' in value_string:
        return 1
    return float(value_string)


def get_empty_vector(fields: FieldDefinitions) -> dict:
    """
    Create an empty feature vector with all possible fields initialized.

    Args:
        fields: FieldDefinitions containing all possible fields

    Returns:
        Dictionary with all fields initialized to default values
    """
    obj = {
        'baseType': '',
        'rarity': '',
        'ilvl': '',
        'corrupted': False,
        'desecrated': False,
        'mirrored': False,
        'sanctified': False,
        'level_requirement': 0,
        'dex_requirement': 0,
        'str_requirement': 0,
        'int_requirement': 0,
        'prefixes': 0,
        'suffixes': 0,
        'sockets': 0,
        'pdps': 0,
        'edps': 0,
        'dps': 0,
        'ar': 0,
        'es': 0,
        'ev': 0
    }

    for prop in fields.properties:
        obj[f'prop_{prop}'] = 0

    for modifier in fields.modifiers:
        obj[f'mod_{modifier}_present'] = 0
        obj[f'mod_{modifier}_fract'] = 0
        obj[f'mod_{modifier}_desecrated'] = 0
        obj[f'mod_{modifier}_tier'] = 0

    for stat in fields.stats:
        obj[f'stat_{stat}_value'] = 0

    return obj


def transform_item(item: dict, fields: FieldDefinitions, skip_stats: bool = True) -> dict:
    """
    Transform a single item into a feature vector.

    Args:
        item: Item dictionary from the API
        fields: FieldDefinitions for the vector structure
        skip_stats: Whether to skip parsing stat text values

    Returns:
        Feature vector as a dictionary
    """
    item_vector = get_empty_vector(fields)
    item_vector['baseType'] = item['item']['baseType']
    item_vector['rarity'] = item['item']['rarity']

    if 'sockets' in item['item']:
        item_vector['sockets'] = len(item['item']['sockets'])
    if 'ilvl' in item['item']:
        item_vector['ilvl'] = item['item']['ilvl']

    if 'requirements' in item['item']:
        for requirement in item['item']['requirements']:
            if requirement['type'] not in REQUIREMENTS_MAP:
                print(f"Cannot find a requirement {requirement['type']}")
            else:
                item_vector[REQUIREMENTS_MAP[requirement['type']]] = int(requirement['values'][0][0])

    for simple_property in ['corrupted', 'desecrated', 'mirrored', 'sanctified']:
        if simple_property in item['item']:
            item_vector[simple_property] = item['item'][simple_property]

    for extended_property in ['pdps', 'edps', 'dps', 'ar', 'es', 'ev']:
        if extended_property in item['item']['extended']:
            item_vector[extended_property] = item['item']['extended'][extended_property]

    prefixes = 0
    suffixes = 0

    for prop in item['item']['properties']:
        if 'type' not in prop or not prop.get('values'):
            continue
        prop_val = sum(numerize_prop(x[0]) for x in prop['values'])
        item_vector[f"prop_{prop['type']}"] = prop_val

    mods = item['item']['extended']['mods']
    for mod_category in ['explicit', 'implicit', 'fractured', 'desecrated']:
        if mod_category not in mods:
            continue
        for mod in mods[mod_category]:
            if mod['magnitudes'] is None:
                continue
            mod_str = get_mod_string(get_stat_strings(mod))
            tier = 0
            fractured = 0
            desecrated = 0
            is_prefix = False
            is_suffix = False
            if mod['tier']:
                is_prefix = 'P' in mod['tier']
                is_suffix = 'S' in mod['tier']
                tier = int(mod['tier'].replace('S', '').replace('P', ''))
            if 'fractured' in mod_str:
                mod_str = mod_str.replace('fractured', 'explicit')
                fractured = 1
            if 'desecrated' in mod_str:
                mod_str = mod_str.replace('desecrated', 'explicit')
                desecrated = 1

            if f'mod_{mod_str}_present' in item_vector:
                item_vector[f'mod_{mod_str}_present'] = 1
                item_vector[f'mod_{mod_str}_tier'] = tier
                item_vector[f'mod_{mod_str}_fract'] = fractured
                item_vector[f'mod_{mod_str}_desecrated'] = desecrated
            else:
                print('Modifier not found in fields!')

            if is_prefix:
                prefixes += 1
            if is_suffix:
                suffixes += 1

    item_vector['prefixes'] = prefixes
    item_vector['suffixes'] = suffixes

    if not skip_stats:
        stats = item['item']
        for mod_category in ['explicitMods', 'implicitMods', 'fracturedMods', 'desecratedMods']:
            if mod_category not in stats:
                continue
            for mod_text in stats[mod_category]:
                text_to_parse = keep_right(mod_text)
                parsed_result = parseMod(text_to_parse)
                if parsed_result is None:
                    print(f'Cannot parse a mod! Value: {mod_text}')
                    continue

                if not parsed_result['parseResult']:
                    numeric_value = parsed_result['matchingData'][1]
                elif len(parsed_result['parseResult']) == 1:
                    numeric_value = parsed_result['parseResult'][0]
                else:
                    numeric_value = sum(parsed_result['parseResult']) / len(parsed_result['parseResult'])

                stat_type = 'explicit' if mod_category in ['explicitMods', 'fracturedMods', 'desecratedMods'] else 'implicit'

                stat_name = ''
                if stat_name not in parsed_result['matchingData'][3]['ids']:
                    continue
                for potential_stat_name in parsed_result['matchingData'][3]['ids'][stat_type]:
                    if potential_stat_name in fields.stats:
                        stat_name = potential_stat_name
                        break
                if not stat_name:
                    print(f"Couldn't find a stat name for the stat! Value: {mod_text}")
                    continue

                item_vector[f'stat_{stat_name}_value'] += numeric_value

    return item_vector


def transform_items(items: list, fields: FieldDefinitions, skip_stats: bool = True) -> Tuple[List[list], List[float]]:
    """
    Transform all items into feature vectors with prices.

    Args:
        items: List of item dictionaries
        fields: FieldDefinitions for the vector structure
        skip_stats: Whether to skip parsing stat text values

    Returns:
        Tuple of (vectors list, prices list)
    """
    item_vectors = []
    item_prices = []
    items_count = len(items)

    print('Transforming vectors...')
    for i, item in enumerate(items):
        item_vector = transform_item(item, fields, skip_stats)
        item_vectors.append(list(item_vector.values()))

        price_calculated = np.log1p(CurrencyFetcher.get_price(item['listing']['price']))
        item_prices.append(price_calculated)

        if (i + 1) % PROGRESS_REPORT_INTERVAL == 0:
            print(f' Transformed ({i + 1}/{items_count}) items...')

    print(f'Transformed {len(item_vectors)} items total')
    return item_vectors, item_prices


if __name__ == '__main__':
    import argparse
    import json
    from data_loader import load_items
    from field_calculator import calculate_fields, load_fields

    parser = argparse.ArgumentParser(description='Transform items to feature vectors')
    parser.add_argument('data_directory', help='Directory containing data-*.json files')
    parser.add_argument('--fields', '-f', help='Path to pre-calculated fields JSON (optional)')
    parser.add_argument('--output', '-o', help='Output file path for vectors (JSON)')
    parser.add_argument('--include-stats', action='store_true', help='Include parsed stat values')

    args = parser.parse_args()

    print('Loading items...')
    items = load_items(args.data_directory)
    print(f'Loaded {len(items)} items')

    if args.fields:
        print(f'Loading fields from {args.fields}...')
        fields = load_fields(args.fields)
    else:
        print('Calculating fields...')
        fields = calculate_fields(items)

    vectors, prices = transform_items(items, fields, skip_stats=not args.include_stats)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({'vectors': vectors, 'prices': prices}, f)
        print(f'Saved vectors to {args.output}')
