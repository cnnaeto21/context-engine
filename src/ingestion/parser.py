"""
Blueprint Parser Module - Day 2: Dolphin Integration

Handles parsing of construction blueprint PDFs into structured JSON format.
Supports both mock mode (JSON) and Dolphin-v2 mode (real PDF/image parsing).
"""

import json
import logging
import os
import requests
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
    confidence_score: float = Field(1.0, description="Extraction confidence (0.0-1.0)")


class BlueprintData(BaseModel):
    """Complete blueprint document structure."""
    blueprint_id: str = Field(..., description="Unique blueprint identifier")
    project_id: str = Field(..., description="Project identifier")
    revision: str = Field(..., description="Blueprint revision (A, B, C, etc.)")
    date: str = Field(..., description="Blueprint date (YYYY-MM-DD)")
    assets: List[BlueprintAsset] = Field(default_factory=list, description="List of assets")
    extraction_confidence: float = Field(1.0, description="Overall extraction confidence (0.0-1.0)")
    parser_source: str = Field("mock", description="Parser used (mock, dolphin)")


class DolphinClient:
    """
    Client for communicating with Dolphin inference service.

    Handles HTTP communication with the local Dolphin FastAPI service
    and transforms Dolphin output into BlueprintAsset objects.
    """

    def __init__(self, api_url: str = "http://localhost:8001"):
        """
        Initialize Dolphin client.

        Args:
            api_url: Base URL for Dolphin inference service
        """
        self.api_url = api_url
        logger.info(f"DolphinClient initialized with API URL: {api_url}")

    def parse_document(
        self,
        file_path: Path,
        doc_type: str = "blueprint"
    ) -> Dict[str, Any]:
        """
        Parse a document using Dolphin service.

        Args:
            file_path: Path to PDF or image file
            doc_type: Document type hint (default: "blueprint")

        Returns:
            Dictionary with parsed elements and confidence scores

        Raises:
            requests.RequestException: If API call fails
        """
        logger.info(f"Parsing document with Dolphin: {file_path}")

        try:
            # Prepare file for upload
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, self._get_mime_type(file_path))}
                params = {'doc_type': doc_type}

                # Make API request
                response = requests.post(
                    f"{self.api_url}/parse",
                    files=files,
                    params=params,
                    timeout=120  # 2 minute timeout for large files
                )
                response.raise_for_status()

            result = response.json()
            logger.info(f"Dolphin parse complete: {len(result['parsed_elements'])} elements, "
                       f"confidence={result['overall_confidence']:.2f}")

            return result

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Dolphin service not available at {self.api_url}: {e}")
            logger.warning("Falling back to mock parsing mode")
            return self._mock_parse_document(file_path)

    def table_to_assets(
        self,
        table_element: Dict[str, Any],
        blueprint_id: str,
        floor_id: str = "Unknown"
    ) -> List[BlueprintAsset]:
        """
        Convert a parsed table into BlueprintAsset objects.

        Expects table to have columns like: Asset ID, Type, Material, Quantity, Unit

        Args:
            table_element: Parsed table element from Dolphin
            blueprint_id: Blueprint identifier
            floor_id: Floor identifier (default: "Unknown")

        Returns:
            List of BlueprintAsset objects
        """
        assets = []
        table_data = table_element.get('content', {})
        cells = table_data.get('cells', [])

        if not cells:
            logger.warning("No cells found in table")
            return assets

        # Build a grid from cells
        max_row = max(cell['row'] for cell in cells)
        max_col = max(cell['col'] for cell in cells)

        grid = [[None for _ in range(max_col + 1)] for _ in range(max_row + 1)]
        cell_confidences = [[0.0 for _ in range(max_col + 1)] for _ in range(max_row + 1)]

        for cell in cells:
            grid[cell['row']][cell['col']] = cell['text']
            cell_confidences[cell['row']][cell['col']] = cell['confidence']

        # Assume first row is header
        if max_row < 1:
            logger.warning("Table has no data rows (only header)")
            return assets

        header = grid[0]
        logger.info(f"Table header: {header}")

        # Map columns (case-insensitive)
        col_map = {}
        for idx, col_name in enumerate(header):
            if col_name:
                col_lower = col_name.lower().strip()
                if 'asset' in col_lower or 'id' in col_lower or 'mark' in col_lower:
                    col_map['id'] = idx
                elif 'type' in col_lower:
                    col_map['type'] = idx
                elif 'material' in col_lower:
                    col_map['material'] = idx
                elif 'quantity' in col_lower or 'qty' in col_lower:
                    col_map['quantity'] = idx
                elif 'unit' in col_lower:
                    col_map['unit'] = idx

        logger.info(f"Column mapping: {col_map}")

        # Parse data rows
        for row_idx in range(1, max_row + 1):
            row = grid[row_idx]
            row_confidences = cell_confidences[row_idx]

            # Extract fields
            try:
                asset_id = row[col_map.get('id', 0)] if col_map.get('id') is not None else f"Asset_{row_idx}"
                asset_type = row[col_map.get('type', 1)] if col_map.get('type') is not None else "Unknown"
                material = row[col_map.get('material', 2)] if col_map.get('material') is not None else "Unknown"
                quantity_str = row[col_map.get('quantity', 3)] if col_map.get('quantity') is not None else "0"
                unit = row[col_map.get('unit', 4)] if col_map.get('unit') is not None else "units"

                # Clean quantity (remove $ and commas)
                quantity_str = quantity_str.replace('$', '').replace(',', '').strip()
                quantity = float(quantity_str) if quantity_str and quantity_str.replace('.', '').isdigit() else 0.0

                # Calculate row confidence
                row_confidence = sum(row_confidences) / len(row_confidences) if row_confidences else 0.85

                asset = BlueprintAsset(
                    id=asset_id,
                    type=asset_type,
                    material=material,
                    quantity=quantity,
                    unit=unit,
                    floor=floor_id,
                    confidence_score=row_confidence
                )

                assets.append(asset)
                logger.debug(f"Extracted asset: {asset_id} ({asset_type}, {material}, {quantity} {unit})")

            except (ValueError, IndexError, TypeError) as e:
                logger.warning(f"Failed to parse row {row_idx}: {e}")
                continue

        logger.info(f"Extracted {len(assets)} assets from table")
        return assets

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type from file extension."""
        suffix = file_path.suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff'
        }
        return mime_types.get(suffix, 'application/octet-stream')


class BlueprintParser:
    """
    Parses construction blueprints into structured data.

    Supports multiple parser backends:
    - mock: Reads from mock JSON files (Day 1 MVP)
    - dolphin: ByteDance Dolphin-v2 for real PDF/image parsing (Day 2)
    """

    def __init__(self, parser_service: str = "mock", dolphin_api_url: Optional[str] = None):
        """
        Initialize the blueprint parser.

        Args:
            parser_service: Parser backend to use ("mock" or "dolphin")
            dolphin_api_url: URL for Dolphin service (required if parser_service="dolphin")
        """
        self.parser_service = parser_service
        self.dolphin_client = None

        if parser_service == "dolphin":
            if not dolphin_api_url:
                dolphin_api_url = os.getenv("DOLPHIN_API_URL", "http://localhost:8001")
            self.dolphin_client = DolphinClient(api_url=dolphin_api_url)

        logger.info(f"BlueprintParser initialized (parser_service={parser_service})")

    def parse_blueprint(self, file_path: Path) -> BlueprintData:
        """
        Parse a blueprint file into structured data.

        Args:
            file_path: Path to the blueprint file (PDF, image, or JSON)

        Returns:
            BlueprintData object containing parsed assets

        Raises:
            FileNotFoundError: If the blueprint file doesn't exist
            ValueError: If the blueprint data is invalid
        """
        if self.parser_service == "mock":
            return self._parse_mock_json(file_path)
        elif self.parser_service == "dolphin":
            return self._parse_with_dolphin(file_path)
        else:
            raise ValueError(f"Unknown parser service: {self.parser_service}")

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

    def _parse_with_dolphin(self, file_path: Path) -> BlueprintData:
        """
        Parse a blueprint using Dolphin service.

        Args:
            file_path: Path to PDF or image file

        Returns:
            BlueprintData object with extracted assets

        Raises:
            FileNotFoundError: If the file doesn't exist
            requests.RequestException: If Dolphin API call fails
        """
        logger.info(f"Parsing blueprint with Dolphin: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {file_path}")

        # Call Dolphin API
        parse_result = self.dolphin_client.parse_document(file_path, doc_type="blueprint")

        # Extract metadata
        blueprint_id = file_path.stem  # Use filename as blueprint ID
        extraction_confidence = parse_result.get('overall_confidence', 0.0)

        # Find table elements and convert to assets
        all_assets = []
        for element in parse_result.get('parsed_elements', []):
            if element['type'] == 'table':
                assets = self.dolphin_client.table_to_assets(
                    element,
                    blueprint_id=blueprint_id,
                    floor_id="Floor_1"  # Default floor, should be detected from context
                )
                all_assets.extend(assets)

        # Create BlueprintData
        blueprint = BlueprintData(
            blueprint_id=blueprint_id,
            project_id="Project_1",  # Default, should be detected from context
            revision="Unknown",  # Should be detected from document
            date="2024-01-01",  # Should be detected from document
            assets=all_assets,
            extraction_confidence=extraction_confidence,
            parser_source="dolphin"
        )

        logger.info(f"Successfully parsed blueprint {blueprint_id} with Dolphin: "
                   f"{len(all_assets)} assets, confidence={extraction_confidence:.2f}")

        return blueprint

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
