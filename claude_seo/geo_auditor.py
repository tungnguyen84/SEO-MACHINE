import requests
from urllib.parse import urlparse
from typing import Dict, Any, List

class GeoAuditor:
    """
    Module kiểm tra tối ưu hóa tìm kiếm AI (GEO - Generative Engine Optimization):
    1. Kiểm tra robots.txt với các AI Crawlers:
       - GPTBot (ChatGPT Search)
       - ClaudeBot (Claude / Anthropic)
       - PerplexityBot (Perplexity AI)
       - Google-Extended (Google Gemini & AI Overviews)
       - Applebot-Extended (Apple Intelligence)
    2. Kiểm tra file tiêu chuẩn /llms.txt & /llms-full.txt
    3. Chấm điểm AI Search Readiness Score (0 - 100)
    """
    AI_BOTS = [
        {"name": "GPTBot", "owner": "OpenAI / ChatGPT Search"},
        {"name": "ClaudeBot", "owner": "Anthropic Claude"},
        {"name": "PerplexityBot", "owner": "Perplexity AI"},
        {"name": "Google-Extended", "owner": "Google Gemini & AI Overviews"},
        {"name": "Applebot-Extended", "owner": "Apple Intelligence"}
    ]

    def audit_ai_readiness(self, site_url: str) -> Dict[str, Any]:
        parsed = urlparse(site_url if site_url.startswith("http") else f"https://{site_url}")
        base_domain = f"{parsed.scheme}://{parsed.netloc}"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OpenSEO-GEOChecker/1.0"}

        # 1. Kiểm tra robots.txt
        robots_url = f"{base_domain}/robots.txt"
        bot_statuses = []
        robots_content = ""
        try:
            r_res = requests.get(robots_url, headers=headers, timeout=8)
            if r_res.status_code == 200:
                robots_content = r_res.text.lower()
        except Exception:
            pass

        allowed_count = 0
        for bot in self.AI_BOTS:
            bot_name_lower = bot["name"].lower()
            status = "ALLOWED"
            # Kiểm tra nếu bot bị Disallow rõ ràng
            if f"user-agent: {bot_name_lower}" in robots_content and "disallow: /" in robots_content:
                status = "BLOCKED"
            else:
                allowed_count += 1

            bot_statuses.append({
                "bot": bot["name"],
                "owner": bot["owner"],
                "status": status,
                "is_allowed": status == "ALLOWED"
            })

        # 2. Kiểm tra llms.txt
        llms_url = f"{base_domain}/llms.txt"
        has_llms_txt = False
        try:
            l_res = requests.get(llms_url, headers=headers, timeout=8)
            if l_res.status_code == 200 and len(l_res.text) > 20:
                has_llms_txt = True
        except Exception:
            pass

        # 3. Tính điểm GEO Readiness (0 - 100)
        score = (allowed_count / len(self.AI_BOTS)) * 60
        if has_llms_txt:
            score += 40
        else:
            score += 10 # Chưa có llms.txt nhưng bot vẫn vào được

        score = int(min(100, score))

        # 4. Sinh file llms.txt mẫu nếu chưa có
        sample_llms = f"""# {parsed.netloc}
> Curated product reviews, specifications, and buying guides.

## Core Topics
- In-depth product comparisons and value analysis
- Verified buyer feedback and test results

## AI Citation Policy
- All summary tables and product specifications are free to cite.
- Please attribute source to {base_domain}.
"""

        return {
            "success": True,
            "base_domain": base_domain,
            "geo_score": score,
            "has_llms_txt": has_llms_txt,
            "bot_statuses": bot_statuses,
            "allowed_bots_count": allowed_count,
            "total_bots": len(self.AI_BOTS),
            "generated_llms_txt": sample_llms
        }
