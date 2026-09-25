import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime

class SocialWebhookDispatcher:
    """
    Module Tự Động Hóa Đa Kênh (Social Media Webhook Syndication)
    - Tự động phát tín hiệu Webhook tới Make.com / Zapier / n8n / Pabbly khi có:
      1. Bài viết mới xuất bản thành công (Article Published)
      2. Video ngắn 9:16 vừa hoàn thành render (Short Video Created)
    - Giúp kết nối tự động đăng lên: Facebook Fanpage/Reels, YouTube Shorts, TikTok, Pinterest, Twitter/X, Telegram Channel.
    """

    @classmethod
    def test_webhook(cls, webhook_url: str) -> Dict[str, Any]:
        """Gửi gói tin thử nghiệm để kiểm tra kết nối Webhook."""
        payload = {
            "event": "test_ping",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "OpenSEO SaaS Suite",
            "message": "🎉 Kết nối Webhook thành công! OpenSEO sẵn sàng tự động đồng bộ bài viết & video lên mạng xã hội.",
            "sample_data": {
                "title": "Top 5 Best Espresso Machines for Home Baristas (2026)",
                "url": "https://your-affiliate-site.com/best-espresso-machines",
                "summary": "Review chi tiết 5 máy pha cà phê bán chạy nhất cùng ưu nhược điểm thực tế.",
                "hashtags": ["#affiliate", "#coffee", "#homebarista", "#reviews"]
            }
        }
        return cls._dispatch(webhook_url, payload)

    @classmethod
    def send_article_published(cls, webhook_url: str, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """Bắn dữ liệu bài viết mới tới Make/Zapier để auto-post lên Fanpage / Twitter / Pinterest."""
        payload = {
            "event": "article_published",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "OpenSEO SaaS",
            "title": article_data.get("title", ""),
            "url": article_data.get("link") or article_data.get("wp_link", ""),
            "keyword": article_data.get("keyword", ""),
            "slug": article_data.get("slug", ""),
            "featured_image": article_data.get("featured_image", ""),
            "summary": article_data.get("summary", ""),
            "category": article_data.get("category", "Affiliate Reviews"),
            "hashtags": [
                f"#{article_data.get('keyword', 'shopping').replace(' ', '')}",
                "#affiliate",
                "#reviews",
                "#deals2026"
            ]
        }
        return cls._dispatch(webhook_url, payload)

    @classmethod
    def send_video_created(cls, webhook_url: str, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Bắn dữ liệu video short mới tới Make/Zapier để auto-post lên Facebook Reels / YouTube Shorts."""
        payload = {
            "event": "video_created",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "OpenSEO AI Video Engine",
            "title": video_data.get("title", ""),
            "video_url": video_data.get("video_url", ""),
            "video_path": video_data.get("video_path", ""),
            "caption": video_data.get("caption", ""),
            "blog_url": video_data.get("blog_url", ""),
            "hashtags": video_data.get("hashtags", ["#shorts", "#reels", "#fyp", "#shopping"]),
            "duration": video_data.get("duration", 0)
        }
        return cls._dispatch(webhook_url, payload)

    @classmethod
    def _dispatch(cls, webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not webhook_url or not webhook_url.startswith("http"):
            return {"success": False, "error": "URL Webhook không hợp lệ (cần bắt đầu bằng http:// hoặc https://)"}

        try:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "OpenSEO-AutoSyndicate-Bot/2.0"
            }
            res = requests.post(webhook_url, json=payload, headers=headers, timeout=12)
            is_success = res.status_code in [200, 201, 202, 204]
            return {
                "success": is_success,
                "status_code": res.status_code,
                "response_text": res.text[:300] if res.text else "OK",
                "message": "Đã gửi dữ liệu Webhook thành công!" if is_success else f"Webhook trả về HTTP {res.status_code}"
            }
        except Exception as e:
            return {"success": False, "error": f"Lỗi kết nối Webhook: {str(e)}"}
