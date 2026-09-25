import os
import re
import json
import asyncio
import subprocess
import hashlib
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

VIDEOS_DIR = Path(__file__).resolve().parent.parent / "output" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache_video"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class AIShortVideoCreator:
    """
    Module Sản Xuất Video Dọc 9:16 (Shorts / Reels / TikTok) Tự Động Từ Bài Viết & Ảnh Sản Phẩm
    - Tóm tắt kịch bản video 30-45 giây theo chuẩn Hook -> Top 3 Sản Phẩm -> Call To Action (CTA).
    - Giọng đọc AI hoàn toàn Miễn Phí bằng edge-tts (Microsoft Neural Voice).
    - Tạo các slide hình ảnh 1080x1920 chất lượng cao bằng Pillow & render MP4 bằng FFmpeg.
    - Sinh sẵn tiêu đề, mô tả và hashtags tối ưu cho Reels/Shorts/TikTok.
    """

    AVAILABLE_VOICES = [
        {"id": "en-US-ChristopherNeural", "name": "Christopher (US Male - Năng Động & Lôi Cuốn)", "lang": "en"},
        {"id": "en-US-JennyNeural", "name": "Jenny (US Female - Thân Thiện & Rõ Ràng)", "lang": "en"},
        {"id": "en-US-GuyNeural", "name": "Guy (US Male - Uy Tín & Chuyên Nghiệp)", "lang": "en"},
        {"id": "en-GB-RyanNeural", "name": "Ryan (UK Male - Chuẩn Anh Quốc)", "lang": "en"},
        {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My (VN Nữ - Dịu Dàng & Truyền Cảm)", "lang": "vi"},
        {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh (VN Nam - Tự Nhiên & Dứt Khoát)", "lang": "vi"}
    ]

    def __init__(self):
        pass

    def get_available_voices(self) -> List[Dict[str, str]]:
        return self.AVAILABLE_VOICES

    def generate_short_script(
        self,
        title: str,
        keyword: str,
        products: List[Dict[str, Any]],
        language: str = "en",
        blog_url: str = ""
    ) -> Dict[str, Any]:
        """Tóm tắt bài viết thành kịch bản video ngắn 30-45 giây và chuẩn bị nội dung các slide."""
        clean_kw = re.sub(r'\b(best|in 2026|top|tested|reviewed)\b', '', keyword, flags=re.I).strip().title()
        if not clean_kw:
            clean_kw = "Top Products"

        # Chuẩn hóa 2-4 sản phẩm
        selected_prods = products[:4] if products else []
        if not selected_prods:
            selected_prods = [
                {"title": f"Premium {clean_kw}", "price": "$49.99", "asin": "B07SAMPLE1", "badge": "🏆 TOP PICK", "rating": 4.8},
                {"title": f"Budget-Friendly {clean_kw}", "price": "$29.99", "asin": "B07SAMPLE2", "badge": "💰 BEST VALUE", "rating": 4.6},
                {"title": f"Ultra-Durable {clean_kw}", "price": "$69.99", "asin": "B07SAMPLE3", "badge": "⭐ RUNNER-UP", "rating": 4.9}
            ]

        slides = []
        full_voice_lines = []

        if language == "vi":
            # Slide 1: Hook Intro
            hook_title = f"Top {clean_kw} Tốt Nhất 2026!"
            hook_sub = "Đừng tốn tiền mua nhầm loại dở!"
            hook_voice = f"Nếu bạn đang tìm mua {clean_kw} tốt nhất năm 2026, hãy xem ngay 3 lựa chọn đáng tiền nhất sau đây."
            slides.append({
                "type": "hook",
                "tag": "🔥 TỔNG HỢP ĐÁNG MUA NHẤT",
                "headline": hook_title,
                "subline": hook_sub,
                "voice_text": hook_voice
            })
            full_voice_lines.append(hook_voice)

            # Slides sản phẩm
            for idx, p in enumerate(selected_prods):
                p_title = p.get("title", f"Sản phẩm {idx+1}")[:42]
                badge = p.get("badge") or ("🏆 LỰA CHỌN TỐT NHẤT" if idx == 0 else ("💰 GIÁ RẺ NHẤT" if idx == 1 else "⭐ ĐÁNG MUA"))
                price = p.get("price") or "$39.99"
                p_voice = f"Vị trí số {idx+1}: {badge}. {p_title}. Giá chỉ khoảng {price}, sở hữu độ bền vượt trội và đánh giá cực cao."
                slides.append({
                    "type": "product",
                    "index": idx + 1,
                    "badge": badge,
                    "title": p_title,
                    "price": price,
                    "rating": p.get("rating", 4.8),
                    "image": p.get("image", ""),
                    "asin": p.get("asin", ""),
                    "voice_text": p_voice
                })
                full_voice_lines.append(p_voice)

            # Slide CTA
            cta_voice = "Xem ngay bảng so sánh chi tiết và link ưu đãi giảm giá tốt nhất ở phần mô tả hoặc bio của video nhé!"
            slides.append({
                "type": "cta",
                "tag": "🔗 LINK TRONG PHẦN MÔ TẢ & BIO",
                "headline": "Xem Chi Tiết & Mã Giảm Giá",
                "subline": "Bấm vào link bên dưới để xem bảng thông số đầy đủ!",
                "voice_text": cta_voice
            })
            full_voice_lines.append(cta_voice)

            social_title = f"Top {len(selected_prods)} {clean_kw} Đáng Mua Nhất 2026! 🚗✨"
            social_desc = (
                f"Đánh giá chi tiết top {len(selected_prods)} {clean_kw} tốt nhất hiện nay.\n"
                f"👉 Link bài viết đánh giá & mã giảm giá ở Bio / Comment!\n"
                f"{blog_url}"
            )
            hashtags = f"#shorts #reels #tiktok #review #danhgia #{clean_kw.lower().replace(' ', '')} #muasam"

        else:
            # English
            hook_title = f"Top {clean_kw} in 2026!"
            hook_sub = "Stop wasting money on junk!"
            hook_voice = f"Looking for the best {clean_kw} in 2026? Stop wasting money on bad picks. Here are the top tested models you can trust."
            slides.append({
                "type": "hook",
                "tag": "🔥 TESTED & REVIEWED 2026",
                "headline": hook_title,
                "subline": hook_sub,
                "voice_text": hook_voice
            })
            full_voice_lines.append(hook_voice)

            for idx, p in enumerate(selected_prods):
                p_title = p.get("title", f"Product {idx+1}")[:42]
                badge = p.get("badge") or ("🏆 OVERALL TOP PICK" if idx == 0 else ("💰 BEST BUDGET" if idx == 1 else "⭐ RUNNER-UP"))
                price = p.get("price") or "$39.99"
                p_voice = f"Number {idx+1}: {badge}. The {p_title}. At around {price}, it delivers outstanding build quality and top-tier user ratings."
                slides.append({
                    "type": "product",
                    "index": idx + 1,
                    "badge": badge,
                    "title": p_title,
                    "price": price,
                    "rating": p.get("rating", 4.8),
                    "image": p.get("image", ""),
                    "asin": p.get("asin", ""),
                    "voice_text": p_voice
                })
                full_voice_lines.append(p_voice)

            cta_voice = "Which one fits your needs? Check out the full comparison table and exclusive discount links in the description or bio below!"
            slides.append({
                "type": "cta",
                "tag": "🔗 LINK IN BIO & DESCRIPTION",
                "headline": "Full Comparison & Deals",
                "subline": "Tap the link below for detailed specs and verified discounts!",
                "voice_text": cta_voice
            })
            full_voice_lines.append(cta_voice)

            social_title = f"Best {clean_kw} in 2026 - Tested & Ranked! 🛒🔥"
            social_desc = (
                f"Here are the top {len(selected_prods)} {clean_kw} tested for quality, durability and value.\n"
                f"👉 Full buyer guide and discounted prices link in description / bio!\n"
                f"{blog_url}"
            )
            hashtags = f"#shorts #reels #tiktok #amazonfinds #{clean_kw.lower().replace(' ', '')} #buyersguide #honestreview"

        full_script = " ".join(full_voice_lines)

        return {
            "title": title,
            "keyword": keyword,
            "language": language,
            "slides": slides,
            "full_script": full_script,
            "social_title": social_title,
            "social_desc": social_desc,
            "hashtags": hashtags
        }

    async def synthesize_voiceover(self, text: str, voice: str, output_path: str) -> float:
        """Sinh giọng đọc bằng edge-tts và đo độ dài âm thanh chính xác."""
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

        # Đo độ dài bằng ffprobe
        duration = 15.0
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                output_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            duration = float(res.stdout.strip())
        except Exception as e:
            print(f"[ShortVideoCreator] Lỗi đo thời lượng audio: {e}")
        return duration

    def _download_or_cache_image(self, url: str) -> Optional[str]:
        """Tải ảnh sản phẩm về cache để chèn vào video."""
        if not url or not url.startswith("http"):
            return None
        h = hashlib.md5(url.encode('utf-8')).hexdigest()
        local_path = CACHE_DIR / f"img_{h}.jpg"
        if local_path.exists() and local_path.stat().st_size > 1000:
            return str(local_path)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=8) as response, open(local_path, 'wb') as out_file:
                out_file.write(response.read())
            return str(local_path)
        except Exception as e:
            print(f"[ShortVideoCreator] Không tải được ảnh {url}: {e}")
            return None

    def render_slide_image(self, slide_data: Dict[str, Any], output_img_path: str, width: int = 1080, height: int = 1920):
        """Vẽ 1 khung hình dọc chuẩn 9:16 (1080x1920) phong cách hiện đại, sang trọng."""
        # Nền màu Dark Slate hiện đại
        img = Image.new("RGB", (width, height), color=(15, 23, 42)) # Slate 900
        draw = ImageDraw.Draw(img)

        # Vẽ dải gradient trang trí trên và dưới
        for y in range(0, 320):
            alpha = int(60 * (1 - y / 320))
            draw.line([(0, y), (width, y)], fill=(99, 102, 241, alpha)) # Indigo tint
        for y in range(height - 280, height):
            alpha = int(70 * ((y - (height - 280)) / 280))
            draw.line([(0, y), (width, y)], fill=(245, 158, 11, alpha)) # Amber tint

        stype = slide_data.get("type", "product")

        if stype == "hook":
            # Slide Mở đầu (Hook)
            tag = slide_data.get("tag", "🔥 2026 BUYER'S GUIDE")
            draw.rounded_rectangle([(140, 260), (940, 360)], radius=30, fill=(245, 158, 11))
            draw.text((width // 2, 310), tag, fill=(15, 23, 42), anchor="mm")

            headline = slide_data.get("headline", "Top Picks")
            draw.text((width // 2, 700), headline, fill=(255, 255, 255), anchor="mm")

            subline = slide_data.get("subline", "Tested & Reviewed")
            draw.text((width // 2, 860), subline, fill=(148, 163, 184), anchor="mm")

            # Icon decor ở giữa
            draw.rounded_rectangle([(340, 1060), (740, 1460)], radius=50, fill=(30, 41, 59), outline=(99, 102, 241), width=4)
            draw.text((width // 2, 1260), "🏆", fill=(245, 158, 11), anchor="mm")

            draw.text((width // 2, 1620), "⚡ Vuốt lên & xem ngay!", fill=(226, 232, 240), anchor="mm")

        elif stype == "cta":
            # Slide Kêu gọi hành động (CTA)
            tag = slide_data.get("tag", "🔗 LINK IN BIO & DESCRIPTION")
            draw.rounded_rectangle([(100, 260), (980, 360)], radius=30, fill=(16, 185, 129))
            draw.text((width // 2, 310), tag, fill=(255, 255, 255), anchor="mm")

            headline = slide_data.get("headline", "Full Comparison Link")
            draw.text((width // 2, 600), headline, fill=(255, 255, 255), anchor="mm")

            # Hộp thông tin CTA
            draw.rounded_rectangle([(120, 800), (960, 1400)], radius=40, fill=(30, 41, 59), outline=(16, 185, 129), width=5)
            draw.text((width // 2, 960), "👇 BẤM VÀO ĐÂY ĐỂ XEM 👇", fill=(245, 158, 11), anchor="mm")
            draw.text((width // 2, 1100), "• Bảng So Sánh Giá Rẻ Nhất", fill=(241, 245, 249), anchor="mm")
            draw.text((width // 2, 1220), "• Đánh Giá & Điểm Trừ Của Sản Phẩm", fill=(241, 245, 249), anchor="mm")

            draw.rounded_rectangle([(180, 1520), (900, 1640)], radius=30, fill=(99, 102, 241))
            draw.text((width // 2, 1580), "👉 Xem bài viết đầy đủ tại Bio", fill=(255, 255, 255), anchor="mm")

        else:
            # Slide Giới thiệu sản phẩm
            idx = slide_data.get("index", 1)
            badge = slide_data.get("badge", f"TOP {idx}")
            title = slide_data.get("title", f"Product {idx}")
            price = slide_data.get("price", "$39.99")
            rating = slide_data.get("rating", 4.8)

            # Badge vị trí sản phẩm
            draw.rounded_rectangle([(120, 180), (960, 280)], radius=25, fill=(245, 158, 11))
            draw.text((width // 2, 230), f"#{idx} • {badge.upper()}", fill=(15, 23, 42), anchor="mm")

            # Tiêu đề sản phẩm
            draw.text((width // 2, 380), title, fill=(255, 255, 255), anchor="mm")

            # Khung chứa ảnh sản phẩm
            card_box = (140, 480, 940, 1280)
            draw.rounded_rectangle(card_box, radius=40, fill=(255, 255, 255), outline=(226, 232, 240), width=4)

            # Tải và dán ảnh sản phẩm vào giữa
            img_url = slide_data.get("image", "")
            cached_img_path = self._download_or_cache_image(img_url) if img_url else None
            pasted = False
            if cached_img_path and Path(cached_img_path).exists():
                try:
                    p_img = Image.open(cached_img_path).convert("RGBA")
                    # Resize fit vào khung 700x700
                    p_img.thumbnail((720, 720), Image.Resampling.LANCZOS)
                    pw, ph = p_img.size
                    offset_x = 140 + (800 - pw) // 2
                    offset_y = 480 + (800 - ph) // 2
                    img.paste(p_img, (offset_x, offset_y), p_img if p_img.mode == 'RGBA' else None)
                    pasted = True
                except Exception as e:
                    print(f"[ShortVideoCreator] Lỗi paste ảnh: {e}")

            if not pasted:
                draw.text((width // 2, 880), "📷 [Hình Ảnh Sản Phẩm]", fill=(100, 116, 139), anchor="mm")

            # Hộp Giá & Sao đánh giá
            draw.rounded_rectangle([(160, 1360), (520, 1480)], radius=25, fill=(234, 88, 12)) # Cam đậm
            draw.text((340, 1420), f"Giá: {price}", fill=(255, 255, 255), anchor="mm")

            draw.rounded_rectangle([(560, 1360), (920, 1480)], radius=25, fill=(30, 41, 59), outline=(245, 158, 11), width=3)
            draw.text((740, 1420), f"⭐ {rating} / 5.0", fill=(245, 158, 11), anchor="mm")

            # Call to Action nhỏ phía dưới
            draw.text((width // 2, 1650), "👉 Link xem chi tiết ở mô tả / bio!", fill=(148, 163, 184), anchor="mm")

        img.save(output_img_path, format="JPEG", quality=92)

    async def create_video_short(
        self,
        title: str,
        keyword: str,
        products: List[Dict[str, Any]],
        language: str = "en",
        voice: Optional[str] = None,
        blog_url: str = ""
    ) -> Dict[str, Any]:
        """Quy trình tạo Video Short trọn gói (Script -> Edge-TTS Audio -> Pillow Frames -> FFmpeg MP4)."""
        if not voice:
            voice = "vi-VN-NamMinhNeural" if language == "vi" else "en-US-ChristopherNeural"

        # 1. Sinh kịch bản và chia slide
        script_info = self.generate_short_script(title, keyword, products, language, blog_url)
        slides = script_info["slides"]
        full_script = script_info["full_script"]

        slug_base = re.sub(r'[^a-zA-Z0-9]', '_', keyword.lower()).strip('_')[:25]
        random_hash = hashlib.md5(f"{keyword}_{language}".encode('utf-8')).hexdigest()[:6]
        video_filename = f"short_{slug_base}_{random_hash}.mp4"
        audio_filename = f"audio_{slug_base}_{random_hash}.mp3"

        audio_path = CACHE_DIR / audio_filename
        output_video_path = VIDEOS_DIR / video_filename

        # 2. Sinh giọng đọc bằng edge-tts
        total_duration = await self.synthesize_voiceover(full_script, voice, str(audio_path))
        if total_duration <= 0:
            total_duration = 25.0

        # 3. Vẽ ảnh cho từng slide
        slide_img_paths = []
        for idx, slide in enumerate(slides):
            img_file = CACHE_DIR / f"frame_{slug_base}_{random_hash}_{idx}.jpg"
            self.render_slide_image(slide, str(img_file))
            slide_img_paths.append(str(img_file))

        # 4. Phân bổ thời lượng cho từng slide
        num_slides = len(slides)
        per_slide_duration = round(total_duration / num_slides, 2)
        # Slide hook và CTA cho chạy 4 giây, các slide sản phẩm chia đều phần còn lại
        if num_slides >= 4 and total_duration > 15:
            hook_dur = 4.0
            cta_dur = 4.5
            remain_dur = max(6.0, total_duration - hook_dur - cta_dur)
            prod_dur = round(remain_dur / (num_slides - 2), 2)
            slide_durations = [hook_dur] + [prod_dur] * (num_slides - 2) + [cta_dur]
        else:
            slide_durations = [per_slide_duration] * num_slides

        # Tạo file danh sách concat demuxer cho FFmpeg
        concat_txt = CACHE_DIR / f"concat_{slug_base}_{random_hash}.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for i, p in enumerate(slide_img_paths):
                dur = slide_durations[i]
                # Windows path fix for ffmpeg concat
                p_escaped = p.replace("\\", "/")
                f.write(f"file '{p_escaped}'\n")
                f.write(f"duration {dur}\n")
            # Repeat last file to satisfy ffmpeg concat demuxer bug
            f.write(f"file '{slide_img_paths[-1].replace('\\', '/')}'\n")

        # 5. Render Video bằng FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "25",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output_video_path)
        ]
        
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            print(f"[ShortVideoCreator] Lỗi ffmpeg render: {proc.stderr}")
            raise RuntimeError(f"FFmpeg error: {proc.stderr[:200]}")

        video_url = f"/output/videos/{video_filename}"

        return {
            "success": True,
            "video_url": video_url,
            "filename": video_filename,
            "local_path": str(output_video_path),
            "duration_seconds": round(total_duration, 1),
            "voice_used": voice,
            "slides_count": len(slides),
            "social_copy": {
                "title": script_info["social_title"],
                "description": script_info["social_desc"],
                "hashtags": script_info["hashtags"],
                "full_script": full_script
            }
        }
