"""
Dispatcher Module - Day 2: Provider-Agnostic Architecture

Executes actions based on Claude's recommendations.
Handles budget updates and approval workflows.

Day 2 Enhancement: BaseDispatcher abstract class for modular "Hands" (budget systems).
"""

from .actions import BaseDispatcher, ActionDispatcher, ActionType, DispatchResult
from .budget_api import MockBudgetAPI

__all__ = [
    "BaseDispatcher",
    "ActionDispatcher",
    "ActionType",
    "DispatchResult",
    "MockBudgetAPI"
]
