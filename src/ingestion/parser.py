"""
Blueprint Parser Module

Handles parsing of construction blueprint PDFs into structured JSON format.
For MVP: Uses mock JSON data. Future: Integrates with Reducto.ai or Unstructured.io
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AssetDimensions(BaseModel):
    """Physical dimensions of an asset."""
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


class BlueprintAsset(BaseModel):
    """Represents a physical asset extracted from a blueprint."""
    id: str = Field(..., description="Unique identifier for the asset")
    type: str = Field(..., description="Asset type (Wall, Beam, HVAC, etc.)")
    material: str = Field(..., description="Material type (Concrete, Steel, etc.)")
    quantity: float = Field(..., description="Quantity in specified units")
    unit: str = Field(..., description="Unit of measurement (sqft, linear_ft, etc.)")
    floor: str = Field(..., description="Floor identifier where asset is located")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Physical dimensions")


class BlueprintData(BaseModel):
    """Complete blueprint document structure."""
    blueprint_id: str = Field(..., description="Unique blueprint identifier")
    project_id: str = Field(..., description="Project identifier")
    revision: str = Field(..., description="Blueprint revision (A, B, C, etc.)")
    date: str = Field(..., description="Blueprint date (YYYY-MM-DD)")
    assets: List[BlueprintAsset] = Field(default_factory=list, description="List of assets")


class BlueprintParser:
    """
    Parses construction blueprints into structured data.

    For MVP: Reads from mock JSON files.
    Future: Integrates with PDF parsing APIs (Reducto.ai, Unstructured.io).
    """

    def __init__(self, mock_mode: bool = True):
        """
        Initialize the blueprint parser.

        Args:
            mock_mode: If True, reads from mock JSON files instead of parsing PDFs
        """
        self.mock_mode = mock_mode
        logger.info(f"BlueprintParser initialized (mock_mode={mock_mode})")

    def parse_blueprint(self, file_path: Path) -> BlueprintData:
        """
        Parse a blueprint file into structured data.

        Args:
            file_path: Path to the blueprint file (PDF or JSON)

        Returns:
            BlueprintData object containing parsed assets

        Raises:
            FileNotFoundError: If the blueprint file doesn't exist
            ValueError: If the blueprint data is invalid
        """
        if self.mock_mode:
            return self._parse_mock_json(file_path)
        else:
            # FUTURE: Implement real PDF parsing here
            raise NotImplementedError("Real PDF parsing not yet implemented")

    def _parse_mock_json(self, file_path: Path) -> BlueprintData:
        """
        Parse a mock JSON blueprint file.

        Args:
            file_path: Path to the JSON file

        Returns:
            BlueprintData object

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the JSON is invalid
        """
        logger.info(f"Parsing mock blueprint from: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {file_path}")

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Validate and parse using Pydantic
            blueprint = BlueprintData(**data)
            logger.info(f"Successfully parsed blueprint {blueprint.blueprint_id} "
                       f"with {len(blueprint.assets)} assets")
            return blueprint

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in blueprint file: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing blueprint data: {e}")

    def compare_blueprints(self, before: BlueprintData, after: BlueprintData) -> Dict[str, Any]:
        """
        Compare two blueprints and identify changes.

        Args:
            before: Original blueprint state
            after: New blueprint state

        Returns:
            Dictionary containing added, removed, and modified assets
        """
        logger.info(f"Comparing blueprints: {before.blueprint_id} vs {after.blueprint_id}")

        # Create lookup dictionaries
        before_assets = {asset.id: asset for asset in before.assets}
        after_assets = {asset.id: asset for asset in after.assets}

        # Find added assets
        added = [asset for asset_id, asset in after_assets.items()
                if asset_id not in before_assets]

        # Find removed assets
        removed = [asset for asset_id, asset in before_assets.items()
                  if asset_id not in after_assets]

        # Find modified assets
        modified = []
        for asset_id, after_asset in after_assets.items():
            if asset_id in before_assets:
                before_asset = before_assets[asset_id]
                if self._assets_differ(before_asset, after_asset):
                    modified.append({
                        'asset_id': asset_id,
                        'before': before_asset,
                        'after': after_asset,
                        'changes': self._get_asset_changes(before_asset, after_asset)
                    })

        changes = {
            'added': [asset.dict() for asset in added],
            'removed': [asset.dict() for asset in removed],
            'modified': modified,
            'summary': {
                'added_count': len(added),
                'removed_count': len(removed),
                'modified_count': len(modified)
            }
        }

        logger.info(f"Blueprint comparison complete: {changes['summary']}")
        return changes

    def _assets_differ(self, before: BlueprintAsset, after: BlueprintAsset) -> bool:
        """Check if two assets are different."""
        # Compare key fields that indicate changes
        return (before.quantity != after.quantity or
                before.material != after.material or
                before.type != after.type or
                before.dimensions != after.dimensions)

    def _get_asset_changes(self, before: BlueprintAsset, after: BlueprintAsset) -> Dict[str, Any]:
        """Get specific changes between two assets."""
        changes = {}

        if before.quantity != after.quantity:
            changes['quantity'] = {
                'before': before.quantity,
                'after': after.quantity,
                'delta': after.quantity - before.quantity
            }

        if before.material != after.material:
            changes['material'] = {
                'before': before.material,
                'after': after.material
            }

        if before.type != after.type:
            changes['type'] = {
                'before': before.type,
                'after': after.type
            }

        if before.dimensions != after.dimensions:
            changes['dimensions'] = {
                'before': before.dimensions,
                'after': after.dimensions
            }

        return changes
