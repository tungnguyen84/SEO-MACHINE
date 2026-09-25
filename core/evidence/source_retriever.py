"""
Source Retriever & Document Processor
Loads manufacturer documentation, spec sheets, and PDF user manuals to populate verified evidence.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.database import add_source, add_evidence_claim
from .claim_extractor import ClaimExtractor
from core.entities.entity_manager import EntityManager

class SourceRetriever:
    """Document ingestor and evidence claim generator."""

    @classmethod
    def ingest_text_document(
        cls,
        entity_id: str,
        document_title: str,
        content: str,
        source_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a text document, creates a source entry, extracts claims, and updates entity specs.
        """
        source_id = add_source(
            entity_id=entity_id,
            source_type="official_spec_sheet",
            url=source_url,
            document_title=document_title
        )

        extracted = ClaimExtractor.extract_claims_from_text(content)
        saved_claims = []

        for item in extracted:
            # Register in evidence_claims
            claim_id = add_evidence_claim(
                entity_id=entity_id,
                source_id=source_id,
                attribute_key=item["attribute_key"],
                extracted_value=item["normalized_text"],
                raw_quote=item["raw_quote"],
                page_number=item.get("page_number"),
                status="VERIFIED"
            )
            # Update entity_attribute directly
            EntityManager.add_verified_attribute(
                entity_id=entity_id,
                attr_key=item["attribute_key"],
                raw_value=item["normalized_num"] if item["normalized_num"] is not None else item["normalized_text"],
                unit=item["unit"],
                source_id=source_id,
                evidence_quote=item["raw_quote"]
            )
            saved_claims.append({
                "claim_id": claim_id,
                "key": item["attribute_key"],
                "value": item["normalized_text"],
                "quote": item["raw_quote"]
            })

        return {
            "source_id": source_id,
            "document_title": document_title,
            "claims_extracted_count": len(saved_claims),
            "claims": saved_claims
        }
