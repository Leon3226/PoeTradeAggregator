"""
Model trainer module for training CatBoost regression models.
"""
from typing import List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
from catboost import Pool, CatBoostRegressor

EVAL_SET_RATIO = 0.1


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    iterations: int = 1500
    learning_rate: float = 0.15
    depth: int = 6
    eval_set_ratio: float = 0.1
    cat_features: List[int] = None
    use_best_model: bool = True
    early_stopping_rounds: Optional[int] = 100
    loss_function: str = 'Huber:delta=0.7'
    eval_metric: Optional[str] = 'MAE'

    def __post_init__(self):
        if self.cat_features is None:
            self.cat_features = [0, 1]  # baseType and rarity


@dataclass
class TrainingResult:
    """Result of model training."""
    model: CatBoostRegressor
    train_vectors: List[list]
    train_prices: List[float]
    eval_vectors: Optional[List[list]] = None
    eval_prices: Optional[List[float]] = None
    predictions: Optional[np.ndarray] = None


def split_data(vectors: List[list], prices: List[float], eval_ratio: float) -> Tuple:
    """
    Split data into training and evaluation sets.

    Args:
        vectors: Feature vectors
        prices: Target prices
        eval_ratio: Ratio of data to use for evaluation

    Returns:
        Tuple of (train_vectors, train_prices, eval_vectors, eval_prices)
    """
    eval_set_size = int(len(vectors) * eval_ratio)

    if eval_set_size > 0:
        train_vectors = vectors[:-eval_set_size]
        train_prices = prices[:-eval_set_size]
        eval_vectors = vectors[-eval_set_size:]
        eval_prices = prices[-eval_set_size:]
    else:
        train_vectors = vectors
        train_prices = prices
        eval_vectors = []
        eval_prices = []

    return train_vectors, train_prices, eval_vectors, eval_prices


def train_model(vectors: List[list], prices: List[float], config: TrainingConfig = None) -> TrainingResult:
    """
    Train a CatBoost regression model.

    Args:
        vectors: Feature vectors for training
        prices: Target prices (log-transformed)
        config: Training configuration

    Returns:
        TrainingResult containing the trained model and data splits
    """
    if config is None:
        config = TrainingConfig()

    train_vectors, train_prices, eval_vectors, eval_prices = split_data(
        vectors, prices, config.eval_set_ratio
    )

    model = CatBoostRegressor(
        iterations=config.iterations,
        learning_rate=config.learning_rate,
        depth=config.depth,
        loss_function=config.loss_function,
        eval_metric=config.eval_metric
    )

    predictions = None
    if eval_vectors:
        eval_dataset = Pool(eval_vectors, eval_prices, cat_features=config.cat_features)
        model.fit(
            train_vectors, train_prices, cat_features=config.cat_features,
            eval_set=eval_dataset,
            use_best_model=config.use_best_model,
            early_stopping_rounds=config.early_stopping_rounds
        )
        predictions = model.predict(eval_vectors)
    else:
        model.fit(train_vectors, train_prices, cat_features=config.cat_features)

    return TrainingResult(
        model=model,
        train_vectors=train_vectors,
        train_prices=train_prices,
        eval_vectors=eval_vectors if eval_vectors else None,
        eval_prices=eval_prices if eval_prices else None,
        predictions=predictions
    )


def evaluate_model(result: TrainingResult) -> None:
    """
    Print evaluation metrics for the trained model.

    Args:
        result: TrainingResult from train_model
    """
    if result.predictions is None or result.eval_prices is None:
        print('No evaluation data available')
        return

    print('\nEvaluation Results:')
    print('-' * 60)
    for i in range(len(result.predictions)):
        actual = np.expm1(result.eval_prices[i])
        predicted = np.expm1(result.predictions[i])
        diff = np.abs(float(result.eval_prices[i]) - result.predictions[i])
        rarity = result.eval_vectors[i][1] if result.eval_vectors else 'unknown'
        print(f'{i:>4}. [{actual:<8.1f} {predicted:<12.1f}] ({diff:>12.1f}) [{rarity}]')
    print()


if __name__ == '__main__':
    import argparse
    import json
    from data_loader import load_items
    from field_calculator import calculate_fields, load_fields
    from vector_transformer import transform_items

    parser = argparse.ArgumentParser(description='Train a CatBoost model')
    parser.add_argument('data_directory', help='Directory containing data-*.json files')
    parser.add_argument('--fields', '-f', help='Path to pre-calculated fields JSON')
    parser.add_argument('--iterations', type=int, default=1500, help='Number of training iterations')
    parser.add_argument('--learning-rate', type=float, default=0.15, help='Learning rate')
    parser.add_argument('--depth', type=int, default=6, help='Tree depth')
    parser.add_argument('--eval-ratio', type=float, default=0.1, help='Evaluation set ratio')
    parser.add_argument('--loss-function', default='Huber:delta=0.7', help='CatBoost loss function (default: Huber:delta=0.7)')
    parser.add_argument('--eval-metric', default='MAE', help='CatBoost eval metric used for early stopping (default: MAE)')
    parser.add_argument('--early-stopping-rounds', type=int, default=100, help='Early stopping rounds (default: 100)')
    parser.add_argument('--output', '-o', help='Output model file path')

    args = parser.parse_args()

    print('Loading items...')
    items = load_items(args.data_directory)
    print(f'Loaded {len(items)} items')

    if args.fields:
        fields = load_fields(args.fields)
    else:
        print('Calculating fields...')
        fields = calculate_fields(items)

    print('Transforming items...')
    vectors, prices = transform_items(items, fields)

    config = TrainingConfig(
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        depth=args.depth,
        eval_set_ratio=args.eval_ratio,
        use_best_model=True,
        early_stopping_rounds=args.early_stopping_rounds,
        loss_function=args.loss_function,
        eval_metric=args.eval_metric
    )

    print('Training model...')
    result = train_model(vectors, prices, config)
    evaluate_model(result)

    if args.output:
        result.model.save_model(args.output, format="cbm", pool=result.train_vectors)
        print(f'Model saved to {args.output}')
