"""
Field calculator module for discovering possible modifiers, properties, and stats from items.
"""
import json
from dataclasses import dataclass, field
from typing import Set, List


@dataclass
class FieldDefinitions:
    """Container for all discovered field definitions."""
    properties: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    stats: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'properties': self.properties,
            'modifiers': self.modifiers,
            'stats': self.stats
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FieldDefinitions':
        return cls(
            properties=data.get('properties', []),
            modifiers=data.get('modifiers', []),
            stats=data.get('stats', [])
        )


def get_mod_string(stats: list) -> str:
    """Create a sorted, comma-separated string from stat identifiers."""
    stats_copy = stats.copy()
    stats_copy.sort()
    return ','.join(stats_copy)


def get_stat_strings(mod: dict) -> list:
    """Extract unique stat hash strings from a modifier's magnitudes."""
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


def calculate_fields(items: list) -> FieldDefinitions:
    """
    Scan all items to discover possible modifiers, properties, and stats.

    Args:
        items: List of item dictionaries

    Returns:
        FieldDefinitions containing sorted lists of all discovered fields
    """
    possible_properties: Set[str] = set()
    possible_modifiers: Set[str] = set()
    possible_stats: Set[str] = set()

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

    return FieldDefinitions(
        properties=sorted(possible_properties),
        modifiers=sorted(possible_modifiers),
        stats=sorted(possible_stats)
    )


def save_fields(fields: FieldDefinitions, output_path: str):
    """Save field definitions to a JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(fields.to_dict(), f, ensure_ascii=False, indent=4)


def load_fields(input_path: str) -> FieldDefinitions:
    """Load field definitions from a JSON file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        return FieldDefinitions.from_dict(json.load(f))


if __name__ == '__main__':
    import argparse
    from data_loader import load_items

    parser = argparse.ArgumentParser(description='Calculate possible fields from item data')
    parser.add_argument('data_directory', help='Directory containing data-*.json files')
    parser.add_argument('--output', '-o', required=True, help='Output file path for field definitions (JSON)')

    args = parser.parse_args()

    print('Loading items...')
    items = load_items(args.data_directory, shuffle=False)
    print(f'Loaded {len(items)} items')

    print('Calculating fields...')
    fields = calculate_fields(items)

    print(f'Found {len(fields.properties)} properties')
    print(f'Found {len(fields.modifiers)} modifiers')
    print(f'Found {len(fields.stats)} stats')

    save_fields(fields, args.output)
    print(f'Saved fields to {args.output}')
