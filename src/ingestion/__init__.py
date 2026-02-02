"""
Ingestion Module

Handles PDF blueprint parsing and conversion to structured JSON.
Supports multiple parsing backends (Reducto.ai, Unstructured.io).
"""

from .parser import BlueprintParser

__all__ = ["BlueprintParser"]
