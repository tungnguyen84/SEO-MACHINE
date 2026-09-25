import sys
import argparse
from typing import List

# Fix Unicode output on Windows PowerShell / CMD
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from connectors.wordpress import WordPressClient
from connectors.amazon import AmazonConnector
from pipeline.orchestrator import AffiliatePipelineOrchestrator
from core.config import settings

def test_wordpress():
    print(f"Kiểm tra kết nối tới WordPress: {settings.WP_URL} (User: {settings.WP_USERNAME})...")
    client = WordPressClient()
    res = client.test_connection()
    if res.get("success"):
        print(f"✅ Kết nối WordPress THÀNH CÔNG! Đăng nhập dưới quyền User: '{res.get('user')}' (ID: {res.get('id')})")
    else:
        print(f"❌ Kết nối WordPress THẤT BẠI: {res}")
        print("👉 Gợi ý: Hãy kiểm tra WP_URL, WP_USERNAME và WP_APP_PASSWORD trong file .env.")

def test_amazon(asin_or_url: str):
    print(f"Kiểm tra lấy thông tin sản phẩm Amazon từ: {asin_or_url}...")
    connector = AmazonConnector()
    prod = connector.get_product_details(asin_or_url)
    if prod:
        print("✅ Lấy dữ liệu sản phẩm thành công:")
        print(f"   - Tiêu đề: {prod.title}")
        print(f"   - ASIN: {prod.asin}")
        print(f"   - Giá: {prod.price}")
        print(f"   - Link Affiliate: {prod.affiliate_url}")
        print(f"   - Ảnh: {prod.image_url}")
        print(f"   - Tính năng ({len(prod.features)} items): {prod.features[:2]}")
    else:
        print("❌ Không lấy được dữ liệu sản phẩm.")

def run_single(keyword: str, asins: List[str], category: str, publish: bool, dry_run: bool = False):
    orchestrator = AffiliatePipelineOrchestrator()
    if dry_run:
        print(f"\n🧪 [CHẾ ĐỘ THỬ NGHIỆM - DRY RUN]: Không đẩy lên WordPress, xuất file HTML xem trước.")
    orchestrator.run_roundup_pipeline(
        keyword=keyword,
        product_asins_or_urls=asins,
        category_name=category,
        publish_immediately=publish,
        dry_run=dry_run
    )

