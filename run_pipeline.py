#!/usr/bin/env python3
"""
Context Engine MVP - Main Pipeline Script

Demonstrates the complete Blue-to-Budget reconciliation pipeline:
1. Parse blueprints (before and after)
2. Compare for changes
3. Query Neo4j for current state
4. Calculate deltas
5. Assemble briefcase for Claude
6. Get Claude's reasoning
7. Dispatch actions

Usage:
    python run_pipeline.py
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

from src.ingestion.parser import BlueprintParser
from src.librarian.graph_client import GraphClient
from src.librarian.state_queries import StateQueries
from src.briefcase.assembler import BriefcaseAssembler
from src.reasoner.claude_client import ClaudeClient
from src.dispatcher.actions import ActionDispatcher
from src.dispatcher.budget_api import MockBudgetAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_environment() -> Dict[str, Any]:
    """
    Load and validate environment configuration.

    Returns:
        Dictionary with configuration values

    Raises:
        RuntimeError: If required environment variables are missing
    """
    load_dotenv()

    required_vars = [
        'NEO4J_URI',
        'NEO4J_USER',
        'NEO4J_PASSWORD',
        'ANTHROPIC_API_KEY'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please copy .env.example to .env and fill in the values."
        )

    config = {
        'neo4j_uri': os.getenv('NEO4J_URI'),
        'neo4j_user': os.getenv('NEO4J_USER'),
        'neo4j_password': os.getenv('NEO4J_PASSWORD'),
        'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
        'anthropic_model': os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514'),
        'budget_file': os.getenv('BUDGET_API_FILE', './data/budget_state.json'),
        'approval_threshold': float(os.getenv('APPROVAL_THRESHOLD', '500.0')),
        'max_contingency': float(os.getenv('MAX_CONTINGENCY', '5000.0')),
        'min_confidence': float(os.getenv('MIN_CONFIDENCE_THRESHOLD', '0.85'))
    }

    return config


def print_separator(title: str = "") -> None:
    """Print a formatted separator line."""
    if title:
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    else:
        print(f"{'='*70}")


def main():
    """Run the complete pipeline."""
    print_separator("CONTEXT ENGINE MVP - Blue-to-Budget Pipeline")

    try:
        # 1. Setup
        print("Step 1: Loading configuration...")
        config = setup_environment()
        logger.info("Configuration loaded successfully")

        # 2. Initialize components
        print("\nStep 2: Initializing components...")

        parser = BlueprintParser(mock_mode=True)
        logger.info("✓ BlueprintParser initialized")

        graph_client = GraphClient(
            uri=config['neo4j_uri'],
            user=config['neo4j_user'],
            password=config['neo4j_password']
        )
        logger.info("✓ Neo4j connection established")

        # Test connection
        if not graph_client.health_check():
            raise RuntimeError("Neo4j health check failed")

        state_queries = StateQueries(graph_client)
        logger.info("✓ StateQueries initialized")

        assembler = BriefcaseAssembler(
            approval_threshold=config['approval_threshold'],
            max_contingency=config['max_contingency'],
            min_confidence_threshold=config['min_confidence']
        )
        logger.info("✓ BriefcaseAssembler initialized")

        claude = ClaudeClient(
            api_key=config['anthropic_api_key'],
            model=config['anthropic_model']
        )
        logger.info("✓ ClaudeClient initialized")

        budget_api = MockBudgetAPI(config['budget_file'])
        logger.info("✓ MockBudgetAPI initialized")

        dispatcher = ActionDispatcher(
            budget_api=budget_api,
            min_confidence_for_auto_approval=config['min_confidence']
        )
        logger.info("✓ ActionDispatcher initialized")

        # 3. Parse blueprints
        print_separator("Step 3: Parsing Blueprints")

        base_path = Path(__file__).parent
        before_path = base_path / 'data' / 'mock_blueprints' / 'before.json'
        after_path = base_path / 'data' / 'mock_blueprints' / 'after.json'

        print(f"Loading: {before_path}")
        before = parser.parse_blueprint(before_path)
        print(f"✓ Before blueprint loaded: {before.blueprint_id}")
        print(f"  Revision: {before.revision}, Date: {before.date}")
        print(f"  Assets: {len(before.assets)}")

        print(f"\nLoading: {after_path}")
        after = parser.parse_blueprint(after_path)
        print(f"✓ After blueprint loaded: {after.blueprint_id}")
        print(f"  Revision: {after.revision}, Date: {after.date}")
        print(f"  Assets: {len(after.assets)}")

        # 4. Compare blueprints
        print_separator("Step 4: Comparing Blueprints")

        changes = parser.compare_blueprints(before, after)

        print(f"Change Summary:")
        print(f"  Added:    {changes['summary']['added_count']} assets")
        print(f"  Removed:  {changes['summary']['removed_count']} assets")
        print(f"  Modified: {changes['summary']['modified_count']} assets")

        # 5. Process changes
        print_separator("Step 5: Processing Changes")

        results = []

        # Process modified assets
        for change in changes['modified']:
            asset_id = change['asset_id']
            before_asset = change['before']
            after_asset = change['after']

            print(f"\n[MODIFIED] {asset_id}")
            print(f"  Before: {before_asset.quantity} {before_asset.unit}")
            print(f"  After:  {after_asset.quantity} {after_asset.unit}")
            print(f"  Delta:  {change['changes']['quantity']['delta']:+.2f} {after_asset.unit}")

            # Calculate delta from graph
            print(f"  Querying Neo4j for current state...")
            delta = state_queries.calculate_delta(
                object_id=asset_id,
                new_quantity=after_asset.quantity
            )

            if not delta['exists']:
                print(f"  ⚠ Asset not found in graph database")
                continue

            print(f"  Cost Impact: ${delta['cost_impact']:+,.2f}")

            # Assemble briefcase
            print(f"  Assembling briefcase for Claude...")
            briefcase = assembler.assemble_asset_change(delta)

            # Get Claude's recommendation
            print(f"  Requesting Claude's reasoning...")
            recommendation = claude.reason_about_change(
                briefcase,
                assembler.get_function_definition()
            )

            print(f"  ✓ Recommendation: {recommendation['action_type']}")
            print(f"    Requires Human: {recommendation['requires_human']}")
            print(f"    Confidence: {recommendation['confidence_score']:.2f}")
            print(f"    Reasoning: {recommendation['reasoning'][:100]}...")

            # Dispatch action
            print(f"  Dispatching action...")
            result = dispatcher.dispatch(
                recommendation=recommendation,
                asset_id=asset_id,
                budget_code=delta['lineitem']['id'],
                cost_impact=delta['cost_impact']
            )

            print(f"  ✓ {result['message']}")

            results.append({
                'asset_id': asset_id,
                'change_type': 'modified',
                'delta': delta,
                'recommendation': recommendation,
                'dispatch_result': result
            })

        # Process added assets
        for added_asset_dict in changes['added']:
            asset_id = added_asset_dict['id']

            print(f"\n[ADDED] {asset_id}")
            print(f"  Type: {added_asset_dict['type']}")
            print(f"  Material: {added_asset_dict['material']}")
            print(f"  Quantity: {added_asset_dict['quantity']} {added_asset_dict['unit']}")

            # Assemble briefcase for new asset
            print(f"  Assembling briefcase for Claude...")
            briefcase = assembler.assemble_new_asset(
                asset_data={
                    'object_id': asset_id,
                    'type': added_asset_dict['type'],
                    'material': added_asset_dict['material'],
                    'quantity': added_asset_dict['quantity'],
                    'unit': added_asset_dict['unit'],
                    'floor': added_asset_dict['floor']
                }
            )

            # Get Claude's recommendation
            print(f"  Requesting Claude's reasoning...")
            recommendation = claude.reason_about_change(
                briefcase,
                assembler.get_function_definition()
            )

            print(f"  ✓ Recommendation: {recommendation['action_type']}")
            print(f"    Reasoning: {recommendation['reasoning'][:100]}...")

            results.append({
                'asset_id': asset_id,
                'change_type': 'added',
                'recommendation': recommendation
            })

        # 6. Summary
        print_separator("Step 6: Pipeline Summary")

        print(f"Processed {len(results)} changes")

        auto_approved = sum(
            1 for r in results
            if r.get('dispatch_result', {}).get('success')
            and not r.get('dispatch_result', {}).get('requires_human')
        )
        flagged = sum(
            1 for r in results
            if r.get('dispatch_result', {}).get('requires_human', True)
        )

        print(f"  Auto-approved: {auto_approved}")
        print(f"  Flagged for approval: {flagged}")

        # Show budget summary
        print("\nBudget Summary:")
        summary = budget_api.get_budget_summary()
        print(f"  Total Allocated: ${summary['total_allocated']:,.2f}")
        print(f"  Total Spent: ${summary['total_spent']:,.2f}")
        print(f"  Total Remaining: ${summary['total_remaining']:,.2f}")
        print(f"  Pending Approvals: {summary['pending_approval_count']}")

        # Show pending approvals if any
        if summary['pending_approval_count'] > 0:
            print("\nPending Approvals:")
            pending = budget_api.get_pending_approvals()
            for item in pending:
                print(f"  - {item['budget_code']}: {item['asset_id']} "
                      f"(${item['delta']:+,.2f})")
                if item.get('reasoning'):
                    print(f"    Reason: {item['reasoning'][:80]}...")

        print_separator("Pipeline Complete")
        print("✓ All changes processed successfully!")

        # Cleanup
        graph_client.close()

        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
