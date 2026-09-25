import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup

class EEATAuditor:
    """
    Module kiểm định chất lượng nội dung E-E-A-T và thuật toán chống Thin Affiliate của Google:
    1. Kiểm tra FTC Disclosure (Bắt buộc theo luật và nguyên tắc Google Search).
    2. Kiểm tra thuộc tính thẻ link affiliate (rel='nofollow sponsored').
    3. Đánh giá tính cân bằng (có cả ưu và nhược điểm thực tế).
    4. Quét từ ngữ sáo rỗng AI (Banned cliché words).
    5. Đếm số lượng từ và mật độ heading.
    """
    BANNED_WORDS = [
        "game-changer", "revolutionary", "in today's digital age",
        "without further ado", "look no further", "delve into", "testament to"
    ]

    @classmethod
    def audit_content(cls, html_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text()
        words = text.split()
        word_count = len(words)

        issues = []
        passed_checks = []

        # 1. FTC Disclosure check
        lower_text = text.lower()
        if "affiliate" in lower_text or "commission" in lower_text or "disclosure" in lower_text:
            passed_checks.append("FTC Affiliate Disclosure: Có hiển thị rõ ràng")
        else:
            issues.append("THIẾU: Không tìm thấy thông báo FTC Affiliate Disclosure ở đầu bài.")

        # 2. Affiliate Link Attributes
        links = soup.find_all("a")
        aff_links = [a for a in links if "amazon" in a.get("href", "") or "ebay" in a.get("href", "")]
        proper_links = 0
        for a in aff_links:
            rel = a.get("rel", [])
            rel_str = " ".join(rel) if isinstance(rel, list) else rel
            if "sponsored" in rel_str or "nofollow" in rel_str:
                proper_links += 1
        
        if aff_links:
            if proper_links == len(aff_links):
                passed_checks.append(f"Affiliate Links: {proper_links}/{len(aff_links)} link có thuộc tính rel='nofollow sponsored'")
            else:
                issues.append(f"CẢNH BÁO: Chỉ có {proper_links}/{len(aff_links)} link affiliate có thuộc tính sponsored/nofollow.")
        else:
            issues.append("CẢNH BÁO: Chưa tìm thấy link affiliate nào trong nội dung.")

        # 3. Pros and Cons check
        if "pros" in lower_text or "what we like" in lower_text or "advantages" in lower_text:
            if "cons" in lower_text or "points to consider" in lower_text or "drawbacks" in lower_text:
                passed_checks.append("E-E-A-T Balance: Có đủ bảng Ưu điểm và Nhược điểm (Pros/Cons)")
            else:
                issues.append("E-E-A-T YẾU: Có ưu điểm nhưng thiếu phần nhược điểm thực tế (Cons).")

        # 4. Banned AI Words
        found_banned = [w for w in cls.BANNED_WORDS if w in lower_text]
        if found_banned:
            issues.append(f"AI CLICHÉ: Phát hiện cụm từ sáo rỗng: {', '.join(found_banned)}")
        else:
            passed_checks.append("Văn phong tự nhiên: Không chứa cụm từ AI sáo rỗng thường gặp")

        # 5. Word count
        if word_count >= 1000:
            passed_checks.append(f"Độ dài bài viết: {word_count} từ (Đạt chuẩn in-depth review)")
        else:
            issues.append(f"Nội dung mỏng: Bài viết chỉ có {word_count} từ (Khuyến nghị >= 1,200 từ cho Best Roundups)")

        score = max(0, 100 - len(issues) * 15)

        return {
            "score": score,
            "word_count": word_count,
            "passed": passed_checks,
            "issues": issues,
            "is_ready_for_publish": score >= 70
        }
