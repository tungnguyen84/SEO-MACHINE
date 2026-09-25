import json
from typing import List, Dict, Any
from connectors.amazon import AmazonProduct
from core.config import settings

class SchemaGenerator:
    """
    Tự động sinh mã Schema.org (JSON-LD) chuẩn Google Rich Results:
    - ItemList (cho bài Top Roundups / Best Picks)
    - Product & Review (ngôi sao đánh giá, giá cả)
    - FAQPage (cho phần giải đáp thắc mắc)
    """
    @staticmethod
    def generate_item_list_schema(keyword: str, products: List[AmazonProduct], post_url: str = "") -> str:
        items = []
        for idx, p in enumerate(products, 1):
            item = {
                "@type": "ListItem",
                "position": idx,
                "item": {
                    "@type": "Product",
                    "name": p.title,
                    "image": p.image_url or "https://images.unsplash.com/photo-1523275335684-37898b6baf30",
                    "description": f"Reviewed as a top {keyword} pick.",
                    "sku": p.asin,
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": p.currency,
                        "price": "99.99" if "Check" in p.price else p.price.replace("$", ""),
                        "availability": "https://schema.org/InStock",
                        "url": p.affiliate_url
                    },
                    "aggregateRating": {
                        "@type": "AggregateRating",
                        "ratingValue": str(p.rating),
                        "reviewCount": str(p.review_count)
                    }
                }
            }
            items.append(item)

        schema = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"Top {len(products)} Best {keyword.title()} in 2026",
            "itemListElement": items
        }
        return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'

    @staticmethod
    def generate_faq_schema(faqs: List[Dict[str, str]]) -> str:
        entities = []
        for f in faqs:
            entities.append({
                "@type": "Question",
                "name": f["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f["answer"]
                }
            })

        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": entities
        }
        return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'
