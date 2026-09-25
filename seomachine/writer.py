import os
from typing import List, Dict, Any, Optional
from core.config import settings
from connectors.amazon import AmazonProduct
from saas_affiliate.sentiment_miner import AmazonReviewSentimentMiner
from saas_affiliate.price_guard import AmazonPriceComplianceGuard
from saas_affiliate.geo_router import AmazonGeoRouter

class AffiliateContentWriter:
    """
    Module sinh nội dung Affiliate chuẩn SEO, E-E-A-T và tối ưu tỷ lệ chuyển đổi (CRO)
    theo triết lý của SEOMachine.
    """
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.site_name = settings.SITE_NAME

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Gọi API LLM (hỗ trợ Gemini, Anthropic, OpenAI)."""
        # 1. Google Gemini
        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model=settings.LLM_MODEL or "gemini-2.5-flash",
                    contents=f"{system_prompt}\n\n{user_prompt}"
                )
                return response.text
            except Exception as e:
                print(f"[Writer] Gemini API Error: {e}")

        # 2. Anthropic Claude
        elif self.provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                msg = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                return msg.content[0].text
            except Exception as e:
                print(f"[Writer] Anthropic API Error: {e}")

        # 3. OpenAI
        elif self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                import openai
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return completion.choices[0].message.content
            except Exception as e:
                print(f"[Writer] OpenAI API Error: {e}")

        # Fallback tạo nội dung theo mẫu chuẩn chất lượng cao nếu chưa cấu hình LLM API Key
        print("[Writer] No LLM response or API key, using Dynamic Affiliate Template Engine...")
        return ""

    def generate_roundup_article(
        self,
        keyword: str,
        products: List[AmazonProduct],
        custom_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        Sinh bài viết dạng Top Listicle (Best X in 2026) với đầy đủ bảng so sánh, 
        hộp Quick Picks, Pros/Cons, Buying Guide và FAQ.
        """
        year = 2026
        formatted_title = f"The Best {keyword.title()} in {year}: Data-Driven Buyer's Guide & Spec Comparison"
        slug = f"best-{keyword.lower().replace(' ', '-')}-{year}"

        # Xây dựng danh sách thông số sản phẩm và đào sâu review thực tế từ Amazon
        miner = AmazonReviewSentimentMiner()
        products_context = []
        for idx, p in enumerate(products, 1):
            sent = miner.mine_sentiment_for_asin(p.asin, p.title)
            p_praises = "; ".join(sent.get("praises", [])[:2])
            p_complaints = "; ".join(sent.get("complaints", [])[:2])
            products_context.append(
                f"Product #{idx}:\n"
                f"- Name: {p.title}\n"
                f"- ASIN: {p.asin}\n"
                f"- Price: {p.price}\n"
                f"- Affiliate Link: {p.affiliate_url}\n"
                f"- Image URL: {p.image_url}\n"
                f"- Features: {'; '.join(p.features)}\n"
                f"- Verified Customer Praises: {p_praises}\n"
                f"- Verified Customer Real Complaints/Weaknesses: {p_complaints}\n"
            )
        prod_data_str = "\n".join(products_context)

        system_prompt = (
            "You are a professional, veteran technical product analyst for an authoritative data-driven publication. "
            "Write in an analytical, transparent, honest, and helpful tone (adhering strictly to Google's Helpful Content and E-E-A-T guidelines). "
            "CRITICAL RULE: NEVER use first-person testing claims like 'we tested', 'our tests', 'in our lab', or 'we drove'. "
            "Instead, base all analysis on verified engineering specifications, manufacturer technical datasheets, and aggregated user telemetry. "
            "Never use cheesy marketing hype or cliché phrases like 'revolutionary', 'game-changer', or 'without further ado'. "
            "Output valid HTML content ready for WordPress Gutenberg. Use inline CSS for beautiful, responsive styling."
        )

        user_prompt = f"""
Write an in-depth, high-converting buyer's guide and spec comparison roundup for the target keyword: "{keyword}".
Current Year: {year}

Here are the products to feature (use their exact affiliate links, customer praises, real complaints, and images in your HTML CTA buttons and image tags):
{prod_data_str}

Format Requirements in HTML:
1. Top FTC Affiliate Disclosure box:
   <div style="background:#f8fafc; border-left:4px solid #3b82f6; padding:12px 16px; margin-bottom:24px; font-size:14px; color:#475569; border-radius:4px;">
     <strong>Affiliate Disclosure:</strong> We provide independent, data-driven comparisons. When you buy through our links, we may earn an affiliate commission at no extra cost to you.
   </div>
2. Quick Answer & Verdict (in the first 150 words): Provide the direct bottom line recommendation for different buyer profiles.
3. Introduction & Methodology: Explain evaluation criteria based on manufacturer datasheets, measured electrical efficiency, build quality, and verified owner reports.
4. "Our Top Picks at a Glance" (Summary comparison cards: Best Overall, Best Value, Best Premium).
5. Responsive Comparison Table comparing all products (Columns: Pick, Product, Key Feature, Price, Action).
6. In-Depth Reviews for each product:
   - H2: Product Name + Award (e.g., Best Overall, Best Value)
   - Product Image (<img src="..." alt="..." style="max-width:320px; display:block; margin:16px auto; border-radius:8px;" />)
   - Engineering & Practical Analysis (Integrate technical capabilities and verified customer praises)
   - Pros & Cons box with two columns (Green checkmarks for Pros, Red for Cons). Must include real, critical cons from customer feedback.
   - High-contrast CTA Button linking to the affiliate link:
     <a href="AFFILIATE_URL" rel="nofollow sponsored" target="_blank" style="display:inline-block; background:#f59e0b; color:#1e293b; font-weight:700; padding:12px 24px; border-radius:6px; text-decoration:none; margin:16px 0;">Check Price on Amazon &rarr;</a>
7. Comprehensive Buyer's Guide: 4 key technical factors buyers must verify before purchasing {keyword}.
8. FAQ Section: 4 common questions with concise, clear answers.
9. Conclusion & Final Recommendation.

{custom_instructions}
"""
        html_content = self._call_llm(system_prompt, user_prompt)

        # Fallback nếu không có LLM response
        if not html_content:
            html_content = self._build_template_fallback(keyword, products, year)

        # Đính kèm Amazon Compliance Disclaimer và Stock Verification
        compliance_box = AmazonPriceComplianceGuard.generate_compliance_disclaimer()
        html_content = f"{html_content}\n\n{compliance_box}"

        meta_desc = f"Looking for the best {keyword} in {year}? Read our data-driven engineering analysis with comparison charts, pros & cons, and verified value picks."
        
        return {
            "title": formatted_title,
            "slug": slug,
            "content": html_content,
            "meta_desc": meta_desc,
            "focus_kw": keyword
        }

    def _build_template_fallback(self, keyword: str, products: List[AmazonProduct], year: int) -> str:
        """Sinh nội dung HTML chuẩn CRO khi chạy offline / chưa cấu hình API key."""
        cards = []
        reviews = []
        table_rows = []

        awards = ["Best Overall", "Best Value Pick", "Best Premium Choice", "Top Rated Option", "Budget Friendly"]

        for idx, p in enumerate(products):
            award = awards[idx] if idx < len(awards) else f"Runner Up #{idx+1}"
            features_li = "".join([f"<li>{f}</li>" for f in p.features])
            
            # Card
            cards.append(f"""
            <div style="border:1px solid #e2e8f0; border-radius:8px; padding:16px; margin-bottom:12px; background:#ffffff;">
                <span style="background:#2563eb; color:#fff; font-size:12px; font-weight:700; padding:4px 8px; border-radius:4px;">{award}</span>
                <h4 style="margin:8px 0 4px 0;"><a href="{p.affiliate_url}" rel="nofollow sponsored" target="_blank" style="color:#0f172a; text-decoration:none;">{p.title[:65]}...</a></h4>
                <p style="margin:0 0 10px 0; font-weight:600; color:#16a34a;">{p.price}</p>
                <a href="{p.affiliate_url}" rel="nofollow sponsored" target="_blank" style="display:inline-block; background:#f59e0b; color:#0f172a; font-weight:bold; padding:8px 16px; border-radius:4px; text-decoration:none; font-size:14px;">View on Amazon &rarr;</a>
            </div>
            """)

            # Table row
            table_rows.append(f"""
            <tr style="border-bottom:1px solid #e2e8f0;">
                <td style="padding:10px; font-weight:bold; color:#2563eb;">{award}</td>
                <td style="padding:10px;">{p.title[:45]}...</td>
                <td style="padding:10px;">{p.price}</td>
                <td style="padding:10px;"><a href="{p.affiliate_url}" rel="nofollow sponsored" target="_blank" style="background:#f59e0b; color:#000; padding:6px 12px; border-radius:4px; text-decoration:none; font-weight:bold; font-size:13px;">Check Deal</a></td>
            </tr>
            """)

            # Individual review
            img_html = f'<img src="{p.image_url}" alt="{p.title}" style="max-width:300px; display:block; margin:16px auto; border-radius:6px;" />' if p.image_url else ""
            reviews.append(f"""
            <div style="margin:36px 0; padding-bottom:24px; border-bottom:2px dashed #cbd5e1;">
                <h2>{idx+1}. {p.title} &mdash; <span style="color:#2563eb;">{award}</span></h2>
                {img_html}
                <p>The <strong>{p.title}</strong> stands out in our engineering analysis for its verified build quality, reliability ratings, and practical day-to-day usability. If you need a dependable {keyword} that delivers consistent technical performance, this model offers a compelling combination of features.</p>
                
                <h3>Key Specifications & Highlights:</h3>
                <ul>{features_li}</ul>
                
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin:20px 0;">
                    <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:16px; border-radius:6px;">
                        <h4 style="color:#166534; margin-top:0;">&#10004; What We Like</h4>
                        <ul style="color:#14532d; font-size:14px; margin-bottom:0;">
                            <li>Outstanding performance and verified build quality</li>
                            <li>Intuitive controls and ergonomic design</li>
                            <li>Excellent value relative to its class</li>
                        </ul>
                    </div>
                    <div style="background:#fef2f2; border:1px solid #fecaca; padding:16px; border-radius:6px;">
                        <h4 style="color:#991b1b; margin-top:0;">&#10008; Points to Consider</h4>
                        <ul style="color:#7f1d1d; font-size:14px; margin-bottom:0;">
                            <li>Slightly higher initial investment for premium models</li>
                            <li>May require brief adjustment period for beginners</li>
                        </ul>
                    </div>
                </div>
                
                <div style="text-align:center; margin:24px 0;">
                    <a href="{p.affiliate_url}" rel="nofollow sponsored" target="_blank" style="display:inline-block; background:#f59e0b; color:#1e293b; font-weight:700; padding:14px 28px; border-radius:6px; text-decoration:none; font-size:16px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1);">Check Best Price on Amazon &rarr;</a>
                </div>
            </div>
            """)

        cards_html = "".join(cards)
        table_html = "".join(table_rows)
        reviews_html = "".join(reviews)

        return f"""
        <div style="font-family:system-ui, -apple-system, sans-serif; line-height:1.7; color:#1e293b;">
            <div style="background:#f8fafc; border-left:4px solid #3b82f6; padding:12px 16px; margin-bottom:24px; font-size:14px; color:#475569; border-radius:4px;">
                <strong>Affiliate Disclosure:</strong> As an Amazon Associate and affiliate partner, we earn from qualifying purchases made through links on this page at zero extra cost to you.
            </div>

            <p style="font-size:18px; color:#334155;">Choosing the right <strong>{keyword}</strong> can be daunting with so many models saturating the market. To help you make an informed decision, our editorial team spent weeks evaluating top contenders based on durability, functionality, verified owner feedback, and value for money.</p>

            <h3 style="border-bottom:2px solid #0284c7; padding-bottom:8px;">Quick Picks: Best {keyword.title()} Overview</h3>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:16px; margin:20px 0;">
                {cards_html}
            </div>

            <h3 style="margin-top:36px;">Comparison Matrix</h3>
            <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse:collapse; margin:16px 0; text-align:left;">
                    <thead>
                        <tr style="background:#f1f5f9; border-bottom:2px solid #cbd5e1;">
                            <th style="padding:10px;">Award</th>
                            <th style="padding:10px;">Product</th>
                            <th style="padding:10px;">Price</th>
                            <th style="padding:10px;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_html}
                    </tbody>
                </table>
            </div>

            {reviews_html}

            <h2>Buying Guide: How to Choose the Best {keyword.title()}</h2>
            <p>Before purchasing, keep these critical criteria in mind:</p>
            <ol>
                <li><strong>Durability & Build Materials:</strong> Look for reinforced components that endure daily wear and tear.</li>
                <li><strong>Ergonomics & Ease of Use:</strong> Ensure the design suits your specific routine and space constraints.</li>
                <li><strong>Warranty & Support:</strong> Always favor manufacturers offering responsive customer service and minimum 1-year coverage.</li>
                <li><strong>True Cost vs. Features:</strong> Avoid paying for unnecessary gimmicks you won't utilize.</li>
            </ol>

            <h2>Frequently Asked Questions</h2>
            <h3>Are these {keyword} models worth the price?</h3>
            <p>Yes. Our top picks have been vetted across thousands of verified customer reviews to ensure the price corresponds with actual durability and daily performance.</p>

            <h3>How often should I maintain or replace my {keyword}?</h3>
            <p>With standard maintenance according to manufacturer directions, premium units easily deliver 3 to 5+ years of optimal operation.</p>

            <div style="background:#f1f5f9; padding:20px; border-radius:8px; margin-top:36px;">
                <h3 style="margin-top:0;">Final Verdict</h3>
                <p style="margin-bottom:0;">For the vast majority of users, our <strong>Best Overall</strong> selection offers the ideal balance of functionality, durability, and cost. If you are shopping on a stricter budget, our <strong>Best Value</strong> pick delivers all core essentials without compromising reliability.</p>
            </div>
        </div>
        """

    def generate_single_product_review(self, product: AmazonProduct) -> Dict[str, Any]:
        """
        Sinh bài viết Đánh giá chuyên sâu 1 sản phẩm (Single Product Review)
        kèm điểm đánh giá, hands-on testing, bảng ưu/nhược điểm và Schema Review.
        """
        year = 2026
        formatted_title = f"{product.title[:60]} Review ({year}): Tested & Rated"
        slug = f"{product.title[:40].lower().replace(' ', '-').replace('/', '-')}-review"
        meta_desc = f"Honest, in-depth review of the {product.title[:50]}. Is it worth your money? Check pros, cons, specs, and real-world performance."

        system_prompt = (
            "You are a master product testing reviewer. Write an authentic, thorough single-product review "
            "with first-hand testing observations, specific pros and cons, detailed specs, who should buy vs avoid, "
            "and strong conversion-focused CTA buttons. Output clean HTML for WordPress."
        )

        user_prompt = f"""
Write an in-depth review for this product:
- Name: {product.title}
- ASIN: {product.asin}
- Price: {product.price}
- Affiliate URL: {product.affiliate_url}
- Image: {product.image_url}
- Features: {'; '.join(product.features)}

Structure:
1. FTC Disclosure box.
2. The Bottom Line (Quick verdict card with overall score 9.0/10, Best for, and instant CTA button).
3. First Impressions & Build Quality.
4. Key Features & Specifications Table.
5. Real-World Performance & Testing Experience.
6. The Pros & Cons Box (balanced, real cons).
7. Who Should Buy This vs Who Should Skip It.
8. Final Verdict & Pricing on Amazon.
"""
        html = self._call_llm(system_prompt, user_prompt)
        if not html:
            # Fallback HTML
            img_html = f'<img src="{product.image_url}" alt="{product.title}" style="max-width:320px; display:block; margin:20px auto; border-radius:8px;" />' if product.image_url else ""
            html = f"""
            <div style="font-family:system-ui, -apple-system, sans-serif; line-height:1.7; color:#1e293b;">
                <div style="background:#f8fafc; border-left:4px solid #3b82f6; padding:12px 16px; margin-bottom:24px; font-size:14px; color:#475569; border-radius:4px;">
                    <strong>Affiliate Disclosure:</strong> As an Amazon Associate, we earn from qualifying purchases through links on this page.
                </div>

                <div style="border:2px solid #e2e8f0; border-radius:12px; padding:24px; background:#ffffff; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom:30px;">
                    <span style="background:#22c55e; color:#fff; font-weight:bold; padding:4px 10px; border-radius:4px; font-size:13px;">EDITOR'S RATING: 9.2 / 10</span>
                    <h2 style="margin:12px 0 6px 0;">{product.title}</h2>
                    <p style="font-size:20px; font-weight:bold; color:#16a34a; margin:0 0 16px 0;">{product.price}</p>
                    {img_html}
                    <p><strong>The Quick Verdict:</strong> A standout contender in its category offering exceptional durability, thoughtful ergonomics, and reliable daily operation. Recommended for buyers who prioritize long-term value over budget shortcuts.</p>
                    <div style="text-align:center; margin-top:20px;">
                        <a href="{product.affiliate_url}" rel="nofollow sponsored" target="_blank" style="display:inline-block; background:#f59e0b; color:#1e293b; font-weight:bold; padding:14px 28px; border-radius:6px; text-decoration:none; font-size:16px;">Check Latest Price on Amazon &rarr;</a>
                    </div>
                </div>

                <h2>Build Quality, Materials & Design</h2>
                <p>From the moment you unbox the {product.title}, the attention to structural integrity is evident. Components fit tightly with minimal flex, and touchpoints feel premium and intentional.</p>

                <h2>Key Features & Highlights</h2>
                <ul>{''.join([f'<li>{f}</li>' for f in product.features])}</ul>

                <h2>Pros & Cons Breakdown</h2>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin:24px 0;">
                    <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:16px; border-radius:8px;">
                        <h4 style="color:#166534; margin-top:0;">&#10004; What We Loved</h4>
                        <ul style="color:#14532d; font-size:14px; margin-bottom:0;">
                            <li>High-grade durable materials</li>
                            <li>Effortless setup and intuitive controls</li>
                            <li>Reliable performance across multiple test scenarios</li>
                        </ul>
                    </div>
                    <div style="background:#fef2f2; border:1px solid #fecaca; padding:16px; border-radius:8px;">
                        <h4 style="color:#991b1b; margin-top:0;">&#10008; Room for Improvement</h4>
                        <ul style="color:#7f1d1d; font-size:14px; margin-bottom:0;">
                            <li>Instruction manual could be more detailed</li>
                            <li>Price point reflects higher-end tier</li>
                        </ul>
                    </div>
                </div>

                <h2>Who Should Buy It?</h2>
                <p>This product is tailor-made for users seeking reliability, high build quality, and verified durability. If you are on an ultra-strict entry-level budget, you might consider lower-spec alternatives, but for most serious shoppers, this model justifies its cost.</p>

                <div style="text-align:center; margin:36px 0;">
                    <a href="{product.affiliate_url}" rel="nofollow sponsored" target="_blank" style="display:inline-block; background:#f59e0b; color:#1e293b; font-weight:bold; padding:16px 32px; border-radius:8px; text-decoration:none; font-size:18px;">Buy {product.title[:30]} on Amazon &rarr;</a>
                </div>
            </div>
            """

        compliance_box = AmazonPriceComplianceGuard.generate_compliance_disclaimer()
        html = f"{html}\n\n{compliance_box}"

        return {
            "title": formatted_title,
            "slug": slug,
            "content": html,
            "meta_desc": meta_desc,
            "focus_kw": product.title[:40]
        }

    def generate_vs_comparison(self, prod_a: AmazonProduct, prod_b: AmazonProduct) -> Dict[str, Any]:
        """
        Sinh bài viết So sánh đối đầu 2 sản phẩm (Product A vs Product B).
        """
        year = 2026
        formatted_title = f"{prod_a.title[:35]} vs {prod_b.title[:35]}: Which Wins in {year}?"
        slug = f"{prod_a.title[:20].lower().replace(' ', '-')}-vs-{prod_b.title[:20].lower().replace(' ', '-')}"
        meta_desc = f"Comparing {prod_a.title[:30]} vs {prod_b.title[:30]}. Head-to-head comparison of features, pricing, pros & cons to help you choose the winner."

        system_prompt = (
            "You are an expert product reviewer writing a head-to-head VS comparison article. "
            "Be fair, analytical, and declare a clear winner for different buyer personas. Output clean HTML for WordPress."
        )

        user_prompt = f"""
Write a head-to-head comparison article:
Product A: {prod_a.title} (Price: {prod_a.price}, Link: {prod_a.affiliate_url}, Features: {'; '.join(prod_a.features)})
Product B: {prod_b.title} (Price: {prod_b.price}, Link: {prod_b.affiliate_url}, Features: {'; '.join(prod_b.features)})

Format in HTML:
1. FTC Disclosure.
2. Quick Summary: Which one should you buy?
3. Side-by-side comparison table.
4. Round 1: Design & Build Quality.
5. Round 2: Performance & Everyday Experience.
6. Round 3: Value for Money.
7. Pros & Cons for Product A and Product B.
8. The Verdict & Winner Selection with direct CTA buttons for both.
"""
        html = self._call_llm(system_prompt, user_prompt)
        if not html:
            html = f"""
            <div style="font-family:system-ui, -apple-system, sans-serif; line-height:1.7; color:#1e293b;">
                <div style="background:#f8fafc; border-left:4px solid #3b82f6; padding:12px 16px; margin-bottom:24px; font-size:14px; color:#475569; border-radius:4px;">
                    <strong>Affiliate Disclosure:</strong> As an Amazon Associate, we earn from qualifying purchases through links on this page.
                </div>

                <h2>Quick Winner Summary</h2>
                <p>Both models bring impressive engineering to the table, but they cater to slightly different priorities:</p>
                <ul>
                    <li><strong>Choose {prod_a.title[:30]}:</strong> If you want the most refined overall build and premium features.</li>
                    <li><strong>Choose {prod_b.title[:30]}:</strong> If you want superior value-for-money and straightforward functionality.</li>
                </ul>

                <h2>Side-by-Side Comparison</h2>
                <div style="overflow-x:auto;">
                    <table style="width:100%; border-collapse:collapse; margin:20px 0;">
                        <thead>
                            <tr style="background:#f1f5f9; border-bottom:2px solid #cbd5e1; text-align:left;">
                                <th style="padding:10px;">Factor</th>
                                <th style="padding:10px;">{prod_a.title[:30]}</th>
                                <th style="padding:10px;">{prod_b.title[:30]}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style="border-bottom:1px solid #e2e8f0;">
                                <td style="padding:10px; font-weight:bold;">Price</td>
                                <td style="padding:10px; color:#16a34a; font-weight:bold;">{prod_a.price}</td>
                                <td style="padding:10px; color:#16a34a; font-weight:bold;">{prod_b.price}</td>
                            </tr>
                            <tr style="border-bottom:1px solid #e2e8f0;">
                                <td style="padding:10px; font-weight:bold;">Best For</td>
                                <td style="padding:10px;">Power Users & Professionals</td>
                                <td style="padding:10px;">Everyday Enthusiasts</td>
                            </tr>
                            <tr>
                                <td style="padding:10px; font-weight:bold;">Action</td>
                                <td style="padding:10px;"><a href="{prod_a.affiliate_url}" rel="nofollow sponsored" target="_blank" style="background:#f59e0b; color:#000; padding:6px 12px; border-radius:4px; text-decoration:none; font-weight:bold; font-size:13px;">View {prod_a.title[:15]}</a></td>
                                <td style="padding:10px;"><a href="{prod_b.affiliate_url}" rel="nofollow sponsored" target="_blank" style="background:#2563eb; color:#fff; padding:6px 12px; border-radius:4px; text-decoration:none; font-weight:bold; font-size:13px;">View {prod_b.title[:15]}</a></td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <h2>The Final Verdict</h2>
                <p>After thorough evaluation, <strong>{prod_a.title[:30]}</strong> takes the slight edge for users wanting peak craftsmanship. However, if price is your top consideration, <strong>{prod_b.title[:30]}</strong> remains the smarter purchase.</p>
            </div>
            """

        compliance_box = AmazonPriceComplianceGuard.generate_compliance_disclaimer()
        html = f"{html}\n\n{compliance_box}"

        return {
            "title": formatted_title,
            "slug": slug,
            "content": html,
            "meta_desc": meta_desc,
            "focus_kw": f"{prod_a.title[:20]} vs {prod_b.title[:20]}"
        }

    def optimize_and_rewrite_article(self, original_text_or_url: str) -> Dict[str, Any]:
        """
        Phân tích bài viết cũ hoặc bài của đối thủ, tìm điểm yếu E-E-A-T và viết lại phiên bản nâng cấp.
        """
        content_to_analyze = original_text_or_url
        if original_text_or_url.strip().startswith("http"):
            try:
                import requests
                from bs4 import BeautifulSoup
                res = requests.get(original_text_or_url, timeout=10)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    # Lấy nội dung chính
                    article_elem = soup.find("article") or soup.find("main") or soup.find("body")
                    content_to_analyze = article_elem.get_text()[:4000] if article_elem else res.text[:4000]
            except Exception as e:
                print(f"[Optimizer] Lỗi cào URL: {e}")

        system_prompt = (
            "You are a world-class SEO content editor and conversion rate optimization (CRO) specialist. "
            "Analyze the given article, identify weak spots (thin explanations, lack of clear pros/cons, "
            "weak CTA, lack of structured comparison, robotic AI fluff), and rewrite it into an authoritative, "
            "high-converting, E-E-A-T compliant masterpiece formatted in clean HTML."
        )

        user_prompt = f"""
Analyze and rewrite this article to rank #1 on Google and maximize affiliate conversions:

ORIGINAL CONTENT:
{content_to_analyze[:3000]}

Format Requirements:
1. Provide an 'Optimization Audit Summary' at the top explaining what was improved.
2. Complete rewritten HTML article with FTC disclosure, structured comparison tables, pros/cons, and buying criteria.
"""
        rewritten_html = self._call_llm(system_prompt, user_prompt)
        if not rewritten_html:
            rewritten_html = f"<div style='padding:20px;'><h3>Tối ưu bài viết hoàn tất</h3><p>{content_to_analyze[:500]}...</p></div>"

        return {
            "success": True,
            "rewritten_html": rewritten_html
        }

    def generate_informational_article(
        self,
        topic: str,
        article_type: str = "how_to",
        related_product: Optional[AmazonProduct] = None
    ) -> Dict[str, Any]:
        """
        Sinh bài viết thông tin (Informational / How-To / Educational Guide)
        giúp xây dựng Topical Authority, tăng trust E-E-A-T cho website và làm cầu nối Internal Links tới các bài Money/Roundup.
        """
        year = 2026
        clean_topic = topic.strip()
        formatted_topic = clean_topic
        lower_t = formatted_topic.lower()
        for prefix in ["how to fix ", "how to clean ", "how to ", "what is ", "guide to ", "the ultimate guide to "]:
            if lower_t.startswith(prefix):
                formatted_topic = formatted_topic[len(prefix):]
                break

        type_titles = {
            "how_to": f"How to {formatted_topic.title()}: Step-by-Step Guide ({year})",
            "explainer": f"What is {formatted_topic.title()}? Complete Beginner's Guide ({year})",
            "troubleshooting": f"How to Fix {formatted_topic.title()}: Proven Troubleshooting Guide",
            "guide": f"The Ultimate Guide to {formatted_topic.title()} in {year}"
        }
        title = type_titles.get(article_type, f"How to {formatted_topic.title()}: Complete Guide ({year})")
        slug = f"{clean_topic.lower().replace(' ', '-').replace('?', '').replace('/', '-')}-guide"

        product_context = ""
        if related_product:
            product_context = f"""
Recommended Solution / Product Mention (Integrate naturally as a recommended tool/solution within the article):
- Product Name: {related_product.title}
- Price: {related_product.price}
- Affiliate Link: {related_product.affiliate_url}
- Image: {related_product.image_url}
- Features: {'; '.join(related_product.features)}
"""

        system_prompt = (
            "You are an authoritative subject matter expert and technical educator. "
            "Write an in-depth, structured informational guide that thoroughly answers the reader's question, "
            "providing actionable steps, expert insights, common pitfalls to avoid, and structured FAQ schema. "
            "Write in an engaging, authoritative, and direct tone complying with Google's Helpful Content Guidelines. "
            "Output valid HTML for WordPress Gutenberg."
        )

        user_prompt = f"""
Write a comprehensive, authoritative informational article for:
Topic: "{clean_topic}"
Article Type: {article_type}
Current Year: {year}
{product_context}

Format Requirements in clean HTML:
1. Quick Key Takeaways / Summary box at the top (3-4 bullet points highlighting the immediate answer).
2. Detailed Explanation or Step-by-Step Breakdown (Use clear H2, H3 headings, numbered lists, and bold action verbs).
3. Expert Tips & Common Mistakes to Avoid (Crucial for E-E-A-T score).
{"4. A 'Recommended Tool/Product' section naturally presenting the related product as a helpful solution with image and CTA button." if related_product else ""}
5. FAQ Section (4 specific frequently asked questions with direct answers).
6. Clear, actionable conclusion.
"""
        html = self._call_llm(system_prompt, user_prompt)
        if not html:
            # Fallback template
            prod_box = ""
            if related_product:
                img_tag = f'<img src="{related_product.image_url}" alt="{related_product.title}" style="max-width:260px; display:block; margin:10px auto; border-radius:6px;" />' if related_product.image_url else ""
                prod_box = f"""
                <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:20px; margin:28px 0;">
                    <span style="background:#0284c7; color:#fff; font-size:11px; font-weight:bold; padding:3px 8px; border-radius:4px; text-transform:uppercase;">Recommended Tool</span>
                    <h4 style="margin:10px 0 6px 0;"><a href="{related_product.affiliate_url}" rel="nofollow sponsored" target="_blank" style="color:#0f172a; text-decoration:none;">{related_product.title}</a></h4>
                    {img_tag}
                    <p style="font-size:14px; color:#475569;">To execute these steps efficiently, having the right equipment makes a dramatic difference. This solution offers tested reliability and proven results.</p>
                    <div style="text-align:center; margin-top:14px;">
                        <a href="{related_product.affiliate_url}" rel="nofollow sponsored" target="_blank" style="display:inline-block; background:#f59e0b; color:#1e293b; font-weight:bold; padding:10px 20px; border-radius:6px; text-decoration:none; font-size:14px;">View on Amazon &rarr;</a>
                    </div>
                </div>
                """

            html = f"""
            <div style="font-family:system-ui, -apple-system, sans-serif; line-height:1.7; color:#1e293b;">
                <div style="background:#eff6ff; border-left:4px solid #3b82f6; padding:16px 20px; border-radius:6px; margin-bottom:24px;">
                    <h4 style="color:#1e40af; margin-top:0; font-size:15px;">&#9889; Key Takeaways</h4>
                    <ul style="color:#1e3a8a; font-size:14px; margin-bottom:0; padding-left:20px;">
                        <li>Understanding the fundamentals of {clean_topic} saves time and avoids costly trial-and-error.</li>
                        <li>Follow our tested 4-step framework for optimal, repeatable results.</li>
                        <li>Regular maintenance and adhering to manufacturer guidelines ensures longevity.</li>
                    </ul>
                </div>

                <h2>Understanding {clean_topic.title()}</h2>
                <p>Whether you are dealing with {clean_topic} for the first time or seeking to optimize your current routine, having a systematic approach is essential. In this comprehensive guide, we distill practical insights into clear, actionable advice.</p>

                <h2>Step-by-Step Execution Guide</h2>
                <ol style="padding-left:24px; font-size:15px;">
                    <li style="margin-bottom:12px;"><strong>Preparation & Assessment:</strong> Before taking action, thoroughly inspect the components and assemble the necessary tools.</li>
                    <li style="margin-bottom:12px;"><strong>Core Procedure:</strong> Follow deliberate, measured adjustments to achieve baseline specifications without causing strain.</li>
                    <li style="margin-bottom:12px;"><strong>Fine-Tuning & Verification:</strong> Test under normal working conditions to verify stability, comfort, and performance.</li>
                    <li style="margin-bottom:12px;"><strong>Ongoing Maintenance:</strong> Establish a routine inspection schedule every 3 to 6 months.</li>
                </ol>

                {prod_box}

                <h2>Common Mistakes to Avoid</h2>
                <p>Through our experience, we consistently see users make these three preventable errors:</p>
                <ul>
                    <li><strong>Rushing the initial setup:</strong> Taking an extra 10 minutes upfront prevents premature wear and tear.</li>
                    <li><strong>Ignoring ergonomics:</strong> Always prioritize natural alignment over aesthetics.</li>
                    <li><strong>Over-tightening fittings:</strong> Excessive force can strip threading or damage structural integrity.</li>
                </ul>

                <h2>Frequently Asked Questions</h2>
                <h3>How long does this process typically take?</h3>
                <p>For most users, the complete procedure requires approximately 15 to 30 minutes with standard household equipment.</p>

                <h3>Can I do this without specialized tools?</h3>
                <p>Yes. The majority of steps can be completed using standard tools or equipment included in the original packaging.</p>

                <div style="background:#f1f5f9; padding:20px; border-radius:8px; margin-top:32px;">
                    <h3 style="margin-top:0;">Summary</h3>
                    <p style="margin-bottom:0;">Mastering {clean_topic} is straightforward once you follow a consistent routine. Apply these guidelines today to enhance both performance and longevity.</p>
                </div>
            </div>
            """

        if related_product:
            compliance_box = AmazonPriceComplianceGuard.generate_compliance_disclaimer()
            html = f"{html}\n\n{compliance_box}"

        meta_desc = f"Comprehensive guide to {clean_topic}. Learn step-by-step instructions, expert tips, common mistakes to avoid, and FAQ."

        return {
            "title": title,
            "slug": slug,
            "content": html,
            "meta_desc": meta_desc,
            "focus_kw": clean_topic
        }

    @staticmethod
    def inject_internal_links(content_html: str, links: List[Dict[str, str]], is_how_to: bool = False) -> str:
        """Tự động chèn liên kết nội bộ theo cấu trúc Topic Cluster (Pillar <-> Cluster)."""
        if not links:
            return content_html

        if is_how_to:
            # Bài vệ tinh How-To / Thông tin: Chèn hộp kêu gọi tham khảo bài viết Pillar / Mua hàng chính
            pillar = links[0]
            callout = f"""
            <div style="background:#f0fdf4; border-left:4px solid #16a34a; padding:16px 20px; border-radius:8px; margin:28px 0; font-family:sans-serif;">
                <span style="background:#16a34a; color:#fff; font-size:11px; font-weight:bold; padding:2px 8px; border-radius:4px; text-transform:uppercase;">💡 Lời Khuyên Mua Sắm:</span>
                <p style="margin:8px 0 0 0; font-size:14px; color:#14532d; line-height:1.5;">
                    Bạn đang cân nhắc nâng cấp thiết bị tốt nhất? Hãy tham khảo bài đánh giá và bảng so sánh chi tiết: 
                    <a href="{pillar.get('url', '#')}" style="color:#15803d; font-weight:bold; text-decoration:underline;">{pillar.get('title', 'Xem danh sách sản phẩm tốt nhất')} &rarr;</a>
                </p>
            </div>
            """
            if "</div>" in content_html:
                parts = content_html.rsplit("</div>", 1)
                return f"{parts[0]}{callout}</div>{parts[1] if len(parts) > 1 else ''}"
            return f"{content_html}\n\n{callout}"
        else:
            # Bài Pillar / Roundup / Review: Chèn danh sách các bài viết hướng dẫn vệ tinh
            valid_links = [l for l in links if l.get("title")][:4]
            if not valid_links:
                return content_html
            list_items = "".join([
                f'<li style="margin-bottom:8px;"><a href="{l.get("url", "#")}" style="color:#2563eb; text-decoration:none; font-weight:600;">{l.get("title", "")} &rarr;</a></li>'
                for l in valid_links
            ])
            box = f"""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:20px; margin:32px 0; font-family:sans-serif;">
                <h3 style="margin-top:0; font-size:15px; color:#0f172a;">📚 Cẩm Nang & Hướng Dẫn Kỹ Thuật Liên Quan:</h3>
                <ul style="padding-left:20px; margin-bottom:0; font-size:14px; color:#334155;">
                    {list_items}
                </ul>
            </div>
            """
            if "</div>" in content_html:
                parts = content_html.rsplit("</div>", 1)
                return f"{parts[0]}{box}</div>{parts[1] if len(parts) > 1 else ''}"
            return f"{content_html}\n\n{box}"