def run_batch(csv_file: str, publish: bool):
    import csv
    print(f"📂 Đang đọc danh sách từ khóa từ {csv_file}...")
    orchestrator = AffiliatePipelineOrchestrator()
    with open(csv_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            kw = row.get("keyword", "").strip()
            asins = [a.strip() for a in row.get("asins", "").split(",") if a.strip()]
            cat = row.get("category", "General").strip()
            if kw and asins:
                print(f"\n=======================================================")
                print(f"👉 Đang xử lý: '{kw}' với {len(asins)} sản phẩm...")
                orchestrator.run_roundup_pipeline(
                    keyword=kw,
                    product_asins_or_urls=asins,
                    category_name=cat,
                    publish_immediately=publish
                )

def main():
    parser = argparse.ArgumentParser(
        description="OpenSEO + SEOMachine + Claude-SEO: Hệ thống Affiliate Website Tự Động Hóa"
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    # Lệnh test-wp
    subparsers.add_parser("test-wp", help="Kiểm tra kết nối WordPress REST API")

    # Lệnh test-amazon
    parser_amz = subparsers.add_parser("test-amazon", help="Kiểm tra trích xuất sản phẩm và link affiliate Amazon")
    parser_amz.add_argument("asin_or_url", help="ASIN hoặc link sản phẩm Amazon")

    # Lệnh generate (bài đơn)
    parser_gen = subparsers.add_parser("generate", help="Tự động sinh bài viết và đăng lên WordPress")
    parser_gen.add_argument("--keyword", required=True, help="Từ khóa mục tiêu (ví dụ: 'ergonomic office chairs')")
    parser_gen.add_argument("--asins", required=True, help="Danh sách ASIN hoặc link Amazon, cách nhau bởi dấu phẩy")
    parser_gen.add_argument("--category", default="Buying Guides", help="Chuyên mục trên WordPress")
    parser_gen.add_argument("--publish", action="store_true", help="Đăng công khai ngay lập tức (mặc định là lưu Draft)")
    parser_gen.add_argument("--dry-run", action="store_true", help="Chỉ sinh bài viết và lưu file HTML xem trước, không đăng lên WP")

    # Lệnh batch (chạy danh sách CSV)
    parser_batch = subparsers.add_parser("batch", help="Chạy hàng loạt từ khóa từ file CSV")
    parser_batch.add_argument("--file", required=True, help="Đường dẫn file CSV (ví dụ: topics.example.csv)")
    parser_batch.add_argument("--publish", action="store_true", help="Đăng công khai ngay lập tức")

    # Lệnh find-keywords (tìm từ khóa đuôi dài)
    parser_kw = subparsers.add_parser("find-keywords", help="Tìm từ khóa đuôi dài (Long-tail Buyer Intent) từ Google & Amazon")
    parser_kw.add_argument("seed", help="Từ khóa gốc (ví dụ: 'office chair', 'air purifier')")
    parser_kw.add_argument("--limit", type=int, default=25, help="Số lượng từ khóa tối đa cần tìm (mặc định: 25)")
    parser_kw.add_argument("--output", default="", help="Tên file CSV xuất ra (ví dụ: 'my_keywords.csv')")

    # Lệnh analyze-product (phân tích ngược từ URL/ASIN Amazon)
    parser_prod = subparsers.add_parser("analyze-product", help="Phân tích link Amazon: Tìm keyword, đo lượng search, độ cạnh tranh & gợi ý từ khóa nên viết bài")
    parser_prod.add_argument("url_or_asin", help="URL sản phẩm hoặc mã ASIN Amazon")

    # Lệnh mine-reviews (Khai thác sentiment đánh giá Amazon)
    parser_mine = subparsers.add_parser("mine-reviews", help="Khai thác đánh giá người mua thật trên Amazon (Praises, Complaints, Quotes)")
    parser_mine.add_argument("asin", help="ASIN hoặc link sản phẩm Amazon")

    # Lệnh cloak (Tạo link bọc an toàn /go/slug)
    parser_cloak = subparsers.add_parser("cloak", help="Tạo link bọc /go/slug an toàn chống adblocker")
    parser_cloak.add_argument("--slug", required=True, help="Slug rút gọn (ví dụ: 'sony-xm5')")
    parser_cloak.add_argument("--url", required=True, help="URL affiliate đích (Amazon/eBay)")
    parser_cloak.add_argument("--title", default="", help="Tên sản phẩm / Ghi chú")

    # Lệnh ui (khởi chạy Web Dashboard)
    parser_ui = subparsers.add_parser("ui", help="Mở giao diện Web Dashboard trên trình duyệt")
    parser_ui.add_argument("--port", type=int, default=8000, help="Cổng chạy Web UI (mặc định: 8000)")

    args = parser.parse_args()

    if args.command == "ui":
        import uvicorn
        print(f"\n==================================================================")
        print(f"🌐 KHỞI ĐỘNG GIAO DIỆN WEB DASHBOARD")
        print(f"👉 Mở trình duyệt tại: http://localhost:{args.port}")
        print(f"👉 Nhấn Ctrl + C để dừng.")
        print(f"==================================================================\n")
        uvicorn.run("server:app", host="127.0.0.1", port=args.port, reload=False)
    elif args.command == "test-wp":
        test_wordpress()
    elif args.command == "test-amazon":
        test_amazon(args.asin_or_url)
    elif args.command == "generate":
        asin_list = [a.strip() for a in args.asins.split(",") if a.strip()]
        run_single(args.keyword, asin_list, args.category, args.publish, args.dry_run)
    elif args.command == "batch":
        run_batch(args.file, args.publish)
    elif args.command == "find-keywords":
        from research.longtail import LongtailKeywordFinder
        finder = LongtailKeywordFinder()
        kws = finder.find_buyer_keywords(args.seed, max_results=args.limit)
        print(f"\n🎯 TÌM THẤY {len(kws)} TỪ KHÓA ĐUÔI DÀI:")
        print(f"{'-'*75}")
        for i, k in enumerate(kws, 1):
            print(f"{i:2d}. [{k.intent:20s}] {k.keyword} ({k.source})")
        print(f"{'-'*75}")
        if args.output:
            finder.export_to_csv(kws, args.output)
        else:
            default_out = f"keywords_{args.seed.replace(' ', '_')}.csv"
            finder.export_to_csv(kws, default_out)
    elif args.command == "analyze-product":
        from research.product_advisor import ProductKeywordAdvisor
        advisor = ProductKeywordAdvisor()
        res = advisor.analyze_product_url(args.url_or_asin)
        if not res.get("success"):
            print(f"❌ Lỗi: {res.get('error')}")
            return

        prod = res["product"]
        print(f"\n==========================================================================================")
        print(f"🔎 PHÂN TÍCH TIỀM NĂNG TỪ KHÓA TỪ SẢN PHẨM AMAZON")
        print(f"==========================================================================================")
        print(f"📌 Sản phẩm: {prod.title}")
        print(f"💰 Giá: {prod.price} | ASIN: {prod.asin}")
        print(f"🔗 Link Aff đã gắn Tag: {prod.affiliate_url}")
        print(f"\n📋 DANH SÁCH TỪ KHÓA & CHỈ SỐ CẠNH TRANH:")
        print(f"{'-'*95}")
        print(f"{'STT':<4} | {'Từ khóa tiềm năng':<38} | {'Volume/tháng':<16} | {'Cạnh tranh':<15} | {'Điểm cơ hội':<10}")
        print(f"{'-'*95}")
        for idx, o in enumerate(res["opportunities"], 1):
            star = "⭐ " if idx == 1 else "   "
            print(f"{star}{idx:<2} | {o.keyword:<38} | {o.search_volume:<16} | {o.competition:<15} | {o.opportunity_score}/100")
        print(f"{'-'*95}")

        print(f"\n💡 CHIẾN LƯỢC & ĐỀ XUẤT VIẾT BÀI:")
        print(f"👉 {res['recommendation_reason']}")
        print(f"\n🚀 LỆNH ĐỂ SINH BÀI VIẾT NGAY CHO TỪ KHÓA ĐƯỢC ĐỀ XUẤT:")
        rec_kw = res["recommended_keyword"]
        asin = prod.asin
        print(f'python main.py generate --keyword "{rec_kw}" --asins "{asin}" --category "Product Reviews"')
        print(f"==========================================================================================\n")
    elif args.command == "mine-reviews":
        from saas_affiliate.sentiment_miner import AmazonReviewSentimentMiner
        miner = AmazonReviewSentimentMiner()
        res = miner.mine_sentiment_for_asin(args.asin)
        print(f"\n==========================================================================================")
        print(f"🎯 KẾT QUẢ KHAI THÁC ĐÁNH GIÁ NGƯỜI MUA THẬT (ASIN: {res['asin']})")
        print(f"==========================================================================================")
        print(f"⭐ Đánh giá: {res['rating']}/5.0 | Điểm Sentiment: {int(res['sentiment_score']*100)}% Hài lòng")
        print(f"\n👍 ĐIỂM NGƯỜI DÙNG KHEN NGỢI (PRAISES):")
        for p in res.get("praises", []):
            print(f"   ✓ {p}")
        print(f"\n⚠️ NHƯỢC ĐIỂM / LỖI BỊ PHÀN NÀN (DEALBREAKERS):")
        for c in res.get("complaints", []):
            print(f"   ✕ {c}")
        print(f"\n💬 TRÍCH DẪN KHÁCH HÀNG THỰC TẾ:")
        for q in res.get("verified_quotes", []):
            print(f"   • {q}")
        print(f"==========================================================================================\n")
    elif args.command == "cloak":
        from saas_affiliate.link_cloaker import LinkCloaker
        res = LinkCloaker.create_cloaked_link(1, args.slug, args.title or args.slug, args.url)
        print(f"\n✅ ĐÃ TẠO LINK BỌC AFFILIATE THÀNH CÔNG:")
        print(f"   🔗 Slug Link: http://localhost:8000/go/{res['slug']}")
        print(f"   🎯 Đích đến: {res['destination_url']}")
        print(f"   📊 Đếm Click: Tự động kích hoạt khi có người dùng truy cập.\n")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
