"""
Briefcase Assembler

Constructs the "Briefcase of Truth" by combining graph state with detected changes.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .templates import BriefcaseTemplates

logger = logging.getLogger(__name__)


class BriefcaseAssembler:
    """
    Assembles contextual information for Claude's reasoning.
    Combines current state, detected changes, and business rules.
    """

    def __init__(
        self,
        approval_threshold: float = 500.0,
        max_contingency: float = 5000.0,
        min_confidence_threshold: float = 0.85
    ):
        """
        Initialize the briefcase assembler.

        Args:
            approval_threshold: Dollar threshold for requiring approval
            max_contingency: Maximum contingency budget available
            min_confidence_threshold: Minimum confidence for auto-approval
        """
        self.approval_threshold = approval_threshold
        self.max_contingency = max_contingency
        self.min_confidence_threshold = min_confidence_threshold
        self.templates = BriefcaseTemplates()
        logger.info("BriefcaseAssembler initialized")

    def assemble_asset_change(
        self,
        delta: Dict[str, Any],
        project_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Assemble briefcase for an asset quantity/material change.

        Args:
            delta: Delta information from StateQueries.calculate_delta()
            project_context: Optional additional project context

        Returns:
            Formatted prompt string for Claude
        """
        logger.info(f"Assembling briefcase for asset change: {delta.get('object_id')}")

        if not delta.get('exists'):
            # Asset doesn't exist - treat as new asset
            return self.assemble_new_asset(delta, project_context)

        # Extract data from delta
        obj_data = delta
        lineitem = delta.get('lineitem', {}) or {}
        vendor = delta.get('vendor', {}) or {}

        # Prepare template variables
        template_vars = {
            'asset_id': delta['object_id'],
            'asset_type': obj_data.get('current_material', 'Unknown'),
            'material': delta.get('current_material', 'Unknown'),
            'current_quantity': delta.get('current_quantity', 0),
            'unit': lineitem.get('unit', 'units'),
            'cost_per_unit': delta.get('cost_per_unit', 0),
            'current_total_cost': delta.get('current_total_cost', 0),
            'budget_code': lineitem.get('id', 'Unknown'),
            'vendor_name': vendor.get('name', 'Unknown'),
            'last_updated': self._format_datetime(obj_data.get('last_updated')),
            'new_quantity': delta.get('new_quantity', 0),
            'quantity_delta': delta.get('quantity_delta', 0),
            'cost_impact': delta.get('cost_impact', 0),
            'material_changed': delta.get('material_changed', False),
            'budget_description': lineitem.get('description', 'Unknown'),
            'allocated_budget': lineitem.get('allocated_budget', 0),
            'spent_to_date': lineitem.get('spent_to_date', 0),
            'remaining_budget': lineitem.get('remaining', 0),
            'contingency': lineitem.get('contingency', 0),
            'approval_threshold': self.approval_threshold,
            'max_contingency': self.max_contingency,
            'min_confidence_threshold': self.min_confidence_threshold
        }

        # Add project context if available
        if project_context:
            template_vars.update({
                'project_name': project_context.get('name', 'Unknown Project'),
                'floor_name': project_context.get('floor_name', 'Unknown Floor')
            })

        prompt = self.templates.asset_change_template().format(**template_vars)
        logger.info("Asset change briefcase assembled successfully")
        return prompt

    def assemble_new_asset(
        self,
        asset_data: Dict[str, Any],
        project_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Assemble briefcase for a new asset addition.

        Args:
            asset_data: New asset information
            project_context: Optional project context

        Returns:
            Formatted prompt string for Claude
        """
        logger.info(f"Assembling briefcase for new asset: {asset_data.get('object_id')}")

        # Extract or provide defaults
        template_vars = {
            'asset_id': asset_data.get('object_id', 'Unknown'),
            'asset_type': asset_data.get('type', 'Unknown'),
            'material': asset_data.get('material', 'Unknown'),
            'quantity': asset_data.get('new_quantity', asset_data.get('quantity', 0)),
            'unit': asset_data.get('unit', 'units'),
            'floor_id': asset_data.get('floor', 'Unknown'),
            'project_name': 'Unknown Project',
            'floor_name': 'Unknown Floor',
            'revision': 'Unknown',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'project_budget': 0,
            'total_allocated': 0,
            'total_spent': 0,
            'total_remaining': 0,
            'total_contingency': 0,
            'max_contingency': self.max_contingency,
            'estimated_cost_per_unit': 0
        }

        # Update with project context if available
        if project_context:
            template_vars.update({
                'project_name': project_context.get('name', 'Unknown Project'),
                'floor_name': project_context.get('floor_name', 'Unknown Floor'),
                'revision': project_context.get('revision', 'Unknown'),
                'date': project_context.get('date', template_vars['date']),
                'project_budget': project_context.get('budget_total', 0),
                'total_allocated': project_context.get('total_allocated', 0),
                'total_spent': project_context.get('total_spent', 0),
                'total_remaining': project_context.get('total_remaining', 0),
                'total_contingency': project_context.get('total_contingency', 0)
            })

        prompt = self.templates.new_asset_template().format(**template_vars)
        logger.info("New asset briefcase assembled successfully")
        return prompt

    def assemble_asset_removal(
        self,
        asset_data: Dict[str, Any],
        project_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Assemble briefcase for an asset removal.

        Args:
            asset_data: Removed asset information
            project_context: Optional project context

        Returns:
            Formatted prompt string for Claude
        """
        logger.info(f"Assembling briefcase for asset removal: {asset_data.get('id')}")

        lineitem = asset_data.get('lineitem', {}) or {}

        template_vars = {
            'asset_id': asset_data.get('id', 'Unknown'),
            'asset_type': asset_data.get('type', 'Unknown'),
            'material': asset_data.get('material', 'Unknown'),
            'quantity': asset_data.get('quantity', 0),
            'unit': asset_data.get('unit', 'units'),
            'cost_per_unit': asset_data.get('cost_per_unit', 0),
            'total_cost': asset_data.get('total_cost', 0),
            'budget_code': lineitem.get('id', 'Unknown'),
            'cost_savings': asset_data.get('total_cost', 0),
            'budget_description': lineitem.get('description', 'Unknown'),
            'allocated_budget': lineitem.get('allocated_budget', 0),
            'spent_to_date': lineitem.get('spent_to_date', 0),
            'project_name': 'Unknown Project',
            'floor_name': 'Unknown Floor',
            'revision': 'Unknown'
        }

        # Update with project context if available
        if project_context:
            template_vars.update({
                'project_name': project_context.get('name', 'Unknown Project'),
                'floor_name': project_context.get('floor_name', 'Unknown Floor'),
                'revision': project_context.get('revision', 'Unknown')
            })

        prompt = self.templates.asset_removal_template().format(**template_vars)
        logger.info("Asset removal briefcase assembled successfully")
        return prompt

    def get_function_definition(self) -> Dict[str, Any]:
        """
        Get the Claude function calling definition.

        Returns:
            Function definition dictionary for Claude API
        """
        return self.templates.get_function_definition()

    def _format_datetime(self, dt: Any) -> str:
        """
        Format datetime for display.

        Args:
            dt: Datetime object or string

        Returns:
            Formatted datetime string
        """
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(dt, str):
            return dt
        else:
            return 'Unknown'
