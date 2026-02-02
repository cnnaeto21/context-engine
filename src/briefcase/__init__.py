"""
Briefcase Module

Assembles the "Briefcase of Truth" - structured context for Claude reasoning.
Contains current state, detected changes, and business rules.
"""

from .assembler import BriefcaseAssembler
from .templates import BriefcaseTemplates

__all__ = ["BriefcaseAssembler", "BriefcaseTemplates"]
