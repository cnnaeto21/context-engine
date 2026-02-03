"""
Mock Budget API

Simulates a budget management system API using JSON file storage.
Future: Replace with real API integration (Procore, Autodesk, etc.)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PendingChange(BaseModel):
    """Represents a pending budget change awaiting approval."""
    asset_id: str
    delta: float
    status: str = "pending_approval"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    reasoning: Optional[str] = None


class BudgetLineItem(BaseModel):
    """Represents a budget line item."""
    code: str
    description: str
    allocated: float
    spent: float
    pending_changes: List[PendingChange] = Field(default_factory=list)


class BudgetState(BaseModel):
    """Complete budget state."""
    project_id: str
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    line_items: List[BudgetLineItem] = Field(default_factory=list)


class MockBudgetAPI:
    """
    Mock budget management API that reads/writes to a JSON file.

    For MVP: Simple JSON file operations.
    Future: Replace with real API client for Procore, Autodesk, etc.
    """

    def __init__(self, budget_file_path: str):
        """
        Initialize the mock budget API.

        Args:
            budget_file_path: Path to the JSON file storing budget state
        """
        self.budget_file = Path(budget_file_path)
        logger.info(f"MockBudgetAPI initialized with file: {budget_file_path}")

        # Create file with default structure if it doesn't exist or is empty
        if not self.budget_file.exists() or self.budget_file.stat().st_size == 0:
            self._create_default_budget()

    def _create_default_budget(self) -> None:
        """Create a default budget file if none exists."""
        logger.info("Creating default budget file")

        default_budget = BudgetState(
            project_id="proj_001",
            line_items=[
                BudgetLineItem(
                    code="B47",
                    description="Cast-in-Place Concrete",
                    allocated=50000.00,
                    spent=30000.00
                ),
                BudgetLineItem(
                    code="B48",
                    description="Structural Steel Framing",
                    allocated=75000.00,
                    spent=45000.00
                )
            ]
        )

        self._save_budget(default_budget)

    def _load_budget(self) -> BudgetState:
        """Load budget state from file."""
        try:
            with open(self.budget_file, 'r') as f:
                data = json.load(f)
            return BudgetState(**data)
        except Exception as e:
            logger.error(f"Failed to load budget: {e}")
            raise

    def _save_budget(self, budget: BudgetState) -> None:
        """Save budget state to file."""
        try:
            self.budget_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.budget_file, 'w') as f:
                json.dump(budget.model_dump(), f, indent=2)
            logger.debug("Budget saved successfully")
        except Exception as e:
            logger.error(f"Failed to save budget: {e}")
            raise

    def get_line_item(self, code: str) -> Optional[BudgetLineItem]:
        """
        Get a specific budget line item.

        Args:
            code: Budget line item code (e.g., 'B47')

        Returns:
            BudgetLineItem if found, None otherwise
        """
        budget = self._load_budget()
        for item in budget.line_items:
            if item.code == code:
                return item
        return None

    def update_budget(
        self,
        code: str,
        delta: float,
        asset_id: str,
        auto_approved: bool = False
    ) -> bool:
        """
        Update a budget line item with a delta.

        Args:
            code: Budget line item code
            delta: Amount to change (positive or negative)
            asset_id: Asset identifier causing the change
            auto_approved: If True, update spent immediately; if False, add to pending

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating budget {code}: delta=${delta:.2f}, "
                   f"auto_approved={auto_approved}")

        try:
            budget = self._load_budget()

            # Find the line item
            line_item = None
            for item in budget.line_items:
                if item.code == code:
                    line_item = item
                    break

            if not line_item:
                logger.error(f"Line item not found: {code}")
                return False

            if auto_approved:
                # Update spent amount directly
                line_item.spent += delta
                logger.info(f"Budget updated: {code} spent is now ${line_item.spent:.2f}")
            else:
                # Add to pending changes
                pending = PendingChange(
                    asset_id=asset_id,
                    delta=delta,
                    status="pending_approval"
                )
                line_item.pending_changes.append(pending)
                logger.info(f"Change added to pending approval: {code}")

            budget.last_updated = datetime.now().isoformat()
            self._save_budget(budget)
            return True

        except Exception as e:
            logger.error(f"Failed to update budget: {e}")
            return False

    def flag_for_approval(
        self,
        code: str,
        delta: float,
        asset_id: str,
        reasoning: str
    ) -> bool:
        """
        Flag a budget change for human approval.

        Args:
            code: Budget line item code
            delta: Amount to change
            asset_id: Asset identifier
            reasoning: Explanation for the change

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Flagging for approval: {code}, asset={asset_id}, delta=${delta:.2f}")

        try:
            budget = self._load_budget()

            # Find the line item
            line_item = None
            for item in budget.line_items:
                if item.code == code:
                    line_item = item
                    break

            if not line_item:
                logger.error(f"Line item not found: {code}")
                return False

            # Add to pending changes with reasoning
            pending = PendingChange(
                asset_id=asset_id,
                delta=delta,
                status="pending_approval",
                reasoning=reasoning
            )
            line_item.pending_changes.append(pending)

            budget.last_updated = datetime.now().isoformat()
            self._save_budget(budget)

            logger.info(f"Successfully flagged for approval: {asset_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to flag for approval: {e}")
            return False

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Get all pending approval requests.

        Returns:
            List of pending changes across all line items
        """
        budget = self._load_budget()
        pending = []

        for item in budget.line_items:
            for change in item.pending_changes:
                pending.append({
                    'budget_code': item.code,
                    'description': item.description,
                    'asset_id': change.asset_id,
                    'delta': change.delta,
                    'status': change.status,
                    'timestamp': change.timestamp,
                    'reasoning': change.reasoning
                })

        logger.info(f"Retrieved {len(pending)} pending approvals")
        return pending

    def get_budget_summary(self) -> Dict[str, Any]:
        """
        Get summary of budget state.

        Returns:
            Dictionary with budget summary statistics
        """
        budget = self._load_budget()

        total_allocated = sum(item.allocated for item in budget.line_items)
        total_spent = sum(item.spent for item in budget.line_items)
        total_pending = sum(
            sum(change.delta for change in item.pending_changes)
            for item in budget.line_items
        )

        summary = {
            'project_id': budget.project_id,
            'last_updated': budget.last_updated,
            'total_allocated': total_allocated,
            'total_spent': total_spent,
            'total_pending': total_pending,
            'total_remaining': total_allocated - total_spent,
            'pending_approval_count': sum(
                len(item.pending_changes) for item in budget.line_items
            ),
            'line_items': [
                {
                    'code': item.code,
                    'description': item.description,
                    'allocated': item.allocated,
                    'spent': item.spent,
                    'remaining': item.allocated - item.spent,
                    'pending_count': len(item.pending_changes)
                }
                for item in budget.line_items
            ]
        }

        return summary
