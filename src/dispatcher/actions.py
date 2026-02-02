"""
Action Dispatcher

Executes actions based on Claude's recommendations.
"""

import logging
from typing import Dict, Any, Optional

from .budget_api import MockBudgetAPI

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """
    Dispatches actions based on Claude's reasoning recommendations.

    Handles:
    - Budget updates (auto-approved changes)
    - Approval workflows (changes requiring human review)
    - Notifications and logging
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
        self.budget_api = budget_api
        self.min_confidence_threshold = min_confidence_for_auto_approval
        logger.info("ActionDispatcher initialized")

    def dispatch(
        self,
        recommendation: Dict[str, Any],
        asset_id: str,
        budget_code: str,
        cost_impact: float
    ) -> Dict[str, Any]:
        """
        Dispatch an action based on Claude's recommendation.

        Args:
            recommendation: Claude's recommendation dictionary
            asset_id: Asset identifier
            budget_code: Budget line item code
            cost_impact: Calculated cost impact

        Returns:
            Dictionary containing dispatch result
        """
        logger.info(f"Dispatching action for asset: {asset_id}")

        action_type = recommendation.get('action_type')
        requires_human = recommendation.get('requires_human', True)
        confidence = recommendation.get('confidence_score', 0.0)
        reasoning = recommendation.get('reasoning', 'No reasoning provided')

        result = {
            'asset_id': asset_id,
            'action_type': action_type,
            'requires_human': requires_human,
            'confidence': confidence,
            'reasoning': reasoning,
            'success': False,
            'message': ''
        }

        try:
            if action_type == 'update_budget' and not requires_human:
                # Auto-approve if confidence is high enough
                if confidence >= self.min_confidence_threshold:
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
                    success = self.budget_api.flag_for_approval(
                        code=budget_code,
                        delta=cost_impact,
                        asset_id=asset_id,
                        reasoning=f"Confidence below threshold ({confidence:.2f}): {reasoning}"
                    )
                    result['requires_human'] = True
                    result['success'] = success
                    result['message'] = "Flagged for approval (confidence too low)"
                    logger.info(f"Confidence too low for {asset_id}, flagged for approval")

            elif action_type == 'flag_for_approval' or requires_human:
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
        recommendations: list[Dict[str, Any]],
        asset_ids: list[str],
        budget_codes: list[str],
        cost_impacts: list[float]
    ) -> list[Dict[str, Any]]:
        """
        Dispatch multiple actions in batch.

        Args:
            recommendations: List of Claude recommendations
            asset_ids: List of asset identifiers
            budget_codes: List of budget codes
            cost_impacts: List of cost impacts

        Returns:
            List of dispatch results
        """
        logger.info(f"Dispatching batch of {len(recommendations)} actions")

        results = []
        for rec, asset_id, budget_code, cost_impact in zip(
            recommendations, asset_ids, budget_codes, cost_impacts
        ):
            result = self.dispatch(rec, asset_id, budget_code, cost_impact)
            results.append(result)

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"Batch dispatch complete: {success_count}/{len(results)} successful")

        return results

    def get_approval_queue(self) -> list[Dict[str, Any]]:
        """
        Get all items waiting for approval.

        Returns:
            List of pending approvals
        """
        return self.budget_api.get_pending_approvals()

    def approve_pending_change(
        self,
        budget_code: str,
        asset_id: str
    ) -> bool:
        """
        Manually approve a pending change.

        Args:
            budget_code: Budget line item code
            asset_id: Asset identifier

        Returns:
            True if successful, False otherwise

        Note:
            For MVP, this is simplified. Future: Implement proper approval workflow.
        """
        logger.info(f"Manually approving change: {budget_code}, asset={asset_id}")

        # FUTURE: Implement proper approval workflow
        # For now, just log the approval
        logger.warning("Manual approval not fully implemented in MVP")
        return True

    def reject_pending_change(
        self,
        budget_code: str,
        asset_id: str,
        reason: str
    ) -> bool:
        """
        Reject a pending change.

        Args:
            budget_code: Budget line item code
            asset_id: Asset identifier
            reason: Reason for rejection

        Returns:
            True if successful, False otherwise

        Note:
            For MVP, this is simplified. Future: Implement proper rejection workflow.
        """
        logger.info(f"Rejecting change: {budget_code}, asset={asset_id}, reason={reason}")

        # FUTURE: Implement proper rejection workflow
        logger.warning("Manual rejection not fully implemented in MVP")
        return True
