"""
Integration Tests for the Context Engine Pipeline

Tests the complete flow:
1. Parse blueprints
2. Query Neo4j state
3. Calculate deltas
4. Assemble briefcase
5. Get Claude reasoning
6. Dispatch actions
"""

import os
import pytest
from pathlib import Path

# ASSUMPTION: Tests will be run from project root with proper environment setup

def test_environment_variables():
    """Test that required environment variables are set."""
    required_vars = [
        'NEO4J_URI',
        'NEO4J_USER',
        'NEO4J_PASSWORD',
        'ANTHROPIC_API_KEY'
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        pytest.skip(f"Missing required environment variables: {', '.join(missing)}")


def test_mock_data_files_exist():
    """Test that mock data files exist."""
    base_path = Path(__file__).parent.parent

    required_files = [
        base_path / 'data' / 'mock_blueprints' / 'before.json',
        base_path / 'data' / 'mock_blueprints' / 'after.json',
        base_path / 'data' / 'budget_state.json'
    ]

    for file_path in required_files:
        assert file_path.exists(), f"Required file not found: {file_path}"


def test_blueprint_parser():
    """Test blueprint parsing functionality."""
    from src.ingestion.parser import BlueprintParser

    parser = BlueprintParser(mock_mode=True)

    base_path = Path(__file__).parent.parent
    before_path = base_path / 'data' / 'mock_blueprints' / 'before.json'

    blueprint = parser.parse_blueprint(before_path)

    assert blueprint.blueprint_id == "BP_001_rev_A"
    assert blueprint.project_id == "proj_001"
    assert len(blueprint.assets) == 2

    # Check Wall_A properties
    wall_a = next(asset for asset in blueprint.assets if asset.id == "Wall_A")
    assert wall_a.quantity == 400
    assert wall_a.material == "Concrete"


def test_blueprint_comparison():
    """Test comparing before and after blueprints."""
    from src.ingestion.parser import BlueprintParser

    parser = BlueprintParser(mock_mode=True)

    base_path = Path(__file__).parent.parent
    before_path = base_path / 'data' / 'mock_blueprints' / 'before.json'
    after_path = base_path / 'data' / 'mock_blueprints' / 'after.json'

    before = parser.parse_blueprint(before_path)
    after = parser.parse_blueprint(after_path)

    changes = parser.compare_blueprints(before, after)

    # Should have 1 added asset (HVAC_Unit_1)
    assert changes['summary']['added_count'] == 1

    # Should have 1 modified asset (Wall_A)
    assert changes['summary']['modified_count'] == 1

    # Wall_A should show quantity change from 400 to 500
    wall_changes = next(
        item for item in changes['modified']
        if item['asset_id'] == 'Wall_A'
    )
    assert wall_changes['changes']['quantity']['before'] == 400
    assert wall_changes['changes']['quantity']['after'] == 500
    assert wall_changes['changes']['quantity']['delta'] == 100


@pytest.mark.skipif(
    not os.getenv('NEO4J_URI'),
    reason="Neo4j not configured"
)
def test_graph_connection():
    """Test Neo4j connection (requires running Neo4j instance)."""
    from src.librarian.graph_client import GraphClient
    import os

    client = GraphClient(
        uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        user=os.getenv('NEO4J_USER', 'neo4j'),
        password=os.getenv('NEO4J_PASSWORD', 'contextengine123')
    )

    assert client.health_check(), "Neo4j connection failed"
    client.close()


def test_mock_budget_api():
    """Test mock budget API functionality."""
    from src.dispatcher.budget_api import MockBudgetAPI
    import tempfile

    # Create a temporary budget file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name

    try:
        api = MockBudgetAPI(temp_file)

        # Test getting line item
        item = api.get_line_item('B47')
        assert item is not None
        assert item.code == 'B47'
        assert item.description == 'Cast-in-Place Concrete'

        # Test updating budget
        success = api.update_budget(
            code='B47',
            delta=1000.0,
            asset_id='Wall_A',
            auto_approved=True
        )
        assert success

        # Verify the update
        updated_item = api.get_line_item('B47')
        assert updated_item.spent == 31000.0  # 30000 + 1000

    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_briefcase_assembly():
    """Test briefcase assembly for Claude."""
    from src.briefcase.assembler import BriefcaseAssembler

    assembler = BriefcaseAssembler(
        approval_threshold=500.0,
        max_contingency=5000.0
    )

    # Mock delta data
    delta = {
        'exists': True,
        'object_id': 'Wall_A',
        'current_quantity': 400,
        'new_quantity': 500,
        'quantity_delta': 100,
        'current_material': 'Concrete',
        'cost_per_unit': 10.0,
        'cost_impact': 1000.0,
        'current_total_cost': 4000.0,
        'lineitem': {
            'id': 'B47',
            'code': '03-30-00',
            'description': 'Cast-in-Place Concrete',
            'allocated_budget': 50000.0,
            'spent_to_date': 30000.0,
            'remaining': 20000.0,
            'contingency': 5000.0
        },
        'vendor': {
            'name': 'ConcreteCo Inc'
        }
    }

    briefcase = assembler.assemble_asset_change(delta)

    # Verify briefcase contains key information
    assert 'Wall_A' in briefcase
    assert '400' in briefcase  # current quantity
    assert '500' in briefcase  # new quantity
    assert '1000' in briefcase  # cost impact
    assert 'B47' in briefcase  # budget code


@pytest.mark.skipif(
    not os.getenv('ANTHROPIC_API_KEY'),
    reason="Anthropic API key not configured"
)
def test_claude_client():
    """Test Claude API client (requires API key)."""
    from src.reasoner.claude_client import ClaudeClient
    import os

    client = ClaudeClient(
        api_key=os.getenv('ANTHROPIC_API_KEY'),
        model='claude-sonnet-4-20250514'
    )

    # Simple validation test
    assert client.validate_api_key(), "Claude API key validation failed"


def test_action_dispatcher():
    """Test action dispatcher."""
    from src.dispatcher.actions import ActionDispatcher
    from src.dispatcher.budget_api import MockBudgetAPI
    import tempfile

    # Create temporary budget file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name

    try:
        api = MockBudgetAPI(temp_file)
        dispatcher = ActionDispatcher(
            budget_api=api,
            min_confidence_for_auto_approval=0.85
        )

        # Test auto-approval with high confidence
        recommendation = {
            'action_type': 'update_budget',
            'requires_human': False,
            'confidence_score': 0.95,
            'reasoning': 'Quantity increase is within normal parameters'
        }

        result = dispatcher.dispatch(
            recommendation=recommendation,
            asset_id='Wall_A',
            budget_code='B47',
            cost_impact=1000.0
        )

        assert result['success']
        assert 'auto' in result['message'].lower()

        # Test flagging for approval with low confidence
        recommendation_low = {
            'action_type': 'update_budget',
            'requires_human': False,
            'confidence_score': 0.70,
            'reasoning': 'Uncertain about quantity change'
        }

        result = dispatcher.dispatch(
            recommendation=recommendation_low,
            asset_id='Wall_B',
            budget_code='B47',
            cost_impact=2000.0
        )

        assert result['requires_human']

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
