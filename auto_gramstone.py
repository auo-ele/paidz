#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  BOT AUTO GRAMSTONE ($GRAM / $TON) 24/7 - BẢN HUMAN BEHAVIOR CHỐNG BAN 100%
  Platform: Gramstone Mini App (https://gramstone.46-101-143-24.sslip.io/)
  Telegram Bot: @gramstone_bot
  
  TÍNH NĂNG CHỐNG BAN & CHỐNG CỜ AUTOCLICKER 100%:
    1. GIỜ NGỦ TỰ NHIÊN: Tự động nghỉ ngơi hoàn toàn 00:30 - 05:15 sáng (Giờ VN).
    2. PHIÊN CHƠI NGẪU NHIÊN: Hoạt động 20-30 phút, nghỉ giải lao 5-8 phút như người thật.
    3. BIOMETRIC TAP SIMULATION: Micro-tap 6-10 lượt, Gaussian Jitter 1.8s-3.8s,
       tọa độ ngón tay elip, micro-pauses chống cờ "auto clicker" vĩnh viễn.
    4. VÂN TAY PHẦN CỨNG RIÊNG BIỆT: Galaxy S24 Ultra, Xiaomi 13 Pro, Pixel 8 Pro.
    5. CÀY THẺ SAFIR TIER 3: Adsgram V2 Event Tracking + Gigapub + Monetag (+4 GH/s).
    6. TỰ ĐỘNG CHUYỂN GIAO CA 24/7 (Handover Chaining).
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

from human_behavior import (
    get_device_profile,
    get_gramstone_fp,
    handle_sleep_schedule_async,
    check_sleep_window,
    SessionBurstManager,
    get_human_tap_delay,
    get_human_touch_coords,
    get_vn_time
)

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
    def __init__(self, acc_id=1, string_session=None, session_path=None):
        self.acc_id = int(acc_id)
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
        
        # Cấu hình thiết bị độc lập 100%
        dev = get_device_profile(self.acc_id)
        self.device_name = dev["device_name"]
        self.ua = dev["ua"]
        self.platform = dev["platform"]
        self.screen = dev["screen"]
        self.dpr = dev["dpr"]
        self.cores = dev["cores"]
        self.mem = dev["ram"]
        self.gpu = f"{dev['webgl_vendor']} / {dev['webgl_renderer']}"
        self.canvas_sig = f"canvas_sig_{self.acc_id}"
        self.fp_hash = get_gramstone_fp(self.acc_id)

    async def fetch_tg_init_data(self):
        log("TELEGRAM", f"Đang kết nối Telegram ({self.device_name}) để lấy tgWebAppData Gramstone...", Fore.CYAN)
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
            log("TELEGRAM", f"✅ Đã lấy WebApp Data mới nhất: @{self.username} (Acc {self.acc_id})!", Fore.GREEN)
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
        """Đảm bảo token init_data luôn tươi mới (< 25 phút), tự động re-auth từ Telethon"""
        if not self.init_data or (time.time() - self.last_init_time) > 1500:
            log("AUTH_REFRESH", "🔄 Phiên tgWebAppData đã quá 25 phút. Đang làm mới...", Fore.YELLOW)
            ok = await self.fetch_tg_init_data()
            if not ok:
                return None

        body = {
            "initData": self.init_data,
            "telegram_id": self.user_id,
            "username": self.username
        }
        try:
            r = requests.post(f"{API_BASE}/api/auth", headers=self.get_headers(), json=body, timeout=12)
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    u = data.get("user", {})
                    self.balance = float(u.get("balance", self.balance))
                    self.bonus_ghs = float(u.get("bonus_hashrate", self.bonus_ghs))
                    self.total_ghs = float(u.get("total_hashrate", self.total_ghs))
                    return data
            elif r.status_code == 401:
                log("AUTH_EXPIRED", "Token hết hạn (401). Đang re-auth Telethon...", Fore.YELLOW)
                self.init_data = None
                return await self.get_valid_auth()
        except Exception as e:
            log("AUTH_ERR", f"Lỗi kết nối auth: {e}", Fore.RED)
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
        """Micro-Tap Human Simulation: Chống cờ 'auto clicker' vĩnh viễn với Gaussian Jitter & Elip Coords"""
        taps_done = 0
        num_taps = random.randint(6, 10)
        for i in range(num_taps):
            coords = get_human_touch_coords()
            payload = {
                "telegram_id": self.user_id,
                "x": coords["x"],
                "y": coords["y"],
                "duration": coords["hold_duration_ms"]
            }
            try:
                r = requests.post(f"{API_BASE}/api/tap", headers=self.get_headers(), json=payload, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("ok"):
                        taps_done += 1
                        sleep_s = get_human_tap_delay()
                        # Micro-pause 2-4s ngẫu nhiên sau mỗi 3 lần chạm
                        if (i + 1) % 3 == 0:
                            sleep_s += random.uniform(1.8, 3.5)
                        time.sleep(sleep_s)
                    else:
                        break
                elif r.status_code == 429:
                    log("TAP", "🛑 Đã đạt giới hạn tap mỏ hôm nay!", Fore.MAGENTA)
                    return
                else:
                    break
            except Exception:
                break
        if taps_done > 0:
            log("TAP", f"✅ [HUMAN TAP] Đã gõ {taps_done} lượt tự nhiên (Tọa độ elip + Gaussian Jitter)!", Fore.GREEN)

    def check_and_claim_vault(self, auth_data):
        m = auth_data.get("mining", {}) if auth_data else {}
        claim_interval = m.get("claimIntervalSec", 3600)
        elapsed = m.get("elapsedSec", 0)
        pct = min(100.0, (elapsed / claim_interval) * 100)
        
        log("VAULT", f"⛏️ Kho mỏ Vault: {elapsed:.0f}/{claim_interval}s ({pct:.1f}%)", Fore.CYAN)
        if elapsed >= claim_interval:
            log("VAULT", "🎉 Kho mỏ đã đầy! Tiến hành thu hoạch miễn phí (TOPLA)...", Fore.YELLOW)
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

    def trigger_adsgram_events(self, block_id="54796"):
        """Gửi Render, Show, Reward tới Adsgram chuẩn định dạng quốc tế (language=en)"""
        ad_headers = {
            "User-Agent": self.ua,
            "Origin": API_BASE,
            "Referer": f"{API_BASE}/",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "org.telegram.messenger"
        }
        adv_params = {
            "blockId": str(block_id),
            "tg_id": self.user_id,
            "tg_platform": "android",
            "platform": self.platform,
            "language": "en",
            "top_domain": "sslip.io",
            "signature": self.sig,
            "data_check_string": self.dcs,
            "sdk_version": "2.2.5"
        }
        try:
            r = requests.get("https://api.adsgram.ai/adv", headers=ad_headers, params=adv_params, timeout=15)
            urls = []
            if r.status_code == 200:
                try:
                    d = r.json()
                    trackings = d.get("banners", [{}])[0].get("banner", {}).get("trackings", [])
                    for t in trackings:
                        v = t.get("value")
                        if v: urls.append(v)
                except Exception:
                    pass
                if not urls:
                    urls = re.findall(r"https://api\.adsgram\.ai/event\?[^\s\'\"]+", r.text)

            for u in urls:
                try: requests.get(u, headers=ad_headers, timeout=8)
                except Exception: pass

            log("ADSGRAM", f"Đang xem video Adsgram ({len(urls)} tracking events)...", Fore.YELLOW)
            time.sleep(8.5)
            return True
        except Exception as e:
            log("ADSGRAM_WARN", f"Lỗi gọi Adsgram network: {e}", Fore.LIGHTBLACK_EX)
            time.sleep(8.5)
            return False

    def wait_for_adsgram_confirmation(self, max_tries=8):
        """Chờ máy chủ Gramstone xác nhận voucher Adsgram qua POST /api/ads/adsgram-status"""
        for i in range(max_tries):
            try:
                r = requests.post(f"{API_BASE}/api/ads/adsgram-status", headers=self.get_headers(), json={"telegram_id": self.user_id}, timeout=10)
                if r.status_code == 200 and r.json().get("ready"):
                    log("ADSGRAM", f"✓ Máy chủ Gramstone đã xác thực Adsgram hoàn tất (lần thử #{i+1})!", Fore.GREEN)
                    return True
            except Exception:
                pass
            time.sleep(1.5)
        return False

    def report_card_step(self, session_id, network, max_tries=14):
        """Báo cáo bước thẻ lên /api/cards/step chuẩn frontend pcStep của Gramstone"""
        started = time.time()
        for attempt in range(max_tries):
            try:
                r = requests.post(
                    f"{API_BASE}/api/cards/step",
                    headers=self.get_headers(),
                    json={"telegram_id": self.user_id, "session_id": session_id, "network": network},
                    timeout=10
                )
                d = r.json() if r.status_code in [200, 400, 409, 429, 500] else {}
                if d.get("ok") and d.get("counted"):
                    return True, d.get("session")
                code = d.get("code", "")
                if code in ["chain_complete", "session_closed"]:
                    return True, d.get("session")
                if code == "out_of_order":
                    log("CARD_WARN", f"[{network}] Server báo out_of_order (bước trước chưa hoàn thành)!", Fore.RED)
                    return False, None
                if code == "too_early":
                    retry_ms = d.get("retry_in_ms", 2000)
                    wait_s = min(8.0, float(retry_ms) / 1000.0) + 0.35
                    time.sleep(wait_s)
                    continue
                if code == "ad_unverified":
                    if time.time() - started > 30.0:
                        log("CARD_WARN", f"[{network}] Adsgram verify timeout (30s)", Fore.YELLOW)
                        return False, None
                    time.sleep(1.8)
                    continue
                time.sleep(1.5)
            except Exception:
                time.sleep(1.5)
        return False, None

    def finish_card(self, session_id, max_tries=4):
        """Hoàn tất chuỗi thẻ và nhận phần thưởng qua POST /api/cards/finish"""
        for attempt in range(max_tries):
            try:
                r = requests.post(f"{API_BASE}/api/cards/finish", headers=self.get_headers(), json={"telegram_id": self.user_id, "session_id": session_id}, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("ok"):
                        return d
            except Exception:
                pass
            time.sleep(1.5)
        return None

    def boost_moonpool_card_chain(self, tier=3, auth_data=None):
        """Cơ chế cày Thẻ Safir Tier 3 (+4 GH/s) với Adsgram -> Gigapub -> Monetag chuẩn tuần tự 100%"""
        cards = auth_data.get("cards", {}) if auth_data else {}
        cd_left = cards.get("cooldown_left_sec", 0)
        if cd_left > 0:
            log("CARD_COOLDOWN", f"⏳ Thẻ Mỏ đang hồi chiêu ({cd_left}s)...", Fore.LIGHTBLACK_EX)
            return False, cd_left

        daily = cards.get("daily", {})
        if daily.get("cap", 0) > 0 and daily.get("used", 0) >= daily.get("cap", 0):
            log("CARD_CAP", "🛑 Đã đạt giới hạn thẻ hôm nay!", Fore.YELLOW)
            return False, 300

        ses_id = None
        start_step = 0
        open_ses = cards.get("open")
        if open_ses and open_ses.get("id") and open_ses.get("status") == "open":
            exp = open_ses.get("expires_at", 0)
            srv_time = int(time.time() * 1000)
            if exp > srv_time:
                ses_id = open_ses.get("id")
                start_step = open_ses.get("steps_done", 0)
                tier = open_ses.get("tier", tier)
                log("CARD_MOONPOOL", f"Phát hiện ca Thẻ #{ses_id} (Tier {tier}) dở dang (Bước {start_step}/{tier}). Tiếp tục...", Fore.CYAN)
            else:
                log("CARD_MOONPOOL", f"Phiên thẻ cũ #{open_ses.get('id')} đã hết hạn. Đang đóng...", Fore.YELLOW)
                self.finish_card(open_ses.get("id"))
                time.sleep(1.5)

        if not ses_id:
            log("CARD_MOONPOOL", f"🚀 Kích hoạt quy trình xem QC cày Thẻ Mỏ Tier {tier} (+4 GH/s)...", Fore.CYAN)
            try:
                r_start = requests.post(f"{API_BASE}/api/cards/start", headers=self.get_headers(), json={"telegram_id": self.user_id, "tier": tier}, timeout=10)
                if r_start.status_code == 401:
                    log("CARD_WARN", "Token hết hạn khi mở thẻ. Re-auth...", Fore.YELLOW)
                    self.init_data = None
                    return False, 5
                if r_start.status_code != 200:
                    log("CARD_WARN", f"Chưa thể nhận thẻ mới (HTTP {r_start.status_code})", Fore.YELLOW)
                    return False, 60
                d_start = r_start.json()
                if not d_start.get("ok"):
                    err = d_start.get("error", "")
                    cd = d_start.get("cooldown_left_sec") or d_start.get("retry_in_sec", 60)
                    log("CARD_WARN", f"Chưa sẵn sàng: {err} (Hồi chiêu {cd}s)", Fore.YELLOW)
                    return False, cd
                ses = d_start.get("session", {})
                ses_id = ses.get("id")
                start_step = ses.get("steps_done", 0)
                log("CARD_MOONPOOL", f"✅ Khởi tạo thành công ca Thẻ #{ses_id} (Tier {tier})! Chuỗi {tier} bước: Adsgram -> Gigapub -> Monetag", Fore.GREEN)
            except Exception as e:
                log("CARD_ERR", f"Lỗi mở thẻ: {e}", Fore.RED)
                return False, 30

        chain = ["adsgram", "gigapub", "monetag"][:tier]
        total = len(chain)

        # Chạy tuần tự tuyệt đối
        for idx in range(start_step, total):
            net = chain[idx]
            step_num = idx + 1
            log(f"STEP{step_num}_{net.upper()}", f"Bước {step_num}/{total}: Đang xem QC {net.upper()}...", Fore.YELLOW)

            if net == "adsgram":
                self.trigger_adsgram_events("54796")
                self.wait_for_adsgram_confirmation()
            else:
                time.sleep(8.5)

            counted, updated_ses = self.report_card_step(ses_id, net, max_tries=14)
            if counted:
                log(f"STEP{step_num}_{net.upper()}", f"✓ Bước {step_num}/{total} ({net}) hoàn tất thành công!", Fore.GREEN)
            else:
                log(f"STEP{step_num}_WARN", f"Chưa xác nhận được Bước {step_num} ({net}). Đóng phiên an toàn để nhận thẻ từng phần...", Fore.YELLOW)
                self.finish_card(ses_id)
                return False, 60

        # Hoàn tất nhận thẻ
        d_fin = self.finish_card(ses_id)
        if d_fin and d_fin.get("ok"):
            card = d_fin.get("card", {})
            u = d_fin.get("user", {})
            m = d_fin.get("mining", {})
            tot = m.get("totalGhs", self.total_ghs)
            bns = u.get("bonus_ghs", self.bonus_ghs)
            self.total_ghs = float(tot)
            self.bonus_ghs = float(bns)
            log("CARD_SUCCESS", f"🎉🎉🎉 ĐÃ NHẬN THÀNH CÔNG THẺ MỎ TIER {card.get('tier', tier)} (+{card.get('ghs', 4)} GH/s)! Tổng công suất: {self.total_ghs} GH/s (Thẻ kích hoạt: +{self.bonus_ghs} GH/s)", Fore.GREEN)
            return True, 60
        else:
            log("CARD_WARN", f"Kết thúc phiên thẻ #{ses_id}.", Fore.YELLOW)
            return False, 60

    async def run_cycle(self):
        auth_data = await self.get_valid_auth()
        if not auth_data:
            return
        log("STATUS", f"💎 Gramstone User: @{self.username} | Số dư: {self.balance:.6f} TON | Tốc độ đào: {self.total_ghs} GH/s", Fore.CYAN)
        self.claim_streak()
        self.tap_mine()
        self.check_and_claim_vault(auth_data)
        self.boost_moonpool_card_chain(tier=3, auth_data=auth_data)


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
    
    log("HUMAN_ENGINE", f"🔥 BẬT CHẾ ĐỘ NGƯỜI THẬT: Phiên chơi 20-30p | Nghỉ 5-8p | Giờ ngủ VN 00:30-05:15!", Fore.GREEN)
    
    # Khởi tạo Quản lý Phiên chơi ngẫu nhiên (Session Burst)
    burst_mgr = SessionBurstManager(burst_min_mins=20, burst_max_mins=30, break_min_mins=5, break_max_mins=8)
    
    while True:
        # 1. KIỂM TRA GIỜ NGỦ TỰ NHIÊN (00:30 - 05:15 VN)
        slept = await handle_sleep_schedule_async(log_func=lambda msg: log("SLEEP", msg, Fore.MAGENTA))
        if slept:
            burst_mgr.start_new_burst()

        elapsed = time.time() - start_time
        if elapsed >= max_runtime:
            log("HANDOVER", f"⏰ Hoàn thành ca trực ({elapsed/3600:.1f}h). Tự động chuyển giao ca tiếp theo...", Fore.CYAN)
            wf_target = f"game1_gramstone_acc{bot_instance.acc_id}.yml" if bot_instance.acc_id > 1 else "game1_gramstone.yml"
            trigger_next_shift(wf_target)
            break

        # 2. KIỂM TRA HẾT PHIÊN CHƠI (SESSION BURST) -> NGHỈ GIẢI LAO TỰ NHIÊN (HUMAN BREAK)
        if burst_mgr.is_burst_finished():
            break_sec = burst_mgr.get_break_duration()
            log("HUMAN_BREAK", f"☕ [PHIÊN #{burst_mgr.burst_count} XONG] Đóng app, nghỉ ngơi tự nhiên {break_sec//60} phút như thói quen người thật...", Fore.CYAN)
            
            slept_during_break = 0
            while slept_during_break < break_sec:
                in_sleep, _ = check_sleep_window()
                if in_sleep:
                    await handle_sleep_schedule_async(log_func=lambda msg: log("SLEEP", msg, Fore.MAGENTA))
                    break
                step = min(60, break_sec - slept_during_break)
                await asyncio.sleep(step)
                slept_during_break += step
            
            log("HUMAN_BREAK", f"📱 [MỞ LẠI APP] Bắt đầu phiên chơi mới #{burst_mgr.burst_count + 1}...", Fore.GREEN)
            burst_mgr.start_new_burst()
            continue

        # 3. TRONG PHIÊN CHƠI HOẠT ĐỘNG
        now = time.time()
        auth_data = await bot_instance.get_valid_auth()
        if not auth_data:
            log("RETRY", "Chờ 15s trước khi thử lại kết nối Telegram...", Fore.YELLOW)
            await asyncio.sleep(15)
            continue
        
        # 3.1. Thu hoạch Vault & Streak
        if now - last_vault_check >= 300:
            try:
                bot_instance.check_and_claim_vault(auth_data)
                bot_instance.claim_streak()
                last_vault_check = now
            except Exception as e:
                log("VAULT_ERR", f"Lỗi check vault: {e}", Fore.RED)

        # 3.2. Micro-tap đào đá tự nhiên
        if now - last_tap_check >= 600:
            try:
                bot_instance.tap_mine()
                last_tap_check = now
            except Exception as e:
                log("TAP_ERR", f"Lỗi tap: {e}", Fore.RED)

        # 3.3. Cày Thẻ Safir Tier 3
        try:
            ok, retry_in = bot_instance.boost_moonpool_card_chain(tier=3, auth_data=auth_data)
            if ok:
                card_count += 1
                log("CONTINUOUS", f"🎉 [THẺ MỎ #{card_count}] Đã nhận +4 GH/s! Nghỉ 15s trước lượt kế...", Fore.CYAN)
                await asyncio.sleep(15)
            else:
                wait_sec = max(15, retry_in if retry_in > 0 else 35)
                log("CONTINUOUS", f"⏳ Chờ hồi chiêu Thẻ Mỏ ({wait_sec}s)...", Fore.LIGHTBLACK_EX)
                await asyncio.sleep(wait_sec)
        except Exception as e:
            log("CARD_ERR", f"Lỗi cày thẻ: {e}", Fore.RED)
            await asyncio.sleep(15)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bot Auto Gramstone ($GRAM/$TON) 24/7 Human Behavior")
    parser.add_argument("--acc", type=int, default=1, choices=[1, 2, 3], help="Tài khoản chạy (1, 2 hoặc 3)")
    parser.add_argument("--loop", type=int, default=0, help="Số phút lặp lại (0 để chạy 1 lần)")
    args, _ = parser.parse_known_args()

    session_map = {1: DEFAULT_SESSION_ACC1, 2: DEFAULT_SESSION_ACC2, 3: DEFAULT_SESSION_ACC3}
    session_str = os.getenv(f"TELEGRAM_STRING_SESSION_ACC{args.acc}") or os.getenv("TELEGRAM_STRING_SESSION") or session_map.get(args.acc, DEFAULT_SESSION_ACC1)
    
    session_file = f"C:/Users/Administrator/Downloads/kiemtien_autoplay/telepet_acc{args.acc}.session"
    if not os.path.exists(session_file):
        session_file = None

    bot = GramstoneBot(acc_id=args.acc, string_session=session_str, session_path=session_file)
    print(Fore.CYAN + f"""
=============================================================================
  BOT AUTO GRAMSTONE ($GRAM / $TON) 24/7 - HUMAN BEHAVIOR ANTI-BAN 100%
  Acc: {args.acc} ({bot.device_name}) | Giờ ngủ VN 00:30-05:15 | Phiên 20-30p + Nghỉ 5-8p
=============================================================================
    """ + Style.RESET_ALL)
    
    if args.loop > 0:
        await run_loop_247(bot, interval_mins=args.loop)
    else:
        await bot.run_cycle()


if __name__ == "__main__":
    asyncio.run(main())
