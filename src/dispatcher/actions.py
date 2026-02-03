"""
Action Dispatcher - Day 2: Provider-Agnostic Architecture

Implements BaseDispatcher abstract class to ensure the Action layer
remains modular and ready for transition to QuickBooks, Ramp, or other systems.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

from .budget_api import MockBudgetAPI

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions that can be dispatched."""
    UPDATE_BUDGET = "update_budget"
    FLAG_FOR_APPROVAL = "flag_for_approval"
    NOTIFY_STAKEHOLDER = "notify_stakeholder"
    CREATE_CHANGE_ORDER = "create_change_order"


class DispatchResult(Dict[str, Any]):
    """
    Standardized dispatch result structure.

    Ensures consistent response format across all dispatcher implementations.
    """
    pass


class BaseDispatcher(ABC):
    """
    Abstract base class for action dispatchers.

    Enforces a provider-agnostic interface so we can swap "Hands" (budget systems)
    without changing the "Brain" (reasoning engine) or "Eyes" (parsing engine).

    Provider Examples:
    - MockBudgetAPI (current MVP)
    - QuickBooks API (future)
    - Ramp API (future)
    - Procore API (future)
    - Custom ERP systems
    """

    def __init__(self, min_confidence_threshold: float = 0.85):
        """
        Initialize base dispatcher.

        Args:
            min_confidence_threshold: Minimum confidence for auto-approval
        """
        self.min_confidence_threshold = min_confidence_threshold
        logger.info(f"{self.__class__.__name__} initialized")

    @abstractmethod
    def dispatch(
        self,
        recommendation: Dict[str, Any],
        asset_id: str,
        budget_code: str,
        cost_impact: float,
        extraction_confidence: Optional[float] = None
    ) -> DispatchResult:
        """
        Dispatch an action based on Claude's recommendation.

        Args:
            recommendation: Claude's recommendation dictionary
            asset_id: Asset identifier
            budget_code: Budget line item code
            cost_impact: Calculated cost impact
            extraction_confidence: Optional PDF extraction confidence

        Returns:
            DispatchResult with standardized structure
        """
        pass

    @abstractmethod
    def dispatch_batch(
        self,
        recommendations: List[Dict[str, Any]],
        asset_ids: List[str],
        budget_codes: List[str],
        cost_impacts: List[float],
        extraction_confidences: Optional[List[float]] = None
    ) -> List[DispatchResult]:
        """
        Dispatch multiple actions in batch.

        Args:
            recommendations: List of Claude recommendations
            asset_ids: List of asset identifiers
            budget_codes: List of budget codes
            cost_impacts: List of cost impacts
            extraction_confidences: Optional list of extraction confidences

        Returns:
            List of DispatchResults
        """
        pass

    @abstractmethod
    def get_approval_queue(self) -> List[Dict[str, Any]]:
        """
        Get all items waiting for approval.

        Returns:
            List of pending approvals
        """
        pass

    @abstractmethod
    def approve_pending_change(
        self,
        budget_code: str,
        asset_id: str,
        approver_id: Optional[str] = None
    ) -> bool:
        """
        Manually approve a pending change.

        Args:
            budget_code: Budget line item code
            asset_id: Asset identifier
            approver_id: Optional approver identifier

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def reject_pending_change(
        self,
        budget_code: str,
        asset_id: str,
        reason: str,
        rejector_id: Optional[str] = None
    ) -> bool:
        """
        Reject a pending change.

        Args:
            budget_code: Budget line item code
            asset_id: Asset identifier
            reason: Reason for rejection
            rejector_id: Optional rejector identifier

        Returns:
            True if successful, False otherwise
        """
        pass

    def _should_auto_approve(
        self,
        claude_confidence: float,
        extraction_confidence: Optional[float],
        requires_human: bool
    ) -> bool:
        """
        Determine if change should be auto-approved.

        Combines multiple confidence signals:
        - Claude's reasoning confidence
        - PDF extraction confidence (if available)
        - Explicit requires_human flag

        Args:
            claude_confidence: Claude's confidence score
            extraction_confidence: Optional extraction confidence from parser
            requires_human: Explicit human review requirement

        Returns:
            True if should auto-approve
        """
        if requires_human:
            return False

        # If we have extraction confidence, use the minimum of both
        if extraction_confidence is not None:
            combined_confidence = min(claude_confidence, extraction_confidence)
        else:
            combined_confidence = claude_confidence

        return combined_confidence >= self.min_confidence_threshold


class ActionDispatcher(BaseDispatcher):
    """
    Concrete implementation of BaseDispatcher using MockBudgetAPI.

    Day 2: Now extends BaseDispatcher for provider-agnostic architecture.
    Future: Easily swap MockBudgetAPI for QuickBooks, Ramp, etc.
    """

    def __init__(
        self,
        budget_api: MockBudgetAPI,
        min_confidence_for_auto_approval: float = 0.85
    ):
        """
        Initialize the action dispatcher.

        Args:
            budget_api: Budget API client instance
            min_confidence_for_auto_approval: Minimum confidence score for auto-approval
        """
        super().__init__(min_confidence_threshold=min_confidence_for_auto_approval)
        self.budget_api = budget_api

    def dispatch(
        self,
        recommendation: Dict[str, Any],
        asset_id: str,
        budget_code: str,
        cost_impact: float,
        extraction_confidence: Optional[float] = None
    ) -> DispatchResult:
        """
        Dispatch an action based on Claude's recommendation.

        Day 2 Enhancement: Now considers extraction confidence from Dolphin parser.

        Args:
            recommendation: Claude's recommendation dictionary
            asset_id: Asset identifier
            budget_code: Budget line item code
            cost_impact: Calculated cost impact
            extraction_confidence: Optional Dolphin extraction confidence

        Returns:
            Dictionary containing dispatch result
        """
        logger.info(f"Dispatching action for asset: {asset_id}")

        action_type = recommendation.get('action_type')
        requires_human = recommendation.get('requires_human', True)
        claude_confidence = recommendation.get('confidence_score', 0.0)
        reasoning = recommendation.get('reasoning', 'No reasoning provided')

        result: DispatchResult = {
            'asset_id': asset_id,
            'action_type': action_type,
            'requires_human': requires_human,
            'claude_confidence': claude_confidence,
            'extraction_confidence': extraction_confidence,
            'reasoning': reasoning,
            'success': False,
            'message': ''
        }

        try:
            if action_type == ActionType.UPDATE_BUDGET.value and not requires_human:
                # Check if we should auto-approve (combining confidences)
                should_auto_approve = self._should_auto_approve(
                    claude_confidence,
                    extraction_confidence,
                    requires_human
                )

                if should_auto_approve:
                    success = self.budget_api.update_budget(
                        code=budget_code,
                        delta=cost_impact,
                        asset_id=asset_id,
                        auto_approved=True
                    )
                    if success:
                        result['success'] = True
                        result['message'] = f"Budget updated automatically: ${cost_impact:+.2f}"
                        logger.info(f"Auto-approved budget update for {asset_id}")
                    else:
                        result['message'] = "Failed to update budget"
                        logger.error(f"Budget update failed for {asset_id}")
                else:
                    # Confidence too low for auto-approval
                    confidence_msg = self._format_confidence_message(
                        claude_confidence,
                        extraction_confidence
                    )
                    success = self.budget_api.flag_for_approval(
                        code=budget_code,
                        delta=cost_impact,
                        asset_id=asset_id,
                        reasoning=f"{confidence_msg}: {reasoning}"
                    )
                    result['requires_human'] = True
                    result['success'] = success
                    result['message'] = "Flagged for approval (confidence too low)"
                    logger.info(f"Confidence too low for {asset_id}, flagged for approval")

            elif action_type == ActionType.FLAG_FOR_APPROVAL.value or requires_human:
                # Flag for human review
                success = self.budget_api.flag_for_approval(
                    code=budget_code,
                    delta=cost_impact,
                    asset_id=asset_id,
                    reasoning=reasoning
                )
                result['success'] = success
                result['message'] = "Flagged for human approval"
                logger.info(f"Flagged for approval: {asset_id}")

            else:
                result['message'] = f"Unknown action type: {action_type}"
                logger.warning(f"Unknown action type: {action_type}")

        except Exception as e:
            result['success'] = False
            result['message'] = f"Error dispatching action: {str(e)}"
            logger.error(f"Error dispatching action for {asset_id}: {e}")

        return result

    def dispatch_batch(
        self,
        recommendations: List[Dict[str, Any]],
        asset_ids: List[str],
        budget_codes: List[str],
        cost_impacts: List[float],
        extraction_confidences: Optional[List[float]] = None
    ) -> List[DispatchResult]:
        """
        Dispatch multiple actions in batch.

        Args:
            recommendations: List of Claude recommendations
            asset_ids: List of asset identifiers
            budget_codes: List of budget codes
            cost_impacts: List of cost impacts
            extraction_confidences: Optional list of Dolphin confidences

        Returns:
            List of dispatch results
        """
        logger.info(f"Dispatching batch of {len(recommendations)} actions")

        # Prepare extraction confidences
        if extraction_confidences is None:
            extraction_confidences = [None] * len(recommendations)

        results = []
        for rec, asset_id, budget_code, cost_impact, extraction_conf in zip(
            recommendations, asset_ids, budget_codes, cost_impacts, extraction_confidences
        ):
            result = self.dispatch(
                rec, asset_id, budget_code, cost_impact, extraction_conf
            )
            results.append(result)

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"Batch dispatch complete: {success_count}/{len(results)} successful")

        return results

    def get_approval_queue(self) -> List[Dict[str, Any]]:
        """
        Get all items waiting for approval.

        Returns:
            List of pending approvals
        """
        return self.budget_api.get_pending_approvals()

    def approve_pending_change(
        self,
        budget_code: str,
        asset_id: str,
        approver_id: Optional[str] = None
    ) -> bool:
        """
        Manually approve a pending change.

        Args:
            budget_code: Budget line item code
            asset_id: Asset identifier
            approver_id: Optional approver identifier

        Returns:
            True if successful, False otherwise

        Note:
            For MVP, this is simplified. Future: Implement proper approval workflow.
        """
        logger.info(f"Manually approving change: {budget_code}, asset={asset_id}")

        if approver_id:
            logger.info(f"Approved by: {approver_id}")

        # FUTURE: Implement proper approval workflow with audit trail
        logger.warning("Manual approval not fully implemented in MVP")
        return True

    def reject_pending_change(
        self,
        budget_code: str,
        asset_id: str,
        reason: str,
        rejector_id: Optional[str] = None
    ) -> bool:
        """
        Reject a pending change.

        Args:
            budget_code: Budget line item code
            asset_id: Asset identifier
            reason: Reason for rejection
            rejector_id: Optional rejector identifier

        Returns:
            True if successful, False otherwise

        Note:
            For MVP, this is simplified. Future: Implement proper rejection workflow.
        """
        logger.info(f"Rejecting change: {budget_code}, asset={asset_id}, reason={reason}")

        if rejector_id:
            logger.info(f"Rejected by: {rejector_id}")

        # FUTURE: Implement proper rejection workflow with audit trail
        logger.warning("Manual rejection not fully implemented in MVP")
        return True

    def _format_confidence_message(
        self,
        claude_confidence: float,
        extraction_confidence: Optional[float]
    ) -> str:
        """
        Format confidence message for logging/reasoning.

        Args:
            claude_confidence: Claude's confidence
            extraction_confidence: Optional extraction confidence

        Returns:
            Formatted message
        """
        if extraction_confidence is not None:
            combined = min(claude_confidence, extraction_confidence)
            return (f"Combined confidence {combined:.2f} below threshold "
                   f"(Claude: {claude_confidence:.2f}, "
                   f"Extraction: {extraction_confidence:.2f})")
        else:
            return f"Confidence {claude_confidence:.2f} below threshold"
