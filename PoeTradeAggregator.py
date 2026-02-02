import json
import os
import random
import re

import numpy as np
from catboost import Pool, CatBoostRegressor

from Helpers.currencyFetcher import CurrencyFetcher
from parser import parseMod

REQUIREMENTS_MAP = {
    62: 'level_requirement',
    63: 'str_requirement',
    64: 'dex_requirement',
    65: 'int_requirement'
}
EVAL_SET_RATIO = 0.1
PROGRESS_REPORT_INTERVAL = 1000
SKIP_STATS = True


def keep_right(text: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'\[([^\]]+)\]', lambda m: m.group(1).split('|')[-1], text)).strip()


def load_items(data_directory: str) -> list:
    items = []
    for file in os.listdir(data_directory):
        filename = os.fsdecode(file)
        if not filename.startswith('data-'):
            continue
        with open(f'{data_directory}/{filename}', encoding='utf-8') as f:
            items.extend(json.load(f)['result'])
    random.shuffle(items)
    return items

def get_empty_vector(possible_modifiers: list, possible_properties: list, possible_stats: list) -> dict:
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

    for prop in possible_properties:
        obj[f'prop_{prop}'] = 0

    for modifier in possible_modifiers:
        obj[f'mod_{modifier}_present'] = 0
        obj[f'mod_{modifier}_fract'] = 0
        obj[f'mod_{modifier}_desecrated'] = 0
        obj[f'mod_{modifier}_tier'] = 0

    for stat in possible_stats:
        obj[f'stat_{stat}_value'] = 0

    return obj

def numerize_prop(value_string: str) -> float:
    if '%' in value_string:
        return float(value_string.replace('%', ''))
    if '-' in value_string:
        vals = value_string.split('-')
        return (float(vals[0]) + float(vals[1])) / 2
    if 'Large' in value_string:
        return 3
    if 'Medium' in value_string:
        return 2
    if 'Small' in value_string:
        return 1
    return float(value_string)


def get_mod_string(stats: list) -> str:
    stats.sort()
    return ','.join(stats)


def get_stat_strings(mod: dict) -> list:
    if 'magnitudes' not in mod or mod['magnitudes'] is None:
        return []

    unique_magns = []
    for magn in mod['magnitudes']:
        magn_value = magn['hash']
        if 'fractured' in magn_value or 'desecrated' in magn_value:
            magn_value = magn_value.replace('fractured', 'explicit').replace('desecrated', 'explicit')
        if magn_value not in unique_magns:
            unique_magns.append(magn_value)
    return unique_magns

def train_model(model_name: str, data_directory: str, model_save_directory: str,
                fields_save_directory: str, iterations: int = 1500, learning_rate: float = 0.15,
                depth: int = 6):
    print(f"Starting training for {model_name}")
    print('Loading items...')
    items = load_items(data_directory)
    item_vectors = []
    item_prices = []
    possible_properties = set()
    possible_modifiers = set()
    possible_stats = set()

    def load_modifiers():
        print('Loading modifiers...')
        for item in items:
            mods = item['item']['extended']['mods']
            all_mods = []
            for mod_category in ['explicit', 'implicit', 'fractured', 'desecrated']:
                if mod_category in mods:
                    all_mods.extend(mods[mod_category])
            for mod in all_mods:
                stat_strs = get_stat_strings(mod)
                mod_str = get_mod_string(stat_strs)
                possible_stats.update(s for s in stat_strs if s)
                if mod_str:
                    possible_modifiers.add(mod_str)

            for item_property in item['item']['properties']:
                if 'type' in item_property:
                    possible_properties.add(item_property['type'])

    def transform_items():
        nonlocal possible_modifiers, possible_properties, possible_stats
        possible_modifiers = sorted(possible_modifiers)
        possible_properties = sorted(possible_properties)
        possible_stats = sorted(possible_stats)

        print('Transforming vectors...')
        items_count = len(items)
        items_processed = 0
        for item in items:
            item_vector = get_empty_vector(possible_modifiers, possible_properties, possible_stats)
            item_vector['baseType'] = item['item']['baseType']
            item_vector['rarity'] = item['item']['rarity']
            if 'sockets' in item['item']:
                item_vector['sockets'] = len(item['item']['sockets'])
            if 'ilvl' in item['item']:
                item_vector['ilvl'] = item['item']['ilvl']

            if 'requirements' in item['item']:
                for requirement in item['item']['requirements']:
                    if requirement['type'] not in REQUIREMENTS_MAP:
                        print(f"Can not find a requirement {requirement['type']}")
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
                        print('stuff not found!')
                    if is_prefix:
                        prefixes += 1
                    if is_suffix:
                        suffixes += 1

            item_vector['prefixes'] = prefixes
            item_vector['suffixes'] = suffixes

            stats = item['item']
            if not SKIP_STATS:
                for mod_category in ['explicitMods', 'implicitMods', 'fracturedMods', 'desecratedMods']:
                    if mod_category not in stats:
                        continue
                    for mod_text in stats[mod_category]:
                        text_to_parse = keep_right(mod_text)
                        parsed_result = parseMod(text_to_parse)
                        if parsed_result is None:
                            print(f'Can not parse a mod! Value: {mod_text}')
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
                            if potential_stat_name in possible_stats:
                                stat_name = potential_stat_name
                                break
                        if not stat_name:
                            print(f"Couldn't find a stat name for the stat! Value: {mod_text}")
                            continue

                        item_vector[f'stat_{stat_name}_value'] += numeric_value

            item_vectors.append(list(item_vector.values()))

            price_calculated = np.log1p(CurrencyFetcher.get_price(item['listing']['price']))
            item_prices.append(price_calculated)
            items_processed += 1
            if items_processed % PROGRESS_REPORT_INTERVAL == 0:
                print(f' Transformed ({items_processed}/{items_count}) items...')

    def train_and_save_model():
        eval_set_size = int(len(item_vectors) * EVAL_SET_RATIO)

        if eval_set_size > 0:
            train_vectors = item_vectors[:-eval_set_size]
            train_prices = item_prices[:-eval_set_size]
            control_vectors = item_vectors[-eval_set_size:]
            control_prices = item_prices[-eval_set_size:]
        else:
            train_vectors = item_vectors
            train_prices = item_prices
            control_vectors = []
            control_prices = []

        cat_features = [0, 1]

        model = CatBoostRegressor(
            iterations=iterations,
            learning_rate=learning_rate,
            depth=depth
        )

        if control_vectors:
            eval_dataset = Pool(control_vectors, control_prices, cat_features=cat_features)
            model.fit(train_vectors, train_prices, cat_features=cat_features, eval_set=eval_dataset)

            preds = model.predict(control_vectors)
            for i in range(preds.size):
                actual = np.expm1(control_prices[i])
                predicted = np.expm1(preds[i])
                diff = np.abs(float(control_prices[i]) - preds[i])
                print(f'{i:>4}. [{actual:<8.1f} {predicted:<12.1f}] ({diff:>12.1f}) [{control_vectors[i][1]}]')
            print('')
        else:
            model.fit(train_vectors, train_prices, cat_features=cat_features)

        model.save_model(f"{model_save_directory}/{model_name}", format="cbm", pool=train_vectors)
        with open(f"{fields_save_directory}/{model_name}.json", 'w', encoding='utf-8') as f:
            json.dump({
                'properties': possible_properties,
                'modifiers': possible_modifiers,
                'stats': possible_stats
            }, f, ensure_ascii=False, indent=4)

    load_modifiers()
    transform_items()
    train_and_save_model()

