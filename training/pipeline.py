"""
Training pipeline that orchestrates all training steps.

This script combines:
1. Loading item data
2. Calculating possible fields
3. Transforming items to vectors
4. Training the model
5. Saving the model and fields
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_items
from field_calculator import calculate_fields, load_fields, save_fields
from vector_transformer import transform_items
from model_trainer import train_model, evaluate_model, TrainingConfig
from model_saver import save_model_with_fields


def run_pipeline(
    model_name: str,
    data_directory: str,
    model_save_directory: str,
    fields_save_directory: str,
    iterations: int = 1500,
    learning_rate: float = 0.15,
    depth: int = 6,
    eval_ratio: float = 0.1,
    skip_stats: bool = True,
    fields_path: str = None,
    loss_function: str = 'Huber:delta=0.7',
    eval_metric: str = 'MAE',
    early_stopping_rounds: int = 100
):
    """
    Run the complete training pipeline.

    Args:
        model_name: Name for the output model
        data_directory: Directory containing data-*.json files
        model_save_directory: Directory to save the trained model
        fields_save_directory: Directory to save field definitions
        iterations: Number of training iterations
        learning_rate: Model learning rate
        depth: Tree depth
        eval_ratio: Ratio of data for evaluation
        skip_stats: Whether to skip parsing stat text values
        fields_path: Optional path to pre-calculated fields JSON
        loss_function: CatBoost loss function
        eval_metric: CatBoost eval metric used for early stopping
        early_stopping_rounds: Number of rounds without improvement before stopping
    """
    print(f"Starting training pipeline for '{model_name}'")
    print('=' * 60)

    # Step 1: Load items
    print('\n[1/5] Loading items...')
    items = load_items(data_directory)
    print(f'      Loaded {len(items)} items')

    # Step 2: Calculate or load fields
    print('\n[2/5] Processing fields...')
    if fields_path:
        print(f'      Loading fields from {fields_path}')
        fields = load_fields(fields_path)
    else:
        print('      Calculating fields from items...')
        fields = calculate_fields(items)
    print(f'      Found {len(fields.properties)} properties')
    print(f'      Found {len(fields.modifiers)} modifiers')
    print(f'      Found {len(fields.stats)} stats')

    # Step 3: Transform items to vectors
    print('\n[3/5] Transforming items to vectors...')
    vectors, prices = transform_items(items, fields, skip_stats=skip_stats)
    print(f'      Created {len(vectors)} vectors')

    # Step 4: Train model
    print('\n[4/5] Training model...')
    config = TrainingConfig(
        iterations=iterations,
        learning_rate=learning_rate,
        depth=depth,
        eval_set_ratio=eval_ratio,
        loss_function=loss_function,
        eval_metric=eval_metric,
        early_stopping_rounds=early_stopping_rounds
    )
    result = train_model(vectors, prices, config)
    evaluate_model(result)

    # Step 5: Save model and fields
    print('\n[5/5] Saving model and fields...')
    save_model_with_fields(
        model=result.model,
        fields=fields,
        model_name=model_name,
        model_directory=model_save_directory,
        fields_directory=fields_save_directory,
        pool_data=result.train_vectors
    )

    print('\n' + '=' * 60)
    print(f"Pipeline completed successfully for '{model_name}'")


def main():
    parser = argparse.ArgumentParser(
        description='Run the complete training pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py my_model ./data ./models ./fields
  python pipeline.py my_model ./data ./models ./fields --iterations 2000 --depth 8
  python pipeline.py my_model ./data ./models ./fields --fields ./existing_fields.json
        """
    )

    parser.add_argument('model_name', help='Name for the output model')
    parser.add_argument('data_directory', help='Directory containing data-*.json files')
    parser.add_argument('model_save_directory', help='Directory to save the trained model')
    parser.add_argument('fields_save_directory', help='Directory to save field definitions')

    parser.add_argument('--iterations', type=int, default=1500,
                        help='Number of training iterations (default: 1500)')
    parser.add_argument('--learning-rate', type=float, default=0.15,
                        help='Learning rate (default: 0.15)')
    parser.add_argument('--depth', type=int, default=6,
                        help='Tree depth (default: 6)')
    parser.add_argument('--eval-ratio', type=float, default=0.1,
                        help='Evaluation set ratio (default: 0.1)')
    parser.add_argument('--include-stats', action='store_true',
                        help='Include parsed stat values (slower)')
    parser.add_argument('--fields', help='Path to pre-calculated fields JSON')
    parser.add_argument('--loss-function', default='Huber:delta=0.7',
                        help='CatBoost loss function (default: Huber:delta=0.7)')
    parser.add_argument('--eval-metric', default='MAE',
                        help='CatBoost eval metric used for early stopping (default: MAE)')
    parser.add_argument('--early-stopping-rounds', type=int, default=100,
                        help='Early stopping rounds (default: 100)')

    args = parser.parse_args()

    run_pipeline(
        model_name=args.model_name,
        data_directory=args.data_directory,
        model_save_directory=args.model_save_directory,
        fields_save_directory=args.fields_save_directory,
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        depth=args.depth,
        eval_ratio=args.eval_ratio,
        skip_stats=not args.include_stats,
        fields_path=args.fields,
        loss_function=args.loss_function,
        eval_metric=args.eval_metric,
        early_stopping_rounds=args.early_stopping_rounds
    )


if __name__ == '__main__':
    main()
