"""
Training package for PoeTradeAggregator.

This package provides modular components for training price prediction models:
- data_loader: Load item data from JSON files
- field_calculator: Calculate possible fields from item data
- vector_transformer: Transform items to feature vectors
- model_trainer: Train CatBoost regression models
- model_saver: Save models and field definitions
- pipeline: Orchestrate the complete training workflow
"""

import os
import sys

# Submodules import each other and the project root (Helpers/, parser.py) via
# bare imports, so both this package's directory and the project root need to
# be on sys.path before those submodules are loaded.
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_PACKAGE_DIR)
for _path in (_PACKAGE_DIR, _PROJECT_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from .data_loader import load_items
from .field_calculator import (
    FieldDefinitions,
    calculate_fields,
    save_fields,
    load_fields,
    get_mod_string,
    get_stat_strings
)
from .vector_transformer import (
    transform_items,
    transform_item,
    get_empty_vector
)
from .model_trainer import (
    TrainingConfig,
    TrainingResult,
    train_model,
    evaluate_model,
    split_data
)
from .model_saver import (
    save_model,
    save_model_with_fields,
    load_model
)
from .pipeline import run_pipeline

__all__ = [
    'load_items',
    'FieldDefinitions',
    'calculate_fields',
    'save_fields',
    'load_fields',
    'get_mod_string',
    'get_stat_strings',
    'transform_items',
    'transform_item',
    'get_empty_vector',
    'TrainingConfig',
    'TrainingResult',
    'train_model',
    'evaluate_model',
    'split_data',
    'save_model',
    'save_model_with_fields',
    'load_model',
    'run_pipeline'
]
