"""
Optional, decoupled extraction of exact rolled modifier values from item mod text.

Why this exists:
  `mod['tier']` is always empty for Unique items, and a unique's mod *pool* is fixed,
  so mod_*_present/_tier/_fract/_desecrated are identical across every instance of a
  given unique. The only signal that distinguishes a perfect roll from a garbage roll
  is the actual rolled number embedded in explicitMods/implicitMods text (e.g.
  "+125 to all Attributes" vs "+86 to all Attributes") - magnitudes.min/max is a
  static reference range for the affix, not the per-item roll.

This module parses that text via parser.parseMod() / Data/stats.ndjson and produces
stat_{hash}_value entries matching the slots already allocated by
field_calculator.get_empty_vector(). It is intentionally kept separate from
vector_transformer.py and is only invoked when skip_stats=False, so it can be
disabled or reworked without touching the rest of the transform pipeline.
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parser as mod_parser
from field_calculator import FieldDefinitions

MOD_CATEGORY_TO_STAT_TYPE = {
    'explicitMods': 'explicit',
    'implicitMods': 'implicit',
    # field_calculator.get_stat_strings() normalizes fractured/desecrated hashes to
    # 'explicit.*', so they must be looked up under the 'explicit' stat type too.
    'fracturedMods': 'explicit',
    'desecratedMods': 'explicit',
}

_NUMBER_RE = re.compile(r'[+-]?\d+(?:\.\d+)?')

# Caches which compiled matcher/record matches a given (stat_type, normalized template)
# so repeat affixes (the common case) skip the linear scan over Data/stats.ndjson matchers.
_template_cache = {}


def keep_right(text: str) -> str:
    """Extract the rightmost value from bracketed alternatives."""
    return re.sub(r'\s+', ' ', re.sub(r'\[([^\]]+)\]', lambda m: m.group(1).split('|')[-1], text)).strip()


def _normalize_template(stat_type: str, cleaned_text: str) -> str:
    return f'{stat_type}|{_NUMBER_RE.sub("#", cleaned_text)}'


def _find_match(stat_type: str, cleaned_text: str):
    """
    Return (parse_result_tuple, matching_data_row) for cleaned_text, or None.
    Caches the resolved matcher per normalized template to avoid re-scanning
    Data/stats.ndjson's ~3000 matchers for every mod on every item.
    """
    if not mod_parser.matchers:
        mod_parser.initParser()

    template_key = _normalize_template(stat_type, cleaned_text)
    cached = _template_cache.get(template_key, False)
    if cached is not False:
        if cached is None:
            return None
        result = cached['matcher'].parse(cleaned_text)
        if result is None:
            return None
        return result.fixed, mod_parser.records['values'].values[cached['recordIndex']]

    for matcher in mod_parser.matchers:
        result = matcher['matcher'].parse(cleaned_text)
        if result is not None:
            _template_cache[template_key] = matcher
            return result.fixed, mod_parser.records['values'].values[matcher['recordIndex']]

    _template_cache[template_key] = None
    return None


def extract_stat_values(item: dict, fields: FieldDefinitions) -> dict:
    """
    Extract rolled numeric values from an item's mod text.

    Returns a dict of {'stat_{hash}_value': number} for stats present in
    fields.stats, ready to be added into a feature vector produced by
    get_empty_vector(). Mods that can't be parsed, or whose stat isn't in
    fields.stats, are silently skipped.
    """
    result = {}
    item_data = item['item']

    for mod_category, stat_type in MOD_CATEGORY_TO_STAT_TYPE.items():
        mod_texts = item_data.get(mod_category)
        if not mod_texts:
            continue

        for mod_text in mod_texts:
            match = _find_match(stat_type, keep_right(mod_text))
            if match is None:
                continue

            parse_result, matching_data = match
            if not parse_result:
                # No numeric component (e.g. "Life Recovery from Flasks is instant") -
                # use the 'better' flag as a presence indicator.
                numeric_value = matching_data[1]
            elif len(parse_result) == 1:
                numeric_value = parse_result[0]
            else:
                numeric_value = sum(parse_result) / len(parse_result)

            trade_ids = matching_data[3]['ids']
            if stat_type not in trade_ids:
                continue

            for candidate_hash in trade_ids[stat_type]:
                if candidate_hash not in fields.stats:
                    continue
                stat_key = f'stat_{candidate_hash}_value'
                result[stat_key] = result.get(stat_key, 0) + numeric_value
                break

    return result
