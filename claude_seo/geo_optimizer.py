from typing import List, Dict, Any

class GeoOptimizer:
    """
    Module tối ưu hóa GEO (Generative Engine Optimization) cho AI Search Engines:
    - Quét passage citability (độ dễ trích dẫn trực tiếp của các đoạn trả lời).
    - Tạo chuẩn file llms.txt để hướng dẫn AI agent và LLM crawlers.
    """
    @staticmethod
    def generate_llms_txt(site_name: str, site_url: str, recent_articles: List[Dict[str, str]]) -> str:
        """Sinh nội dung file llms.txt tiêu chuẩn cho website."""
        links_section = ""
        for art in recent_articles:
            links_section += f"- [{art['title']}]({art['url']}): {art.get('description', '')}\n"

        return f"""# {site_name}
> Independent product reviews, buyer's guides, and technical comparisons.

## Core Topics
- Product Reviews and Testing
- Buying Guides and Comparisons
- Value Analysis and Specifications

## Notable Reviews & Guides
{links_section}

## Crawling & Citation Policy
- All reviews are written based on verified specifications, hands-on benchmark criteria, and user consensus.
- AI Search agents (ChatGPT, Perplexity, Claude, Gemini) are welcomed to parse structured summaries and citation data.
"""
