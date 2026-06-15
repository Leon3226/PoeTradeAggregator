"""
Model saver module for saving trained models and field definitions.
"""
import os
from typing import List

from catboost import CatBoostRegressor

from field_calculator import FieldDefinitions, save_fields


def save_model(model: CatBoostRegressor, model_path: str, pool_data: List[list] = None) -> None:
    """
    Save a trained CatBoost model to disk.

    Args:
        model: Trained CatBoostRegressor model
        model_path: Path to save the model (without extension)
        pool_data: Optional training data pool for model metadata
    """
    os.makedirs(os.path.dirname(model_path) if os.path.dirname(model_path) else '.', exist_ok=True)
    model.save_model(model_path, format="cbm", pool=pool_data)
    print(f'Model saved to {model_path}')


def save_model_with_fields(model: CatBoostRegressor, fields: FieldDefinitions,
                           model_name: str, model_directory: str, fields_directory: str,
                           pool_data: List[list] = None) -> None:
    """
    Save a trained model and its associated field definitions.

    Args:
        model: Trained CatBoostRegressor model
        fields: Field definitions used for the model
        model_name: Name for the model files
        model_directory: Directory to save the model
        fields_directory: Directory to save field definitions
        pool_data: Optional training data pool for model metadata
    """
    os.makedirs(model_directory, exist_ok=True)
    os.makedirs(fields_directory, exist_ok=True)

    model_path = os.path.join(model_directory, model_name)
    fields_path = os.path.join(fields_directory, f'{model_name}.json')

    save_model(model, model_path, pool_data)
    save_fields(fields, fields_path)
    print(f'Fields saved to {fields_path}')


def load_model(model_path: str) -> CatBoostRegressor:
    """
    Load a CatBoost model from disk.

    Args:
        model_path: Path to the saved model

    Returns:
        Loaded CatBoostRegressor model
    """
    model = CatBoostRegressor()
    model.load_model(model_path)
    return model


if __name__ == '__main__':
    import argparse
    from model_trainer import TrainingResult

    parser = argparse.ArgumentParser(description='Save a trained model')
    parser.add_argument('model_path', help='Path to save the model')
    parser.add_argument('--fields', '-f', help='Path to field definitions JSON')
    parser.add_argument('--fields-output', help='Path to save field definitions')

    args = parser.parse_args()

    print('Model saver utility')
    print('This module is typically used as a library, not directly.')
    print('Use pipeline.py for the full training workflow.')
