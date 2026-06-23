import os

from training.pipeline import run_pipeline
from parser import initParser
from Helpers.currencyFetcher import CurrencyFetcher

initParser()
CurrencyFetcher.get_rates()

TRAIN_GENERIC = True
TRAIN_UNIQUE = True
IGNORE_EXISTING = False

whitelist = ["Tablet"]
exceptions = [
    'Area Level',
    'Relic',

    "Bluetongue",
    "Controlled Metamorphosis",
    "Tangletongue",
    "The Dancing Dervish",
    "The Last Flame"
]

name_map = {
    "Quarterstaff": "Warstaff",
    "Mace One Hand Mace": "One Hand Mace",
    "Mace Two Hand Mace": "Two Hand Mace",
    "LimitedRespawn Revives Available": "Map",
    "Tablet": "TowerAugment"
}

base_data_dir = 'Data/sorted'
base_expected_fields_dir = 'Model/expectedFields'
base_train_model_dir = 'Model/gradientBoostModel'

train_dirs = []
if TRAIN_GENERIC:
    train_dirs.append('generic')
if TRAIN_UNIQUE:
    train_dirs.append('unique')

whitelist_mode = len(whitelist) > 0
for specific_dir in train_dirs:
    dir_path = f'{base_data_dir}/{specific_dir}'
    for folder in os.listdir(dir_path):
        if whitelist_mode:
            if folder not in whitelist:
                continue
        else:
            if folder in exceptions:
                continue
        model_name = name_map.get(folder, folder)
        if IGNORE_EXISTING and os.path.exists(f'{base_train_model_dir}/{specific_dir}/{model_name}'):
            continue
        run_pipeline(
            model_name,
            f'{dir_path}/{folder}',
            f'{base_train_model_dir}/{specific_dir}',
            f'{base_expected_fields_dir}/{specific_dir}',
            skip_stats=False,
            iterations=1000,
            learning_rate=0.12,
            depth=7
        )