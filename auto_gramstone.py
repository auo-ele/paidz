#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  BOT AUTO GRAMSTONE ($GRAM / $TON) 24/7 - BẢN FIX TRIỆT ĐỂ MOONPOOL 2026
  Platform: Gramstone Mini App (https://gramstone.46-101-143-24.sslip.io/)
  Telegram Bot: @gramstone_bot
  
  CƠ CHẾ CÀY THẺ SAFIR TIER 3 (+4 GH/s) LIÊN TỤC 24/7:
    1. Tự động Re-auth Telethon mỗi 25 phút (Chống 401 Unauthorized / Token Expire).
    2. Chuỗi 3 QC chuẩn Native Moonpool Engine:
       - Bước 1: Adsgram (Block 54796) + Full Event Tracking (Render/Show/Reward)
                 + Tự động chờ Server Verification qua /api/ads/adsgram-status (ready: true)
       - Bước 2: Gigapub (Delay chuẩn 8.5s chống too_early)
       - Bước 3: Monetag (Delay chuẩn 8.5s)
       - Kết thúc: Nhận Thẻ Safir Tier 3 (+4 GH/s khai thác 24h liên tục)
    3. Tự động thu hoạch Kho Mỏ (Vault) khi đủ 100% (3600s).
    4. Tự động Tap đào đá tối đa 240/240 lượt/ngày.
    5. Tự động điểm danh hàng ngày Streak (/api/streak/claim).
    6. Tự động kích hoạt ca chạy tiếp theo (Handover Chaining 24/7).
=============================================================================
"""

import os
import sys
import time
import json
import random
import hashlib
import asyncio
import re
import base64
import urllib.parse
import urllib3
import requests
from colorama import init, Fore, Style

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestWebViewRequest

urllib3.disable_warnings()
init(autoreset=True)

# -----------------------------------------------------------------
# CẤU HÌNH HỆ THỐNG
# -----------------------------------------------------------------
_raw_id = os.getenv("TELEGRAM_API_ID", "").strip()
API_ID = int(_raw_id) if _raw_id.isdigit() else 34333329
API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip() or "4f9371f95000578c84dbc670aaf1f819"

DEFAULT_SESSION_ACC1 = (
    "1BVtsOHIBuxmpWiBJ9hvwV9pSrzWw5U2I5Fe20Ww8l1LCk9rnsG6T6lLZEJXZE1JJC_qUH_yyWHnRoedRNI5lJYnfjRN4gyGeDrCxquDU12ZflrpCz0VLhMZx2C0LlyUCy2eHRSRE1wUCpEYZaymL0P7Z9eAHwMy4Oogewh5TqyO4x4MF6j0yTq8Zvfpv43O4aQDzErNv3GRqpx8DXBcOJIMP9yVhq-Mby5VH5J9cF-h-bJ5ws3xKjA4GY7YKjHxDt9OI-Zr7mr-V3qZy99UxJooThJj51f2RqOKhODdLh9XZQ0ygSoAd3iFAZDOPMEo8Ch5TrrzLXi2Q3N0HorIL1JfV0xoFQlY="
)
DEFAULT_SESSION_ACC2 = (
    "1BVtsOHIBuzoeRtBOmpNGh2sdyxpZ5e0nY4MrFe-6KKbmJPaM0YnCJiKRI0L9mEh1C5rwqLQqucj456LRF7vV1YIPjZNqL6JevLM0Ww3FTml1NoKdwsiPINfsy9MbBlBhKOvha7py44L4pK5aEXjwpjpoNj4LaSmtWaPiQPufJuTwPB86f4gYjSeXM3HtxhnFU7MtHR5vbZPBa9N2HQSlt2BMB47q00DbQVtvYA37R3R-TrtV2MtwixL9ozChADFq38NYcw4eRyRwKrkobVLccvz0_hvqgHXiQbrfcFLLRkRGwGlRCB-Ew4YhLLdnCbG1hjGEfxUrp9MRmF0JvS-u20MfAuvlcgQ="
)
DEFAULT_SESSION_ACC3 = (
    "1BVtsOHIBuxrTG6Dt9a8C_J7D3bm1disV_mQiY_mw7AP5Gp-cEVAlKU1cfvOJiDnU6yi7PInfBRG_wJBQ3uNc-1kOa8fM3ITgUcE7YkaCd77FoBTgIFqw6gMYeRfVJOS1U9S_botQyX5764dx94NBfHHm8HuQKejs0PrdAJQq6WUTDS3mkijWRWIvO4SwXSUrM5yNOFoGIrav8Mbuyl5ZFQaDPg_kwa11NT4kiqov8rVx0virTbGbQudyFeG80kP4zW2CxcuL6TObemIPJgR_2-jb8zVQRQMiI4oN829ZCfHU2JCQY2S2clWwI7onZV8AhYP1LoDBiu32dgQPuk4brS-r1DtkySc="
)
STRING_SESSION = (
    os.getenv("TELEGRAM_STRING_SESSION")
    or os.getenv("TELEGRAM_STRING_SESSION_ACC1")
    or os.getenv("STRING_SESSION")
    or DEFAULT_SESSION_ACC1
)

API_BASE = "https://gramstone.46-101-143-24.sslip.io"
SESSION_FILE_PATH = os.getenv("TELEGRAM_SESSION_PATH", "C:/Users/Administrator/Downloads/kiemtien_autoplay/telepet_acc1.session")


def log(tag, msg, color=Fore.WHITE):
    t_str = time.strftime('%H:%M:%S')
    print(f"{Fore.LIGHTBLACK_EX}[{t_str}]{Style.RESET_ALL} {color}[{tag:<14}]{Style.RESET_ALL} {msg}", flush=True)


class GramstoneBot:
    def __init__(self, string_session=None, session_path=None):
        self.string_session = string_session or STRING_SESSION
        self.session_path = session_path
        self.init_data = None
        self.user_obj = None
        self.user_id = None
        self.username = None
        self.sig = ""
        self.dcs = ""
        self.last_init_time = 0
        self.balance = 0.0
        self.bonus_ghs = 0.0
        self.total_ghs = 0.0
        
        # Giả lập phần cứng chuẩn Android
        self.ua = (
            "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.135 "
            "Mobile Safari/537.36 Telegram-Android/11.5.0"
        )
        self.platform = "Linux armv8l"
        self.lang = "vi,en-US;q=0.9"
        self.tz = "Asia/Ho_Chi_Minh"
        self.screen = "384x854x24"
        self.dpr = 2.8125
        self.cores = 8
        self.mem = 8
        self.touch = 5
        self.gpu = "Qualcomm / Adreno (TM) 750"
        self.canvas_sig = "sig"
        
        raw_fp = "||".join(str(x) for x in [
            self.ua, self.platform, self.lang, self.tz, self.screen, self.dpr,
            self.cores, self.mem, self.touch, self.gpu, self.canvas_sig
        ])
        self.fp_hash = hashlib.sha256(raw_fp.encode('utf-8')).hexdigest()

    async def fetch_tg_init_data(self):
        log("TELEGRAM", "Đang kết nối Telegram để lấy tgWebAppData Gramstone tươi mới...", Fore.CYAN)
        client = None
        try:
            if self.session_path and os.path.exists(self.session_path):
                client = TelegramClient(self.session_path, API_ID, API_HASH)
            else:
                client = TelegramClient(StringSession(self.string_session), API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                log("TELEGRAM_ERR", "❌ Phiên Telegram không được ủy quyền!", Fore.RED)
                await client.disconnect()
                return False

            bot_entity = await client.get_entity("gramstone_bot")
            res = await client(RequestWebViewRequest(
                peer=bot_entity,
                bot=bot_entity,
                url=f"{API_BASE}/",
                platform="android"
            ))
            await client.disconnect()

            frag = res.url.split("#tgWebAppData=")[1].split("&tgWebAppVersion")[0]
            self.init_data = urllib.parse.unquote(frag)
            params = dict(urllib.parse.parse_qsl(self.init_data))
            self.user_obj = json.loads(params.get("user", "{}"))
            self.user_id = str(self.user_obj.get("id"))
            self.username = self.user_obj.get("username", "")
            self.sig = params.get("signature", "")
            
            # Tính data_check_string
            pairs = []
            for k, v in urllib.parse.parse_qsl(self.init_data):
                if k not in ['hash', 'signature']:
                    pairs.append(f"{k}={v}")
            pairs.sort()
            raw = "\n".join(pairs)
            self.dcs = base64.b64encode(raw.encode('utf-8')).decode('ascii').replace('+', '-').replace('/', '_').rstrip('=')
            
            self.last_init_time = time.time()
            log("TELEGRAM", f"✅ Đã lấy tgWebAppData mới nhất cho @{self.username} ({self.user_id})!", Fore.GREEN)
            return True
        except Exception as e:
            log("TELEGRAM_ERR", f"Lỗi lấy WebApp Data: {e}", Fore.RED)
            if client and client.is_connected():
                await client.disconnect()
            return False

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "x-telegram-init-data": self.init_data,
            "x-gs-fp": self.fp_hash,
            "User-Agent": self.ua,
            "Origin": API_BASE,
            "Referer": f"{API_BASE}/"
        }

    async def get_valid_auth(self):
        """
        Đảm bảo LUÔN CÓ phiên đăng nhập hợp lệ:
        - Tự động lấy lại init_data nếu chưa có hoặc đã quá 25 phút (1500s).
        - Nếu authenticate trả về lỗi hoặc 401 -> tự động re-auth Telethon ngay.
        """
        now = time.time()
        if not self.init_data or (now - self.last_init_time > 1500):
            log("AUTH_REFRESH", "🔄 Phiên tgWebAppData đã quá 25 phút. Đang làm mới từ Telegram...", Fore.CYAN)
            await self.fetch_tg_init_data()

        d = self.authenticate()
        if not d:
            log("AUTH_RETRY", "⚠️ Phiên không hợp lệ hoặc hết hạn. Đang kết nối lại Telethon lấy token mới...", Fore.YELLOW)
            ok = await self.fetch_tg_init_data()
            if ok:
                d = self.authenticate()
        return d

    def authenticate(self):
        if not self.init_data:
            return None
        device_info = {
            "ua": self.ua,
            "platform": self.platform,
            "tgPlatform": "android",
            "tgVersion": "11.5.0",
            "lang": self.lang,
            "tz": self.tz,
            "screen": self.screen,
            "dpr": self.dpr,
            "cores": self.cores,
            "mem": self.mem,
            "touch": self.touch,
            "gpu": self.gpu
        }
        body = {
            "telegram_id": self.user_id,
            "username": self.username,
            "first_name": self.user_obj.get("first_name", "GramMadenci"),
            "start_param": "",
            "device": device_info
        }
        try:
            r = requests.post(f"{API_BASE}/api/auth", headers=self.get_headers(), json=body, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    u = data.get("user", {})
                    self.balance = float(u.get("balance", 0.0))
                    self.bonus_ghs = float(u.get("bonus_ghs", 0))
                    m = data.get("mining", {})
                    self.total_ghs = float(m.get("totalGhs", 100))
                    log("AUTH", f"✅ Đăng nhập Gramstone! User: @{self.username} | Số dư: {self.balance:.6f} TON | Tốc độ: {self.total_ghs:.1f} GH/s (+{self.bonus_ghs} GH/s)", Fore.GREEN)
                    return data
            log("AUTH_ERR", f"Lỗi đăng nhập HTTP {r.status_code}: {r.text[:120]}", Fore.RED)
        except Exception as e:
            log("AUTH_ERR", f"Ngoại lệ đăng nhập: {e}", Fore.RED)
        return None

    def claim_streak(self):
        try:
            r = requests.post(f"{API_BASE}/api/streak/claim", headers=self.get_headers(), json={"telegram_id": self.user_id}, timeout=10)
            if r.status_code == 200:
                d = r.json()
                if d.get("ok"):
                    log("STREAK", f"🎉 Điểm danh thành công Ngày {d.get('streakDay', 1)}: +{d.get('rewardGhs', 0)} GH/s!", Fore.GREEN)
        except Exception:
            pass

    def tap_mine(self):
        taps_done = 0
        for _ in range(25):
            try:
                r = requests.post(f"{API_BASE}/api/tap", headers=self.get_headers(), json={"telegram_id": self.user_id}, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("ok"):
                        taps_done += 1
                        time.sleep(random.uniform(0.5, 0.9))
                    else:
                        break
                elif r.status_code == 429:
                    log("TAP", "🛑 Đã hoàn thành tối đa 240/240 lượt Tap hôm nay!", Fore.MAGENTA)
                    return
                else:
                    break
            except Exception:
                break
        if taps_done > 0:
            log("TAP", f"✅ Đã thực hiện {taps_done} lượt Tap đào đá!", Fore.GREEN)

    def check_and_claim_vault(self, auth_data):
        m = auth_data.get("mining", {}) if auth_data else {}
        claim_interval = m.get("claimIntervalSec", 3600)
        elapsed = m.get("elapsedSec", 0)
        pct = min(100.0, (elapsed / claim_interval) * 100)
        
        log("VAULT", f"⛏️ Kho mỏ Vault: {elapsed:.0f}/{claim_interval}s ({pct:.1f}%)", Fore.CYAN)
        if elapsed >= claim_interval:
            log("VAULT", "🎉 Kho mỏ đã đạt 100%! Tiến hành thu hoạch miễn phí (TOPLA)...", Fore.YELLOW)
            try:
                r = requests.post(f"{API_BASE}/api/claim", headers=self.get_headers(), json={"telegram_id": self.user_id, "watched_ad": False}, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("ok"):
                        u = d.get("user", {})
                        new_bal = float(u.get("balance", self.balance))
                        log("VAULT", f"🎉 THU HOẠCH KHO MỎ THÀNH CÔNG! Số dư mới: {new_bal:.6f} TON", Fore.GREEN)
                        self.balance = new_bal
                        return True
            except Exception as e:
                log("VAULT_ERR", f"Lỗi thu hoạch: {e}", Fore.RED)
        return False

    def boost_moonpool_card_chain(self, tier=3):
        """
        CƠ CHẾ MOONPOOL CHÍNH XÁC 100% CÓ SERVER-SIDE CONFIRMATION:
        Bước 1: Bắt đầu ca Thẻ (/api/cards/start).
        Bước 2: Adsgram (Block 54796) + Full Event Tracking (Render/Show/Reward).
                + Poll /api/ads/adsgram-status cho tới khi ready: true.
                + Gửi /api/cards/step (adsgram) với auto retry nếu too_early.
        Bước 3: Xem QC Gigapub (Delay chuẩn 8.5s).
                + Gửi /api/cards/step (gigapub).
        Bước 4: Xem QC Monetag (Delay chuẩn 8.5s).
                + Gửi /api/cards/step (monetag).
        Bước 5: Nhận Thẻ Safir Tier 3 (+4 GH/s)!
        """
        log("CARD_MOONPOOL", f"🚀 Kích hoạt quy trình xem QC cày Thẻ Mỏ Tier {tier} (Safir +4 GH/s)...", Fore.CYAN)
        
        # 1. Bắt đầu ca Thẻ
        try:
            r_start = requests.post(f"{API_BASE}/api/cards/start", headers=self.get_headers(), json={"telegram_id": self.user_id, "tier": tier}, timeout=10)
        except Exception as e:
            log("CARD_WARN", f"Lỗi mạng khi mở thẻ: {e}", Fore.YELLOW)
            return False, 30

        if r_start.status_code == 401:
            log("CARD_WARN", "Token hết hạn khi mở thẻ. Yêu cầu re-auth...", Fore.YELLOW)
            self.init_data = None
            return False, 5
            
        if r_start.status_code != 200:
            log("CARD_WARN", f"Chưa thể nhận thẻ mới (HTTP {r_start.status_code})", Fore.YELLOW)
            return False, 60
            
        d_start = r_start.json()
        if not d_start.get("ok"):
            code = d_start.get("code")
            retry_in = d_start.get("retry_in_sec", 60)
            if code == "cooldown":
                log("CARD_COOLDOWN", f"⏳ Thẻ mỏ đang trong thời gian nghỉ ({retry_in}s)", Fore.LIGHTBLACK_EX)
            else:
                log("CARD_WARN", f"Thông báo: {d_start.get('error', code)} (Thử lại sau {retry_in}s)", Fore.YELLOW)
            return False, retry_in

        ses = d_start.get("session", {})
        ses_id = ses.get("id")
        log("CARD_MOONPOOL", f"Phiên Thẻ Mỏ #{ses_id} đã mở! Bắt đầu chuỗi 3 QC (Adsgram -> Gigapub -> Monetag)...", Fore.CYAN)

        try:
            # --- BƯỚC 1: ADSGRAM (Full Tracking & Server Verification) ---
            log("STEP1_ADSGRAM", "Bước 1/3: Đang tải quảng cáo Adsgram (Block 54796)...", Fore.YELLOW)
            ad_headers = {
                'User-Agent': self.ua,
                'Origin': API_BASE,
                'Referer': f"{API_BASE}/",
                'Accept': 'application/json',
                'X-Requested-With': 'org.telegram.messenger'
            }
            adv_params = {
                'blockId': '54796',
                'tg_id': self.user_id,
                'tg_platform': 'android',
                'platform': 'Linux armv8l',
                'language': 'vi',
                'top_domain': 'sslip.io',
                'signature': self.sig,
                'data_check_string': self.dcs,
                'sdk_version': '2.2.5'
            }
            try:
                r_adv = requests.get('https://api.adsgram.ai/adv', headers=ad_headers, params=adv_params, timeout=12)
                if r_adv.status_code == 200:
                    render_u, show_u, reward_u = None, None, None
                    for u in re.findall(r'https://api\.adsgram\.ai/event\?[^\s\'\"<>]+', r_adv.text):
                        if 'type=Render' in u: render_u = u
                        elif 'type=Show' in u: show_u = u
                        elif 'type=Reward' in u: reward_u = u

                    if render_u: 
                        try: requests.get(render_u, headers=ad_headers, timeout=5)
                        except Exception: pass
                    time.sleep(1)
                    if show_u: 
                        try: requests.get(show_u, headers=ad_headers, timeout=5)
                        except Exception: pass
                    
                    log("STEP1_ADSGRAM", "Đang xem video Adsgram (8.5s theo quy định card_min_step_sec)...", Fore.YELLOW)
                    time.sleep(8.5)

                    if reward_u:
                        try: requests.get(reward_u, headers=ad_headers, timeout=8)
                        except Exception: pass
            except Exception as e:
                log("STEP1_WARN", f"Lỗi gọi Adsgram network: {e}", Fore.LIGHTBLACK_EX)
                time.sleep(8.5)

            # Chờ Adsgram server verification
            log("STEP1_ADSGRAM", "Đang chờ xác nhận máy chủ Adsgram (/api/ads/adsgram-status)...", Fore.YELLOW)
            for _ in range(8):
                try:
                    r_stat = requests.post(f"{API_BASE}/api/ads/adsgram-status", headers=self.get_headers(), json={"telegram_id": self.user_id}, timeout=5)
                    if r_stat.status_code == 200 and r_stat.json().get("ready"):
                        log("STEP1_ADSGRAM", "✓ Máy chủ Adsgram đã xác nhận sẵn sàng!", Fore.GREEN)
                        break
                except Exception:
                    pass
                time.sleep(1.5)

            # Báo cáo Step 1 cho Gramstone (Kiên trì chờ xác nhận tối đa 35s)
            counted_s1 = False
            for step_try in range(16):
                try:
                    r_s1 = requests.post(f"{API_BASE}/api/cards/step", headers=self.get_headers(), json={"telegram_id": self.user_id, "session_id": ses_id, "network": "adsgram"}, timeout=10).json()
                    if r_s1.get("ok") and r_s1.get("counted"):
                        counted_s1 = True
                        log("STEP1_ADSGRAM", "✓ Bước 1/3 Adsgram hoàn thành thành công!", Fore.GREEN)
                        break
                    code = r_s1.get("code")
                    if code == "too_early":
                        ms = int(r_s1.get("retry_in_ms", 1500))
                        time.sleep((ms / 1000.0) + 0.5)
                        continue
                    elif code == "ad_unverified":
                        time.sleep(2.0)
                        continue
                except Exception:
                    pass
                time.sleep(2.0)

            if not counted_s1:
                log("STEP1_WARN", "Chưa xác nhận được Bước 1 Adsgram. Kết thúc phiên.", Fore.YELLOW)
                requests.post(f"{API_BASE}/api/cards/finish", headers=self.get_headers(), json={"telegram_id": self.user_id, "session_id": ses_id}, timeout=10)
                return False, 30

            # --- BƯỚC 2: GIGAPUB ---
            log("STEP2_GIGAPUB", "Bước 2/3: Đang xem QC Gigapub (8.5s chuẩn quy định)...", Fore.YELLOW)
            time.sleep(8.5)
            counted_s2 = False
            for step_try in range(6):
                try:
                    r_s2 = requests.post(f"{API_BASE}/api/cards/step", headers=self.get_headers(), json={"telegram_id": self.user_id, "session_id": ses_id, "network": "gigapub"}, timeout=10).json()
                    if r_s2.get("ok") and r_s2.get("counted"):
                        counted_s2 = True
                        log("STEP2_GIGAPUB", "✓ Bước 2/3 Gigapub hoàn thành!", Fore.GREEN)
                        break
                    if r_s2.get("code") == "too_early":
                        ms = int(r_s2.get("retry_in_ms", 1500))
                        time.sleep((ms / 1000.0) + 0.5)
                        continue
                except Exception:
                    pass
                time.sleep(2.0)

            # --- BƯỚC 3: MONETAG ---
            log("STEP3_MONETAG", "Bước 3/3: Đang xem QC Monetag (8.5s chuẩn quy định)...", Fore.YELLOW)
            time.sleep(8.5)
            counted_s3 = False
            for step_try in range(6):
                try:
                    r_s3 = requests.post(f"{API_BASE}/api/cards/step", headers=self.get_headers(), json={"telegram_id": self.user_id, "session_id": ses_id, "network": "monetag"}, timeout=10).json()
                    if r_s3.get("ok") and r_s3.get("counted"):
                        counted_s3 = True
                        log("STEP3_MONETAG", "✓ Bước 3/3 Monetag hoàn thành!", Fore.GREEN)
                        break
                    if r_s3.get("code") == "too_early":
                        ms = int(r_s3.get("retry_in_ms", 1500))
                        time.sleep((ms / 1000.0) + 0.5)
                        continue
                except Exception:
                    pass
                time.sleep(2.0)

            # --- KẾT THÚC VÀ NHẬN THẺ SAFIR CẤP 3 ---
            r_fin = requests.post(f"{API_BASE}/api/cards/finish", headers=self.get_headers(), json={"telegram_id": self.user_id, "session_id": ses_id}, timeout=10).json()
            if r_fin.get("ok"):
                c = r_fin.get("card", {})
                u = r_fin.get("user", {})
                self.bonus_ghs = u.get("bonus_ghs", self.bonus_ghs)
                log("CARD_SUCCESS", f"🎉🎉🎉 ĐÃ NHẬN THÀNH CÔNG THẺ SAFIR TIER {c.get('tier', 3)} (+{c.get('ghs', 4)} GH/s)! Tổng Bonus GH/s: +{self.bonus_ghs}", Fore.GREEN)
                return True, 0
            else:
                log("CARD_WARN", f"Hoàn tất chuỗi: {r_fin.get('close_reason', 'done')}", Fore.YELLOW)
        except Exception as e:
            log("CARD_ERR", f"Lỗi trong chuỗi QC Moonpool: {e}", Fore.RED)
            try: requests.post(f"{API_BASE}/api/cards/finish", headers=self.get_headers(), json={"telegram_id": self.user_id, "session_id": ses_id}, timeout=10)
            except Exception: pass
        return False, 30

    async def run_cycle(self):
        auth_data = await self.get_valid_auth()
        if not auth_data:
            return

        self.claim_streak()
        self.tap_mine()
        self.check_and_claim_vault(auth_data)
        self.boost_moonpool_card_chain(tier=3)


def trigger_next_shift(workflow_file="game1_gramstone.yml"):
    repo = (os.getenv("GITHUB_REPOSITORY") or "nthanhhung0122-max/gram").strip()
    wf = (os.getenv("WORKFLOW_FILE") or workflow_file).strip()
    pat = (os.getenv("GH_PAT") or os.getenv("GITHUB_TOKEN") or "").strip()
    if not wf or not pat:
        log("HANDOVER", "Không có WORKFLOW_FILE hoặc GitHub Token để retrigger.", Fore.YELLOW)
        return False
    log("HANDOVER", f"🔄 Chuẩn bị chuyển giao ca làm việc tiếp theo trên {repo} ({wf})...", Fore.CYAN)
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{wf}/dispatches"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        r = requests.post(url, json={"ref": "main"}, headers=headers, timeout=15)
        if r.status_code in [200, 204]:
            log("HANDOVER", f"✅ Đã kích hoạt thành công ca chạy tiếp theo trên {repo} ({wf})!", Fore.GREEN)
            return True
        else:
            log("HANDOVER", f"Phản hồi dispatch: {r.status_code} {r.text}", Fore.YELLOW)
    except Exception as e:
        log("HANDOVER", f"Lỗi retrigger: {e}", Fore.RED)
    return False


async def run_loop_247(bot_instance, interval_mins=0):
    raw_rt = os.getenv("MAX_RUNTIME_SECONDS", "17500").strip()
    max_runtime = int(raw_rt) if raw_rt.isdigit() else 17500
    start_time = time.time()
    card_count = 0
    last_vault_check = 0
    last_tap_check = 0
    
    log("CONTINUOUS", "🔥 CHẾ ĐỘ CÀY QUẢNG CÁO THẺ MỎ SAFIR TIER 3 LIÊN TỤC 24/7 ĐÃ BẬT!", Fore.GREEN)
    
    auth_data = await bot_instance.get_valid_auth()
    if not auth_data:
        log("INIT_ERR", "Không thể xác thực ban đầu.", Fore.RED)
        return

    while True:
        elapsed = time.time() - start_time
        if elapsed >= max_runtime:
            log("HANDOVER", f"⏰ Hoàn thành ca trực ({elapsed/3600:.1f}h). Tự động chuyển giao ca tiếp theo...", Fore.CYAN)
            trigger_next_shift("game1_gramstone.yml")
            break

        now = time.time()
        # Đảm bảo LUÔN CÓ auth hợp lệ trước mỗi lượt (tự động re-auth từ Telethon nếu token quá 25 phút)
        auth_data = await bot_instance.get_valid_auth()
        if not auth_data:
            log("RETRY", "Chờ 15s trước khi thử lại kết nối Telegram...", Fore.YELLOW)
            await asyncio.sleep(15)
            continue
        
        # 1. Kiểm tra Kho Mỏ Vault & Streak định kỳ mỗi 5 phút
        if now - last_vault_check >= 300:
            try:
                bot_instance.check_and_claim_vault(auth_data)
                bot_instance.claim_streak()
                last_vault_check = now
            except Exception as e:
                log("VAULT_ERR", f"Lỗi check vault: {e}", Fore.RED)

        # 2. Đào đá Tap định kỳ mỗi 10 phút
        if now - last_tap_check >= 600:
            try:
                bot_instance.tap_mine()
                last_tap_check = now
            except Exception as e:
                log("TAP_ERR", f"Lỗi tap: {e}", Fore.RED)

        # 3. CÀY THẺ SAFIR TIER 3 (+4 GH/s) LIÊN TỤC
        try:
            ok, retry_in = bot_instance.boost_moonpool_card_chain(tier=3)
            if ok:
                card_count += 1
                log("CONTINUOUS", f"🎉 [THẺ MỎ #{card_count}] Đã nhận +4 GH/s! Nghỉ 10s trước ca tiếp theo...", Fore.CYAN)
                await asyncio.sleep(10)
            else:
                wait_sec = max(10, retry_in if retry_in > 0 else 30)
                log("CONTINUOUS", f"⏳ Chờ hồi chiêu Thẻ Mỏ ({wait_sec}s) để cày tiếp...", Fore.LIGHTBLACK_EX)
                await asyncio.sleep(wait_sec)
        except Exception as e:
            log("CARD_ERR", f"Lỗi cày thẻ: {e}", Fore.RED)
            await asyncio.sleep(15)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bot Auto Gramstone ($GRAM/$TON) 24/7")
    parser.add_argument("--acc", type=int, default=1, choices=[1, 2, 3], help="Tài khoản chạy (1, 2 hoặc 3)")
    parser.add_argument("--loop", type=int, default=0, help="Số phút lặp lại (0 để chạy 1 lần)")
    args, _ = parser.parse_known_args()

    session_map = {1: DEFAULT_SESSION_ACC1, 2: DEFAULT_SESSION_ACC2, 3: DEFAULT_SESSION_ACC3}
    session_str = os.getenv(f"TELEGRAM_STRING_SESSION_ACC{args.acc}") or os.getenv("TELEGRAM_STRING_SESSION") or session_map.get(args.acc, DEFAULT_SESSION_ACC1)
    
    session_file = f"C:/Users/Administrator/Downloads/kiemtien_autoplay/telepet_acc{args.acc}.session"
    if not os.path.exists(session_file):
        session_file = None

    print(Fore.CYAN + f"""
=============================================================================
  BOT AUTO GRAMSTONE ($GRAM / $TON) 24/7 - BẢN FIX TRIỆT ĐỂ MOONPOOL 2026
  Acc: {args.acc} | Tự động Thu Hoạch Vault 100% | Cày Thẻ Mỏ Safir Tier 3 | Tap Đào Đá
=============================================================================
    """ + Style.RESET_ALL)
    
    bot = GramstoneBot(string_session=session_str, session_path=session_file)
    if args.loop > 0:
        await run_loop_247(bot, interval_mins=args.loop)
    else:
        await bot.run_cycle()


if __name__ == "__main__":
    asyncio.run(main())
