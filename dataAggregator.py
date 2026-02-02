import json
import os

DATA_CATEGORIES = ['generic', 'unique']
EXPECTED_FIELDS_DIR = 'Model/expectedFields'
OUTPUT_FILE = 'item-vector-data.json'


def load_category_data(category: str) -> dict:
    category_path = os.path.join(EXPECTED_FIELDS_DIR, category)
    category_data = {}

    for filename in os.listdir(category_path):
        if not filename.endswith('.json'):
            print(f'{filename} is not a json file, skipping...')
            continue

        file_path = os.path.join(category_path, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        model_name = filename.rsplit('.', 1)[0]
        category_data[model_name] = data

    return category_data


def aggregate_data() -> dict:
    return {category: load_category_data(category) for category in DATA_CATEGORIES}


def main():
    aggregated_data = aggregate_data()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(aggregated_data, f, ensure_ascii=False, indent=4)

    print(f'Successfully aggregated data into {OUTPUT_FILE}')


if __name__ == "__main__":
    main()