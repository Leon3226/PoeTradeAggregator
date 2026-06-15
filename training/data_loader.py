"""
Data loader module for loading item data from JSON files.
"""
import json
import os
import random


def load_items(data_directory: str, shuffle: bool = True) -> list:
    """
    Load items from all data files in the specified directory.

    Args:
        data_directory: Path to directory containing data-*.json files
        shuffle: Whether to shuffle the items after loading

    Returns:
        List of item dictionaries
    """
    items = []
    seen_ids = set()
    for file in os.listdir(data_directory):
        filename = os.fsdecode(file)
        if not filename.startswith('data-'):
            continue
        with open(f'{data_directory}/{filename}', encoding='utf-8') as f:
            for item in json.load(f)['result']:
                if item['id'] in seen_ids:
                    continue
                seen_ids.add(item['id'])
                items.append(item)

    if shuffle:
        random.shuffle(items)

    return items


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load item data from JSON files')
    parser.add_argument('data_directory', help='Directory containing data-*.json files')
    parser.add_argument('--no-shuffle', action='store_true', help='Do not shuffle items')
    parser.add_argument('--output', '-o', help='Output file path (JSON)')

    args = parser.parse_args()

    items = load_items(args.data_directory, shuffle=not args.no_shuffle)
    print(f'Loaded {len(items)} items')

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(items, f)
        print(f'Saved to {args.output}')
