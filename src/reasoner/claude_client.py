"""
Claude API Client

Handles communication with Anthropic's Claude API for reasoning tasks.
"""

import logging
from typing import Dict, Any, Optional, List

from anthropic import Anthropic
from anthropic.types import Message, ContentBlock

logger = logging.getLogger(__name__)


class ClaudeClient:
    """
    Client for interacting with Claude API for construction budget reasoning.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096
    ):
        """
        Initialize Claude API client.

        Args:
            api_key: Anthropic API key
            model: Claude model identifier
            max_tokens: Maximum tokens for responses
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        logger.info(f"ClaudeClient initialized with model: {model}")

    def reason_about_change(
        self,
        briefcase: str,
        function_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send briefcase to Claude and get reasoning + action recommendation.

        Args:
            briefcase: The "Briefcase of Truth" prompt string
            function_definition: Function calling definition for recommend_action

        Returns:
            Dictionary containing Claude's recommendation

        Raises:
            RuntimeError: If API call fails or response is invalid
        """
        logger.info("Sending briefcase to Claude for reasoning")

        try:
            # Create message with function calling
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                tools=[function_definition],
                messages=[
                    {
                        "role": "user",
                        "content": briefcase
                    }
                ]
            )

            logger.debug(f"Claude response received: {message.stop_reason}")

            # Extract function call from response
            recommendation = self._extract_recommendation(message)

            if not recommendation:
                logger.error("No function call found in Claude's response")
                raise RuntimeError("Claude did not return a function call")

            logger.info(f"Recommendation received: {recommendation.get('action_type')}")
            return recommendation

        except Exception as e:
            logger.error(f"Failed to get reasoning from Claude: {e}")
            raise RuntimeError(f"Claude API call failed: {e}")

    def _extract_recommendation(self, message: Message) -> Optional[Dict[str, Any]]:
        """
        Extract the recommend_action function call from Claude's response.

        Args:
            message: Claude API message response

        Returns:
            Dictionary with recommendation data, or None if not found
        """
        # Look for tool use in the response
        for block in message.content:
            if hasattr(block, 'type') and block.type == 'tool_use':
                if block.name == 'recommend_action':
                    recommendation = {
                        'action_type': block.input.get('action_type'),
                        'requires_human': block.input.get('requires_human'),
                        'confidence_score': block.input.get('confidence_score'),
                        'reasoning': block.input.get('reasoning'),
                        'recommended_budget_code': block.input.get('recommended_budget_code')
                    }
                    return recommendation

        # If no tool use found, log the response for debugging
        logger.warning(f"No tool use found. Response content: {message.content}")
        return None

    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            # Simple test message
            message = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[
                    {
                        "role": "user",
                        "content": "Test"
                    }
                ]
            )
            logger.info("API key validation successful")
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False

    def batch_reason(
        self,
        briefcases: List[str],
        function_definition: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple briefcases in sequence.

        Args:
            briefcases: List of briefcase prompt strings
            function_definition: Function calling definition

        Returns:
            List of recommendations, one for each briefcase

        Note:
            This processes sequentially. Future: Implement true batch API when available.
        """
        logger.info(f"Processing {len(briefcases)} briefcases in batch")

        recommendations = []
        for i, briefcase in enumerate(briefcases):
            try:
                logger.info(f"Processing briefcase {i+1}/{len(briefcases)}")
                recommendation = self.reason_about_change(briefcase, function_definition)
                recommendations.append(recommendation)
            except Exception as e:
                logger.error(f"Failed to process briefcase {i+1}: {e}")
                # Add error placeholder
                recommendations.append({
                    'action_type': 'flag_for_approval',
                    'requires_human': True,
                    'confidence_score': 0.0,
                    'reasoning': f"Error processing: {str(e)}",
                    'error': True
                })

        logger.info(f"Batch processing complete: {len(recommendations)} recommendations")
        return recommendations
