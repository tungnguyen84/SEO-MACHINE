"""
Google Search Console Real Sync Engine & Daily Metric Storage
Priority 8 Implementation
Maintains historical daily time-series without overwriting past dates.
Provides 7d, 28d, and 90d window aggregations.
"""
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from core.database import get_connection

class GSCClient:
    """
    Manages GSC metric ingestion, historical persistence, and time-window aggregations.
    """

    @classmethod
    def record_daily_metric(
        cls,
        page_url: str,
        query: str,
        impressions: int,
        clicks: int,
        ctr: float,
        position: float,
        recorded_date: str,  # YYYY-MM-DD
        workspace_id: int = 1
    ) -> int:
        """
        Inserts a daily metric row.
        Ensures historical data is NEVER overwritten for past dates.
        If a record for the exact same date already exists, updates it safely.
        """
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id FROM gsc_metrics
        WHERE page_url = ? AND query = ? AND recorded_date = ?
        """, (page_url, query, recorded_date))
        row = cursor.fetchone()

        if row:
            metric_id = row[0]
            cursor.execute("""
            UPDATE gsc_metrics SET
                impressions = ?,
                clicks = ?,
                ctr = ?,
                position = ?
            WHERE id = ?
            """, (impressions, clicks, ctr, position, metric_id))
        else:
            cursor.execute("""
            INSERT INTO gsc_metrics (
                workspace_id, page_url, query, impressions,
                clicks, ctr, position, recorded_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (workspace_id, page_url, query, impressions, clicks, ctr, position, recorded_date))
            metric_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return metric_id

    @classmethod
    def get_aggregated_metrics(
        cls,
        page_url: str,
        query: Optional[str] = None,
        days: int = 28
    ) -> Dict[str, Any]:
        """
        Aggregates clicks, impressions, CTR, and average position across a window: 7d, 28d, or 90d.
        """
        conn = get_connection()
        cursor = conn.cursor()

        cutoff_date = (date.today() - timedelta(days=days)).isoformat()

        if query:
            cursor.execute("""
            SELECT
                SUM(impressions) as total_imp,
                SUM(clicks) as total_clicks,
                AVG(position) as avg_pos,
                COUNT(*) as days_recorded
            FROM gsc_metrics
            WHERE page_url = ? AND query = ? AND recorded_date >= ?
            """, (page_url, query, cutoff_date))
        else:
            cursor.execute("""
            SELECT
                SUM(impressions) as total_imp,
                SUM(clicks) as total_clicks,
                AVG(position) as avg_pos,
                COUNT(*) as days_recorded
            FROM gsc_metrics
            WHERE page_url = ? AND recorded_date >= ?
            """, (page_url, cutoff_date))

        row = cursor.fetchone()
        conn.close()

        total_imp = (row[0] or 0) if row else 0
        total_clicks = (row[1] or 0) if row else 0
        avg_pos = round(row[2], 1) if (row and row[2] is not None) else 0.0
        ctr = round((total_clicks / total_imp * 100.0), 2) if total_imp > 0 else 0.0
        days_recorded = (row[3] or 0) if row else 0

        return {
            "page_url": page_url,
            "query": query,
            "window_days": days,
            "days_recorded": days_recorded,
            "total_impressions": total_imp,
            "total_clicks": total_clicks,
            "average_position": avg_pos,
            "ctr_percent": ctr,
            "provenance": "REAL"
        }

    @classmethod
    def get_distinct_historical_dates(cls, page_url: str, query: str) -> List[str]:
        """Returns the distinct dates recorded for a given URL and query."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT DISTINCT recorded_date FROM gsc_metrics
        WHERE page_url = ? AND query = ?
        ORDER BY recorded_date ASC
        """, (page_url, query))
        dates = [r[0] for r in cursor.fetchall()]
        conn.close()
        return dates

    @classmethod
    def process_api_sync_result(
        cls,
        api_status_code: int,
        response_payload: Optional[Dict[str, Any]],
        page_url: str,
        target_date: str,
        workspace_id: int = 1
    ) -> Dict[str, Any]:
        """
        Processes GSC API responses and differentiates:
        - FETCH_FAILED: HTTP 401 (OAuth expired), 429 (quota), 5xx -> keeps existing historical data intact!
        - ZERO_DATA: valid API response where impressions == 0 and clicks == 0 (query got impressions: 0)
        - NO_DATA: valid empty API response (e.g. query not in index or no rows returned)
        """
        if api_status_code in [401, 403]:
            return {
                "status": "FETCH_FAILED",
                "reason": "OAuth token expired or insufficient permissions",
                "action": "PRESERVED_HISTORICAL_DATA",
                "rows_ingested": 0
            }
        elif api_status_code in [429, 500, 502, 503]:
            return {
                "status": "FETCH_FAILED",
                "reason": f"API server error or rate limited (HTTP {api_status_code})",
                "action": "PRESERVED_HISTORICAL_DATA",
                "rows_ingested": 0
            }
        elif not response_payload or "rows" not in response_payload or not response_payload["rows"]:
            return {
                "status": "NO_DATA",
                "reason": "Search Console API returned no rows for this query/date window",
                "action": "RECORD_NO_DATA",
                "rows_ingested": 0
            }

        ingested = 0
        for r in response_payload["rows"]:
            imp = r.get("impressions", 0)
            clicks = r.get("clicks", 0)
            ctr = r.get("ctr", 0.0)
            pos = r.get("position", 0.0)
            query = r.get("keys", [None])[0] if "keys" in r else r.get("query", "unknown")
            cls.record_daily_metric(page_url, query, imp, clicks, ctr, pos, target_date, workspace_id=workspace_id)
            ingested += 1

        return {
            "status": "SUCCESS" if ingested > 0 else "ZERO_DATA",
            "rows_ingested": ingested
        }
