import json
import os
import uuid

RAW_DATA_DIR = 'Data/Raw'
SORTED_DATA_DIR = 'Data/sorted'
CATEGORY_GENERIC = 'generic'
CATEGORY_UNIQUE = 'unique'


def extract_item_type(item_properties: list) -> str:
    if not item_properties:
        return 'Unknown'
    name = item_properties[0].get('name', 'Unknown')
    return name.replace('[', '').replace(']', '').replace('|', ' ')


def normalize_data(data: dict) -> list:
    if 'data' in data:
        data = data['data']
    if 'result' in data:
        data = data['result']
    return data if isinstance(data, list) else []


def process_item(item_json: dict, data_to_save: dict, listings_to_delete: set) -> None:
    if 'item' not in item_json or 'rarity' not in item_json['item']:
        return

    item_data = item_json['item']
    if not item_data.get('identified', False):
        return

    name = item_data.get('name', '')
    item_rarity = item_data['rarity']
    item_type = extract_item_type(item_data.get('properties', []))

    if item_rarity != 'Unique':
        category = CATEGORY_GENERIC
        key = item_type
    else:
        category = CATEGORY_UNIQUE
        key = name

    if key not in data_to_save[category]:
        data_to_save[category][key] = []
    data_to_save[category][key].append(item_json)
    listings_to_delete.add(item_json['id'])


def load_and_sort_items(raw_dir: str) -> tuple:
    data_to_save = {CATEGORY_GENERIC: {}, CATEGORY_UNIQUE: {}}
    listings_to_delete = set()

    json_files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
    total_files = len(json_files)
    print(f'Found {total_files} files to sort')

    for idx, filename in enumerate(json_files, 1):
        file_path = os.path.join(raw_dir, filename)
        with open(file_path, encoding='utf-8') as f:
            data = normalize_data(json.load(f))
            for item in data:
                process_item(item, data_to_save, listings_to_delete)
        print(f'({idx}/{total_files}) files sorted...')

    return data_to_save, listings_to_delete


def save_category_data(base_dir: str, category: str, category_data: dict, session_id: uuid.UUID) -> None:
    category_dir = os.path.join(base_dir, category)
    os.makedirs(category_dir, exist_ok=True)

    print(f'\nSaving {category}...')
    for key, items in category_data.items():
        item_dir = os.path.join(category_dir, key)
        os.makedirs(item_dir, exist_ok=True)
        file_path = os.path.join(item_dir, f'data-{session_id}.json')

        print(f'    Saving {key}...')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'result': items}, f, ensure_ascii=False, indent=4)


def cleanup_raw_files(raw_dir: str, listings_to_delete: set) -> None:
    print('\nDeleting processed data from the raw data...')

    json_files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
    total_files = len(json_files)

    for idx, filename in enumerate(json_files, 1):
        file_path = os.path.join(raw_dir, filename)

        with open(file_path, 'r', encoding='utf-8') as f:
            data = normalize_data(json.load(f))

        new_data = [item for item in data if item['id'] not in listings_to_delete]
        old_len = len(data)
        new_len = len(new_data)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'result': new_data}, f, ensure_ascii=False, indent=4)

        print(f'({idx}/{total_files}) raw files truncated, kept {new_len}/{old_len} unsorted items...')


def main():
    session_id = uuid.uuid4()

    data_to_save, listings_to_delete = load_and_sort_items(RAW_DATA_DIR)

    print('\nSaving the data...')
    save_category_data(SORTED_DATA_DIR, CATEGORY_GENERIC, data_to_save[CATEGORY_GENERIC], session_id)
    save_category_data(SORTED_DATA_DIR, CATEGORY_UNIQUE, data_to_save[CATEGORY_UNIQUE], session_id)

    cleanup_raw_files(RAW_DATA_DIR, listings_to_delete)

    print('\nData sorting complete!')


if __name__ == "__main__":
    main()