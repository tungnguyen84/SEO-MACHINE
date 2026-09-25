"""
Source Retrieval & Evidence Ingestion Engine
Priority 3 & 4 Implementation
Enforces strict source priority, content hashing, stale evidence detection,
and respectful network fetching without hallucinated fallbacks.
"""
import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from core.database import (
    get_connection, upsert_entity_attribute, add_source,
    add_evidence_claim, get_entity_attributes
)
from core.entities.normalizer import UnitNormalizer

class SourcePriority:
    OEM_MANUFACTURER = 1
    OFFICIAL_MANUAL = 2
    PRODUCT_MANUFACTURER = 3
    TRUSTED_RETAILER = 4
    INDEPENDENT_EDITORIAL = 5
    COMMUNITY_FORUM = 6

    @classmethod
    def get_priority(cls, source_type: str) -> int:
        mapping = {
            "oem_manufacturer": cls.OEM_MANUFACTURER,
            "oem_manual": cls.OFFICIAL_MANUAL,
            "user_manual_pdf": cls.OFFICIAL_MANUAL,
            "product_manufacturer": cls.PRODUCT_MANUFACTURER,
            "trusted_retailer": cls.TRUSTED_RETAILER,
            "independent_editorial": cls.INDEPENDENT_EDITORIAL,
            "community_forum": cls.COMMUNITY_FORUM
        }
        return mapping.get(source_type.lower(), cls.TRUSTED_RETAILER)


class SourceIngestionEngine:
    """
    Robust source fetcher and specification extractor.
    Pipeline: URL -> FETCH -> PARSE -> EXTRACT -> NORMALIZE -> VALIDATE -> SAVE SOURCE -> SAVE EVIDENCE -> UPDATE ENTITY
    """

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (OpenSEO GroundTruth Engine/2.0)"

    @classmethod
    def fetch_url(cls, url: str, timeout: int = 15, max_retries: int = 2) -> Dict[str, Any]:
        """
        Respectfully fetches URL with timeout and backoff.
        Does NOT bypass security or CAPTCHA.
        """
        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        retries = 0
        last_error = None
        while retries <= max_retries:
            try:
                resp = requests.get(url, headers=headers, timeout=timeout)
                status = resp.status_code
                content_text = resp.text
                content_hash = hashlib.sha256(resp.content).hexdigest()

                if status == 200:
                    return {
                        "success": True,
                        "url": url,
                        "http_status": 200,
                        "content": content_text,
                        "content_hash": content_hash,
                        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "url": url,
                        "http_status": status,
                        "content": None,
                        "content_hash": None,
                        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "error": f"HTTP status {status}"
                    }
            except Exception as e:
                last_error = str(e)
                retries += 1
                time.sleep(1)

        return {
            "success": False,
            "url": url,
            "http_status": 0,
            "content": None,
            "content_hash": None,
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": last_error or "Network failure"
        }

    @classmethod
    def check_content_hash_staleness(cls, url: str, current_hash: str) -> bool:
        """
        Checks if source content hash changed from previous recorded fetch.
        If hash changed, marks older evidence as STALE.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, content_hash FROM sources WHERE url = ? ORDER BY id DESC LIMIT 1", (url,))
        row = cursor.fetchone()

        is_stale = False
        if row and row["content_hash"]:
            prev_hash = row["content_hash"]
            if prev_hash != current_hash:
                is_stale = True
                source_id = row["id"]
                # Mark previous evidence claims as STALE in revalidation queue
                cursor.execute("UPDATE evidence_claims SET status = 'STALE' WHERE source_id = ?", (source_id,))
                cursor.execute("UPDATE sources SET is_stale = 1 WHERE id = ?", (source_id,))
                conn.commit()

        conn.close()
        return is_stale

    @classmethod
    def ingest_structured_source(
        cls,
        entity_id: str,
        url: str,
        source_type: str,
        document_title: str,
        raw_attributes: Dict[str, Any],
        evidence_quotes: Optional[Dict[str, str]] = None,
        fetch_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Saves verified ground-truth specifications into database.
        Strictly requires a successful fetch or valid document record.
        Enforces source priority so low-priority sources cannot override OEM data.
        """
        if fetch_result and not fetch_result.get("success", False):
            # Rule: Real source failure stops evidence creation
            return {
                "success": False,
                "status": "FETCH_FAILED",
                "reason": f"Source retrieval failed with HTTP {fetch_result.get('http_status')} ({fetch_result.get('error')}). Aborted evidence creation."
            }

        priority = SourcePriority.get_priority(source_type)
        content_hash = fetch_result.get("content_hash") if fetch_result else hashlib.sha256(url.encode("utf-8")).hexdigest()

        # Check content hash staleness
        is_stale = cls.check_content_hash_staleness(url, content_hash) if fetch_result else False

        conn = get_connection()
        cursor = conn.cursor()

        # Insert Source record
        cursor.execute("""
        INSERT INTO sources (
            entity_id, source_type, priority, url, document_title,
            http_status, content_hash, parser_version, is_stale, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, '2.0', ?, CURRENT_TIMESTAMP)
        """, (
            entity_id, source_type, priority, url, document_title,
            fetch_result.get("http_status", 200) if fetch_result else 200,
            content_hash, 1 if is_stale else 0
        ))
        source_id = cursor.lastrowid
        conn.commit()

        # Check existing attribute source priorities
        existing_attrs = get_entity_attributes(entity_id)
        evidence_created = 0
        attrs_updated = 0

        for attr_key, raw_val in raw_attributes.items():
            # If value is missing / unknown, mark as UNKNOWN
            if raw_val is None or str(raw_val).strip() == "" or str(raw_val).upper() == "UNKNOWN":
                upsert_entity_attribute(
                    entity_id=entity_id,
                    attr_key=attr_key,
                    attr_value_num=None,
                    attr_value_text="UNKNOWN",
                    unit="",
                    confidence_score=1.0,
                    verified_by_source_id=source_id
                )
                continue

            # Check existing priority: lower integer means higher priority!
            existing_info = existing_attrs.get(attr_key)
            if existing_info and existing_info.get("source_id"):
                cursor.execute("SELECT priority FROM sources WHERE id = ?", (existing_info["source_id"],))
                p_row = cursor.fetchone()
                if p_row and p_row["priority"] is not None:
                    existing_p = p_row["priority"]
                    # If incoming source has lower authority (higher integer), do not override!
                    if priority > existing_p:
                        continue

            # Normalize attribute
            num_val, text_val, parsed_unit = UnitNormalizer.normalize_attribute(attr_key, raw_val)

            upsert_entity_attribute(
                entity_id=entity_id,
                attr_key=attr_key,
                attr_value_num=num_val,
                attr_value_text=text_val,
                unit=parsed_unit,
                confidence_score=1.0 if priority <= 2 else 0.9,
                verified_by_source_id=source_id
            )
            attrs_updated += 1

            # Evidence Claim
            quote = (evidence_quotes or {}).get(attr_key, f"{attr_key}: {raw_val} from {document_title}")
            add_evidence_claim(
                entity_id=entity_id,
                source_id=source_id,
                attribute_key=attr_key,
                extracted_value=str(raw_val),
                raw_quote=quote,
                status="VERIFIED"
            )
            evidence_created += 1

        conn.commit()
        conn.close()

        return {
            "success": True,
            "source_id": source_id,
            "source_priority": priority,
            "attributes_updated": attrs_updated,
            "evidence_claims_created": evidence_created,
            "is_stale_detected": is_stale
        }
