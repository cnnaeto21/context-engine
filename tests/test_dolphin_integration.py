"""
Test Dolphin Integration

Tests for Dolphin-v2 parser integration, including table-to-asset mapping
and confidence propagation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.ingestion.parser import BlueprintParser, DolphinClient, BlueprintAsset


class TestDolphinClient:
    """Test DolphinClient table-to-asset mapping."""

    def test_table_to_assets_basic(self):
        """Test basic table parsing with standard columns."""
        client = DolphinClient(api_url="http://localhost:8001")

        # Mock table element from Dolphin
        table_element = {
            'type': 'table',
            'bbox': {'x1': 100, 'y1': 150, 'x2': 700, 'y2': 400},
            'content': {
                'rows': 3,
                'cols': 5,
                'cells': [
                    # Header row
                    {'row': 0, 'col': 0, 'text': 'Asset ID', 'confidence': 0.95},
                    {'row': 0, 'col': 1, 'text': 'Type', 'confidence': 0.94},
                    {'row': 0, 'col': 2, 'text': 'Material', 'confidence': 0.93},
                    {'row': 0, 'col': 3, 'text': 'Quantity', 'confidence': 0.96},
                    {'row': 0, 'col': 4, 'text': 'Unit', 'confidence': 0.95},
                    # Data row 1
                    {'row': 1, 'col': 0, 'text': 'Wall_A', 'confidence': 0.91},
                    {'row': 1, 'col': 1, 'text': 'Wall', 'confidence': 0.93},
                    {'row': 1, 'col': 2, 'text': 'Concrete', 'confidence': 0.89},
                    {'row': 1, 'col': 3, 'text': '500', 'confidence': 0.92},
                    {'row': 1, 'col': 4, 'text': 'sqft', 'confidence': 0.94},
                    # Data row 2
                    {'row': 2, 'col': 0, 'text': 'Beam_B1', 'confidence': 0.88},
                    {'row': 2, 'col': 1, 'text': 'Beam', 'confidence': 0.90},
                    {'row': 2, 'col': 2, 'text': 'Steel', 'confidence': 0.87},
                    {'row': 2, 'col': 3, 'text': '120', 'confidence': 0.91},
                    {'row': 2, 'col': 4, 'text': 'linear_ft', 'confidence': 0.93},
                ],
                'markdown': '| Asset ID | Type | Material | Quantity | Unit |\n...',
                'confidence': 0.91
            },
            'confidence': 0.91
        }

        # Parse table to assets
        assets = client.table_to_assets(
            table_element,
            blueprint_id="test_blueprint",
            floor_id="Floor_2"
        )

        # Assertions
        assert len(assets) == 2
        assert assets[0].id == 'Wall_A'
        assert assets[0].type == 'Wall'
        assert assets[0].material == 'Concrete'
        assert assets[0].quantity == 500.0
        assert assets[0].unit == 'sqft'
        assert assets[0].floor == 'Floor_2'
        assert 0.85 <= assets[0].confidence_score <= 1.0

        assert assets[1].id == 'Beam_B1'
        assert assets[1].type == 'Beam'
        assert assets[1].material == 'Steel'
        assert assets[1].quantity == 120.0
        assert assets[1].unit == 'linear_ft'

    def test_table_to_assets_with_money(self):
        """Test table parsing with currency values."""
        client = DolphinClient(api_url="http://localhost:8001")

        # Mock table with cost column
        table_element = {
            'type': 'table',
            'content': {
                'rows': 2,
                'cols': 6,
                'cells': [
                    # Header
                    {'row': 0, 'col': 0, 'text': 'Mark', 'confidence': 0.95},
                    {'row': 0, 'col': 1, 'text': 'Type', 'confidence': 0.94},
                    {'row': 0, 'col': 2, 'text': 'Material', 'confidence': 0.93},
                    {'row': 0, 'col': 3, 'text': 'Quantity', 'confidence': 0.96},
                    {'row': 0, 'col': 4, 'text': 'Unit', 'confidence': 0.95},
                    {'row': 0, 'col': 5, 'text': 'Cost', 'confidence': 0.94},
                    # Data
                    {'row': 1, 'col': 0, 'text': 'D1', 'confidence': 0.92},
                    {'row': 1, 'col': 1, 'text': 'Door', 'confidence': 0.91},
                    {'row': 1, 'col': 2, 'text': 'Wood', 'confidence': 0.90},
                    {'row': 1, 'col': 3, 'text': '$2,500', 'confidence': 0.89},
                    {'row': 1, 'col': 4, 'text': 'each', 'confidence': 0.93},
                    {'row': 1, 'col': 5, 'text': '$2,500', 'confidence': 0.88},
                ],
                'confidence': 0.90
            },
            'confidence': 0.90
        }

        assets = client.table_to_assets(
            table_element,
            blueprint_id="test_blueprint",
            floor_id="Floor_1"
        )

        # Should parse $2,500 as 2500.0
        assert len(assets) == 1
        assert assets[0].id == 'D1'
        assert assets[0].quantity == 2500.0  # $ and comma stripped

    def test_table_to_assets_empty_table(self):
        """Test handling of empty table."""
        client = DolphinClient(api_url="http://localhost:8001")

        table_element = {
            'type': 'table',
            'content': {
                'cells': [],
                'confidence': 0.0
            },
            'confidence': 0.0
        }

        assets = client.table_to_assets(
            table_element,
            blueprint_id="test_blueprint"
        )

        assert len(assets) == 0


class TestBlueprintParserDolphinMode:
    """Test BlueprintParser with Dolphin mode."""

    @patch('src.ingestion.parser.requests.post')
    def test_parse_with_dolphin_mock_response(self, mock_post):
        """Test parsing with mocked Dolphin API response."""
        # Mock Dolphin API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'layout_elements': [
                {
                    'type': 'table',
                    'bbox': {'x1': 100, 'y1': 150, 'x2': 700, 'y2': 400},
                    'confidence': 0.92
                }
            ],
            'parsed_elements': [
                {
                    'type': 'table',
                    'bbox': {'x1': 100, 'y1': 150, 'x2': 700, 'y2': 400},
                    'content': {
                        'rows': 2,
                        'cols': 5,
                        'cells': [
                            {'row': 0, 'col': 0, 'text': 'Asset ID', 'confidence': 0.95},
                            {'row': 0, 'col': 1, 'text': 'Type', 'confidence': 0.94},
                            {'row': 0, 'col': 2, 'text': 'Material', 'confidence': 0.93},
                            {'row': 0, 'col': 3, 'text': 'Quantity', 'confidence': 0.96},
                            {'row': 0, 'col': 4, 'text': 'Unit', 'confidence': 0.95},
                            {'row': 1, 'col': 0, 'text': 'HVAC_1', 'confidence': 0.91},
                            {'row': 1, 'col': 1, 'text': 'HVAC', 'confidence': 0.93},
                            {'row': 1, 'col': 2, 'text': 'Metal', 'confidence': 0.89},
                            {'row': 1, 'col': 3, 'text': '1', 'confidence': 0.92},
                            {'row': 1, 'col': 4, 'text': 'unit', 'confidence': 0.94},
                        ],
                        'markdown': '...',
                        'confidence': 0.91
                    },
                    'confidence': 0.91
                }
            ],
            'layout_confidence': 0.92,
            'extraction_confidence': 0.91,
            'overall_confidence': 0.91,
            'page_count': 1,
            'processing_time_ms': 234.5
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Create parser in dolphin mode
        parser = BlueprintParser(
            parser_service="dolphin",
            dolphin_api_url="http://localhost:8001"
        )

        # Create a mock file
        test_file = Path("/tmp/test_blueprint.pdf")
        test_file.write_text("mock pdf content")

        try:
            # Parse blueprint
            blueprint = parser.parse_blueprint(test_file)

            # Assertions
            assert blueprint.parser_source == "dolphin"
            assert blueprint.extraction_confidence == 0.91
            assert len(blueprint.assets) == 1
            assert blueprint.assets[0].id == "HVAC_1"
            assert blueprint.assets[0].type == "HVAC"
            assert blueprint.assets[0].confidence_score > 0.0

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()


class TestConfidencePropagation:
    """Test confidence score propagation through the system."""

    def test_blueprint_asset_confidence(self):
        """Test that BlueprintAsset stores confidence scores."""
        asset = BlueprintAsset(
            id="Test_Asset",
            type="Wall",
            material="Concrete",
            quantity=100.0,
            unit="sqft",
            floor="Floor_1",
            confidence_score=0.87
        )

        assert asset.confidence_score == 0.87

    def test_blueprint_data_confidence(self):
        """Test that BlueprintData stores overall confidence."""
        from src.ingestion.parser import BlueprintData

        blueprint = BlueprintData(
            blueprint_id="BP001",
            project_id="PRJ001",
            revision="A",
            date="2024-01-01",
            assets=[],
            extraction_confidence=0.89,
            parser_source="dolphin"
        )

        assert blueprint.extraction_confidence == 0.89
        assert blueprint.parser_source == "dolphin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
