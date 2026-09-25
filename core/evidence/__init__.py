"""
OpenSEO Evidence & Source Retrieval Module
Manages factual sources, technical PDF data extraction, and claim citations.
"""
from .claim_extractor import ClaimExtractor
from .source_retriever import SourceRetriever

__all__ = ["ClaimExtractor", "SourceRetriever"]
