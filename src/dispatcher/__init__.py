"""
Dispatcher Module

Executes actions based on Claude's recommendations.
Handles budget updates and approval workflows.
"""

from .actions import ActionDispatcher
from .budget_api import MockBudgetAPI

__all__ = ["ActionDispatcher", "MockBudgetAPI"]
