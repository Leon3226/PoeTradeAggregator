import os

from training.pipeline import run_pipeline
from parser import initParser
from Helpers.currencyFetcher import CurrencyFetcher

initParser()
CurrencyFetcher.get_rates()

TRAIN_GENERIC = True
TRAIN_UNIQUE = False
IGNORE_EXISTING = False

whitelist = []
exceptions = [
    'Area Level',
    'Relic',
    # Waystones get mis-sorted under this name by sortRawData's extract_item_type
    'LimitedRespawn Revives Available',
]

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
        if IGNORE_EXISTING and os.path.exists(f'{base_train_model_dir}/{specific_dir}/{folder}'):
            continue
        run_pipeline(
            folder,
            f'{dir_path}/{folder}',
            f'{base_train_model_dir}/{specific_dir}',
            f'{base_expected_fields_dir}/{specific_dir}',
            iterations=1000,
            learning_rate=0.12,
            depth=7
        )