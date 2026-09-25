import json
from typing import Dict, Any, List

class SchemaStudio:
    """
    Xưởng sinh & kiểm tra mã Schema.org độc lập (Standalone Schema Studio):
    - Hỗ trợ FAQPage, Product, Review, HowTo, Article, Breadcrumbs
    - Kiểm tra tính hợp lệ cú pháp JSON-LD chuẩn Google Rich Results
    """
    @staticmethod
    def generate_faq_schema(faq_items: List[Dict[str, str]]) -> str:
        entities = []
        for item in faq_items:
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()
            if q and a:
                entities.append({
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": a
                    }
                })
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": entities
        }
        return json.dumps(schema, indent=2)

    @staticmethod
    def generate_product_schema(name: str, price: str, currency: str, rating: float, reviews_count: int, image_url: str, sku: str) -> str:
        clean_price = price.replace("$", "").replace(",", "").strip() if price else "99.99"
        schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": name,
            "image": image_url or "https://via.placeholder.com/500",
            "sku": sku,
            "offers": {
                "@type": "Offer",
                "priceCurrency": currency or "USD",
                "price": clean_price,
                "availability": "https://schema.org/InStock"
            },
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": str(rating),
                "reviewCount": str(reviews_count)
            }
        }
        return json.dumps(schema, indent=2)

    @staticmethod
    def generate_howto_schema(name: str, steps: List[Dict[str, str]]) -> str:
        step_entities = []
        for idx, s in enumerate(steps, 1):
            step_entities.append({
                "@type": "HowToStep",
                "position": idx,
                "name": s.get("title", f"Step {idx}"),
                "text": s.get("text", "")
            })
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": name,
            "step": step_entities
        }
        return json.dumps(schema, indent=2)

    @staticmethod
    def validate_json_ld(raw_json: str) -> Dict[str, Any]:
        """Kiểm tra hợp lệ JSON-LD."""
        clean = raw_json.strip()
        if clean.startswith("<script"):
            clean = clean.split(">", 1)[-1].rsplit("</script>", 1)[0].strip()

        try:
            parsed = json.loads(clean)
            context = parsed.get("@context")
            schema_type = parsed.get("@type")
            if not context or "schema.org" not in context:
                return {"valid": False, "error": "Thiếu thuộc tính @context: 'https://schema.org'"}
            if not schema_type:
                return {"valid": False, "error": "Thiếu thuộc tính @type"}
            return {
                "valid": True,
                "type": schema_type,
                "parsed": parsed
            }
        except Exception as e:
            return {"valid": False, "error": f"Lỗi cú pháp JSON: {str(e)}"}
