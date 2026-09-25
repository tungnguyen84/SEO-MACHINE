"""
Tests for WordPress Safe Publish Gate and Metadata Mapping
Priority 7 Verification
"""
import pytest
from unittest.mock import patch, MagicMock
from core.database import init_db, get_connection
from core.config import settings
from connectors.wordpress import WordPressClient

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_wordpress_default_draft():
    """
    Test that default publishing status is strictly 'draft' when AUTO_PUBLISH is False,
    even if the caller attempts to pass 'publish'.
    """
    assert settings.AUTO_PUBLISH is False

    client = WordPressClient(url="https://test-site.local", username="admin", password="password")

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": 9901,
            "link": "https://test-site.local/?p=9901",
            "status": "draft"
        }
        mock_post.return_value = mock_resp

        # Caller attempts to publish
        res = client.create_post(
            title="Subaru Outback Camping Setup",
            content="Grounded content with verified specs",
            status="publish"  # Should be overridden to 'draft'!
        )

        assert res["success"] is True
        # Verify the actual payload sent to WordPress REST API
        call_args = mock_post.call_args
        sent_payload = call_args[1]["json"]
        assert sent_payload["status"] == "draft", "AUTO_PUBLISH=False must force status to 'draft'"

def test_wordpress_metadata_mapping():
    """
    Test that WordPress synchronization mapping is properly recorded in articles table:
    local_article_id, wordpress_post_id, wordpress_url, page_type,
    primary_entity_id, quality_score, quality_decision, last_verified_at.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO articles (title, keyword, status)
    VALUES ('Subaru Outback Guide', 'subaru outback camping', 'draft')
    """)
    local_id = cursor.lastrowid
    conn.commit()
    conn.close()

    WordPressClient.save_wordpress_metadata(
        local_article_id=local_id,
        wordpress_post_id=9901,
        wordpress_url="https://test-site.local/subaru-outback-guide",
        page_type="compatibility_guide",
        primary_entity_id="car_subaru_outback_2025",
        quality_score=92.5,
        quality_decision="INDEX"
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles WHERE id = ?", (local_id,))
    row = dict(cursor.fetchone())
    conn.close()

    assert row["wp_post_id"] == 9901
    assert row["wp_link"] == "https://test-site.local/subaru-outback-guide"
    assert row["page_type"] == "compatibility_guide"
    assert row["primary_entity_id"] == "car_subaru_outback_2025"
    assert row["quality_score"] == 92.5
    assert row["quality_decision"] == "INDEX"
    assert row["last_verified_at"] is not None
