"""
Tool Auto Cày Eggram 24/7 Cho 3 Tài Khoản (Phiên bản Tối ưu Siêu Tốc 5.2s + Pipelining Cooldown)
Bot Telegram: @eggramearnbot
Backend: https://eggram.209-38-193-227.sslip.io

Tối ưu hóa:
- Tốc độ xem QC rút gọn 5.2s/bước (Server quy định ad_min_step_sec: 5).
- Tự động bắt đúng thời gian cooldown_left_sec + 0.5s để vào ca mới tức thì.
- Pipelining: Tận dụng thời gian cooldown để gom giỏ trứng (/api/claim) và điểm danh.
- Full Signature & Data Check String cho Adsgram verification.
- Handover Chaining 24/7 trên GitHub Actions.
"""

import os
import sys
import time
import json
import re
import base64
import argparse
import urllib.parse
from datetime import datetime, timezone, timedelta

import requests
from colorama import init, Fore, Style

# Telethon
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestWebViewRequest

from human_behavior import (
    get_device_profile,
    report_device_to_server,
    handle_sleep_schedule_sync,
    check_sleep_window,
    SessionBurstManager,
    get_vn_time
)

init(autoreset=True)

# ----------------- CẤU HÌNH CỐ ĐỊNH -----------------
API_ID = 26569107
API_HASH = "8156cfc55db2ca6ec31fec793bf81d1e"
BOT_USERNAME = "eggramearnbot"
API_BASE = "https://eggram.209-38-193-227.sslip.io"

# 3 Account Sessions
DEFAULT_SESSION_ACC1 = "1BVtsOHIBuxmpWiBJ9hvwV9pSrzWw5U2I5Fe20Ww8l1LCk9rnsG6T6lLZEJXZE1JJC_qUH_yyWHnRoedRNI5lJYnfjRN4gyGeDrCxquDU12ZflrpCz0VLhMZx2C0LlyUCy2eHRSRE1wUCpEYZaymL0P7Z9eAHwMy4Oogewh5TqyO4x4MF6j0yTq8Zvfpv43O4aQDzErNv3GRqpx8DXBcOJIMP9yVhq-Mby5VH5J9cF-h-bJ5ws3xKjA4GY7YKjHxDt9OI-Zr7mr-V3qZy99UxJooThJj51f2RqOKhODdLh9XZQ0ygSoAd3iFAZDOPMEo8Ch5TrrzLXi2Q3N0HorIL1JfV0xoFQlY="
DEFAULT_SESSION_ACC2 = "1BVtsOHIBuzoeRtBOmpNGh2sdyxpZ5e0nY4MrFe-6KKbmJPaM0YnCJiKRI0L9mEh1C5rwqLQqucj456LRF7vV1YIPjZNqL6JevLM0Ww3FTml1NoKdwsiPINfsy9MbBlBhKOvha7py44L4pK5aEXjwpjpoNj4LaSmtWaPiQPufJuTwPB86f4gYjSeXM3HtxhnFU7MtHR5vbZPBa9N2HQSlt2BMB47q00DbQVtvYA37R3R-TrtV2MtwixL9ozChADFq38NYcw4eRyRwKrkobVLccvz0_hvqgHXiQbrfcFLLRkRGwGlRCB-Ew4YhLLdnCbG1hjGEfxUrp9MRmF0JvS-u20MfAuvlcgQ="
DEFAULT_SESSION_ACC3 = "1BVtsOHIBuxrTG6Dt9a8C_J7D3bm1disV_mQiY_mw7AP5Gp-cEVAlKU1cfvOJiDnU6yi7PInfBRG_wJBQ3uNc-1kOa8fM3ITgUcE7YkaCd77FoBTgIFqw6gMYeRfVJOS1U9S_botQyX5764dx94NBfHHm8HuQKejs0PrdAJQq6WUTDS3mkijWRWIvO4SwXSUrM5yNOFoGIrav8Mbuyl5ZFQaDPg_kwa11NT4kiqov8rVx0virTbGbQudyFeG80kP4zW2CxcuL6TObemIPJgR_2-jb8zVQRQMiI4oN829ZCfHU2JCQY2S2clWwI7onZV8AhYP1LoDBiu32dgQPuk4brS-r1DtkySc="

try:
    with open('sessions.json', 'r') as f:
        _s = json.load(f)
        DEFAULT_SESSION_ACC1 = _s.get('acc1', DEFAULT_SESSION_ACC1)
        DEFAULT_SESSION_ACC2 = _s.get('acc2', DEFAULT_SESSION_ACC2)
        DEFAULT_SESSION_ACC3 = _s.get('acc3', DEFAULT_SESSION_ACC3)
except Exception:
    pass

VN_TZ = timezone(timedelta(hours=7))

def now_vn():
    return datetime.now(VN_TZ).strftime("%H:%M:%S")

def log(tag, msg, color=Fore.WHITE):
    print(f"{Fore.LIGHTBLACK_EX}[{now_vn()}]{Style.RESET_ALL} {Fore.CYAN}[{tag}]{Style.RESET_ALL} {color}{msg}{Style.RESET_ALL}", flush=True)


class EggramBot:
    def __init__(self, acc_id=1, string_session=None):
        self.acc_id = acc_id
        session_map = {
            1: DEFAULT_SESSION_ACC1,
            2: DEFAULT_SESSION_ACC2,
            3: DEFAULT_SESSION_ACC3
        }
        self.string_session = (
            string_session
            or os.getenv(f"TELEGRAM_STRING_SESSION_ACC{acc_id}")
            or os.getenv("TELEGRAM_STRING_SESSION")
            or session_map.get(acc_id)
        )
        self.init_data = None
        self.user_obj = None
        self.user_id = None
        self.username = None
        self.sig = ""
        self.dcs = ""
        self.last_init_time = 0
        self.adsgram_block_id = "58569"
        self.http = requests.Session()
        
        dev = get_device_profile(self.acc_id)
        self.device_name = dev["device_name"]
        self.ua = dev["ua"]
        self.platform = dev["platform"]

    def get_headers(self):
        h = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'User-Agent': self.ua,
            'Origin': API_BASE,
            'Referer': f"{API_BASE}/",
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty'
        }
        if self.init_data:
            h['X-Telegram-Init-Data'] = self.init_data
        return h

    async def refresh_tg_data(self):
        """Kết nối Telethon lấy initData mới nhất từ bot"""
        log(f"ACC{self.acc_id}_TELEGRAM", "Đang kết nối Telegram lấy WebApp token...", Fore.YELLOW)
        client = TelegramClient(StringSession(self.string_session), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            log(f"ACC{self.acc_id}_AUTH_ERR", "Session Telegram không hợp lệ hoặc đã hết hạn!", Fore.RED)
            await client.disconnect()
            return False

        me = await client.get_me()
        self.user_id = str(me.id)
        self.username = me.username or me.first_name
        log(f"ACC{self.acc_id}_AUTH", f"Đăng nhập Telegram thành công: {me.first_name} (@{me.username}) ID: {me.id}", Fore.GREEN)

        bot = await client.get_input_entity(BOT_USERNAME)
        res = await client(RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform='android',
            url=f"{API_BASE}/"
        ))
        await client.disconnect()

        raw_url = res.url
        fragment = urllib.parse.urlparse(raw_url).fragment
        params = urllib.parse.parse_qs(fragment)
        init_data = params.get('tgWebAppData', [None])[0]
        if not init_data:
            init_data = urllib.parse.unquote(fragment.replace('tgWebAppData=', ''))

        self.init_data = init_data
        self.last_init_time = time.time()

        # Parse sig & dcs cho Adsgram verification
        try:
            q_dict = dict(urllib.parse.parse_qsl(init_data))
            self.sig = q_dict.get("signature", "")
            u_json = q_dict.get("user")
            if u_json:
                self.user_obj = json.loads(u_json)
                self.user_id = str(self.user_obj.get("id", self.user_id))

            pairs = []
            for k, v in urllib.parse.parse_qsl(init_data):
                if k not in ("hash", "signature"):
                    pairs.append(f"{k}={v}")
            pairs.sort()
            raw = "\n".join(pairs)
            self.dcs = base64.b64encode(raw.encode('utf-8')).decode('ascii').replace('+', '-').replace('/', '_').rstrip('=')
        except Exception as e:
            log(f"ACC{self.acc_id}_PARSE_WARN", f"Lỗi parse data_check_string: {e}", Fore.YELLOW)

        log(f"ACC{self.acc_id}_TOKEN", f"✓ Đã cấp token WebApp mới (User ID: {self.user_id})", Fore.GREEN)
        return True

    def ensure_auth(self):
        """Đảm bảo token init_data hợp lệ (< 50 phút)"""
        if not self.init_data or (time.time() - self.last_init_time) > 3000:
            import asyncio
            return asyncio.run(self.refresh_tg_data())
        return True

    def auth_state(self):
        """Gọi /api/auth để lấy full state game"""
        self.ensure_auth()
        try:
            r = self.http.post(f"{API_BASE}/api/auth", headers=self.get_headers(), json={}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    state = data.get("state", {})
                    cfg_nets = state.get("config", {}).get("networks", {})
                    if cfg_nets.get("adsgram", {}).get("block_id"):
                        self.adsgram_block_id = str(cfg_nets["adsgram"]["block_id"])
                    if not getattr(self, "_device_reported", False):
                        ok_fp, fp_res = report_device_to_server(API_BASE, self.init_data, self.acc_id, "Eggram")
                        if ok_fp:
                            log(f"ACC{self.acc_id}_FP", f"✅ [DEVICE-OK] Đã đăng ký thiết bị sạch: {self.device_name} (fp={fp_res})", Fore.GREEN)
                            self._device_reported = True
                        else:
                            log(f"ACC{self.acc_id}_FP_WARN", f"⚠️ Gửi fp thiết bị: {fp_res}", Fore.YELLOW)
                    return state
            elif r.status_code == 401:
                log(f"ACC{self.acc_id}_AUTH", "Token hết hạn 401. Đang làm mới...", Fore.YELLOW)
                self.init_data = None
                self.ensure_auth()
                return self.auth_state()
        except Exception as e:
            log(f"ACC{self.acc_id}_NET_ERR", f"Lỗi kết nối auth: {e}", Fore.RED)
        return None

    def claim_basket(self, state=None):
        """Thu hoạch giỏ trứng vào số dư GRAM"""
        if not state:
            state = self.auth_state()
        if not state:
            return False

        vault = state.get("vault", {})
        claimable = vault.get("claimable", False)
        pending = float(vault.get("pending", 0))

        if claimable and pending > 0:
            log(f"ACC{self.acc_id}_BASKET", f"🧺 Giỏ trứng đang có {pending:.6f} GRAM. Đang gom...", Fore.CYAN)
            try:
                r = self.http.post(f"{API_BASE}/api/claim", headers=self.get_headers(), json={}, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("ok"):
                        amt = float(data.get("amount", 0))
                        new_bal = float(data.get("state", {}).get("balance", 0))
                        log(f"ACC{self.acc_id}_CLAIMED", f"✓ Đã gom +{amt:.6f} GRAM! (Ví: {new_bal:.6f} GRAM)", Fore.GREEN)
                        return True
            except Exception as e:
                log(f"ACC{self.acc_id}_CLAIM_ERR", f"Lỗi gom trứng: {e}", Fore.RED)
        return False

    def check_tasks(self, state=None):
        """Tự động điểm danh Daily Streak và nhiệm vụ"""
        if not state:
            state = self.auth_state()
        if not state:
            return

        tasks = state.get("tasks", [])
        for t in tasks:
            tid = t.get("id")
            status = t.get("status")
            if tid == "streak" and status == "claimable":
                try:
                    r = self.http.post(f"{API_BASE}/api/tasks/streak/claim", headers=self.get_headers(), json={}, timeout=15)
                    if r.status_code == 200 and r.json().get("ok"):
                        log(f"ACC{self.acc_id}_STREAK", "✓ Đã nhận thưởng Daily Streak thành công!", Fore.GREEN)
                except Exception as e:
                    log(f"ACC{self.acc_id}_TASK_ERR", f"Lỗi claim streak: {e}", Fore.RED)

            elif tid in ("channel", "group") and status == "available":
                try:
                    self.http.post(f"{API_BASE}/api/tasks/{tid}/check", headers=self.get_headers(), json={}, timeout=10)
                except:
                    pass

    def trigger_adsgram_events(self):
        """Gửi Render, Show, Reward tới Adsgram với tốc độ tối ưu 5.2s"""
        ad_headers = {
            'User-Agent': self.ua,
            'Origin': API_BASE,
            'Referer': f"{API_BASE}/",
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'org.telegram.messenger'
        }
        adv_params = {
            'blockId': self.adsgram_block_id,
            'tg_id': self.user_id,
            'tg_platform': 'android',
            'platform': getattr(self, 'platform', 'Linux armv8l'),
            'language': 'en',
            'top_domain': 'sslip.io',
            'signature': self.sig,
            'data_check_string': self.dcs,
            'sdk_version': '2.2.5'
        }
        try:
            r_adv = self.http.get('https://api.adsgram.ai/adv', headers=ad_headers, params=adv_params, timeout=20)
            if r_adv.status_code == 200:
                render_u, show_u, reward_u = None, None, None
                
                # Cách 1: Parse từ banner trackings
                try:
                    d_json = r_adv.json()
                    banners = d_json.get('banners', [])
                    if banners:
                        trackings = banners[0].get('banner', {}).get('trackings', [])
                        for tr in trackings:
                            name = tr.get('name')
                            val = tr.get('value')
                            if name == 'render': render_u = val
                            elif name == 'show': show_u = val
                            elif name == 'reward': reward_u = val
                except:
                    pass

                # Cách 2: Regex fallback
                if not reward_u:
                    for u in re.findall(r'https://api\.adsgram\.ai/event\?[^\s\'"<>]+', r_adv.text):
                        if 'type=Render' in u or 'trackingtypeid=1' in u: render_u = u
                        elif 'type=Show' in u or 'trackingtypeid=0' in u or 'trackingtypeid=2' in u: show_u = u
                        elif 'type=Reward' in u or 'trackingtypeid=14' in u or 'trackingtypeid=3' in u: reward_u = u

                if render_u:
                    try: self.http.get(render_u, headers=ad_headers, timeout=10)
                    except: pass
                if show_u:
                    try: self.http.get(show_u, headers=ad_headers, timeout=10)
                    except: pass
                
                # TỐI ƯU SIÊU TỐC: Đợi đúng 5.2s (đủ chuẩn ad_min_step_sec: 5)
                time.sleep(5.2)

                if reward_u:
                    try: self.http.get(reward_u, headers=ad_headers, timeout=10)
                    except: pass
                    time.sleep(1.8)

                log(f"ACC{self.acc_id}_ADSGRAM", f"✓ Đã gửi hoàn tất xác thực Adsgram (Block {self.adsgram_block_id})", Fore.GREEN)
                return True
        except Exception as e:
            log(f"ACC{self.acc_id}_ADSGRAM_WARN", f"Lỗi Adsgram connection: {e}", Fore.LIGHTBLACK_EX)
            time.sleep(5.2)
        return False

    def report_step(self, session_id, network, max_tries=16):
        """Báo cáo hoàn thành bước QC với auto-retry mili-giây chuẩn xác"""
        for t in range(1, max_tries + 1):
            try:
                r = self.http.post(
                    f"{API_BASE}/api/fish/step",
                    headers=self.get_headers(),
                    json={"session_id": session_id, "network": network},
                    timeout=15
                )
                if r.status_code == 200:
                    d = r.json()
                    if d.get("counted"):
                        return True, d.get("session")
                elif r.status_code == 429:
                    log(f"ACC{self.acc_id}_429", "Bị rate limit 429. Nghỉ 35s...", Fore.YELLOW)
                    time.sleep(35)
                    continue
                elif r.status_code == 409:
                    d = r.json() if r.text.startswith('{') else {}
                    code = d.get("code")
                    if code in ("chain_complete", "session_closed", "fish_already_granted"):
                        return True, d.get("session")
                    elif code == "out_of_order":
                        log(f"ACC{self.acc_id}_STEP_WARN", f"Server báo out_of_order ({network})!", Fore.RED)
                        return False, None
                    elif code == "too_early":
                        ms = int(d.get("retry_in_ms", 1200))
                        time.sleep(max(0.5, (ms / 1000.0) + 0.15))
                        continue
                    elif code == "ad_unverified":
                        time.sleep(1.8)
                        continue
            except Exception:
                time.sleep(1.5)
            time.sleep(1.5)
        return False, None

    def hatch_egg_chain(self):
        """Quy trình Ấp Trứng Vàng Tier 3 Tối ưu Siêu Tốc (+12 ⚡/h trong 24h)"""
        state = self.auth_state()
        if not state:
            return False, 15

        daily = state.get("daily", {})
        daily_left = daily.get("left", 80)
        if daily_left <= 0:
            log(f"ACC{self.acc_id}_DAILY_CAP", "Đã đạt giới hạn ấp gà hôm nay (80/80 con). Nghỉ ngơi...", Fore.YELLOW)
            return False, 300

        open_ses = state.get("open_session")
        ses_id = None
        chain = ["adsgram", "gigapub", "monetag"]
        start_step = 0

        if open_ses and open_ses.get("id"):
            exp = open_ses.get("expires_at", 0)
            srv_time = state.get("server_time", int(time.time() * 1000))
            if exp > srv_time and open_ses.get("status") == "open":
                ses_id = open_ses.get("id")
                chain = open_ses.get("chain", chain)
                start_step = open_ses.get("steps_done", 0)
                log(f"ACC{self.acc_id}_HATCH", f"Phát hiện ca ấp trứng #{ses_id} đang mở (Bước {start_step}/{len(chain)}). Tiếp tục...", Fore.CYAN)
            else:
                log(f"ACC{self.acc_id}_HATCH", f"Ca ấp trứng cũ #{open_ses.get('id')} đã hết hạn. Đang dọn dẹp...", Fore.YELLOW)
                try: self.http.post(f"{API_BASE}/api/fish/finish", headers=self.get_headers(), json={"session_id": open_ses.get("id")}, timeout=8)
                except Exception: pass
                time.sleep(1.5)

        # Nếu chưa có session, kiểm tra chính xác thời gian cooldown
        if not ses_id:
            cards = state.get("cards", [])
            card_tier3 = next((c for c in cards if c.get("tier") == 3), None)
            if card_tier3:
                cd_left = card_tier3.get("cooldown_left_sec", 0)
                if cd_left > 0:
                    log(f"ACC{self.acc_id}_COOLDOWN", f"⏳ Trứng đang hồi chiêu ({cd_left}s). Tranh thủ gom giỏ & nhiệm vụ...", Fore.LIGHTBLACK_EX)
                    # PIPELINING: Tận dụng thời gian cooldown làm các tác vụ phụ
                    self.claim_basket(state)
                    self.check_tasks(state)
                    # Nghỉ CHÍNH XÁC đúng thời gian cooldown còn lại + 0.5s để vào ca mới tức thì
                    return False, max(1.0, cd_left + 0.5)

            # Bắt đầu ca ấp mới
            log(f"ACC{self.acc_id}_START", "🥚 Bắt đầu mở phiên Ấp Trứng Vàng Tier 3 (+12 ⚡/h)...", Fore.CYAN)
            try:
                r_start = self.http.post(f"{API_BASE}/api/fish/start", headers=self.get_headers(), json={"tier": 3}, timeout=15)
                if r_start.status_code == 200:
                    d_start = r_start.json()
                    if d_start.get("ok"):
                        ses = d_start.get("session", {})
                        ses_id = ses.get("id")
                        chain = ses.get("chain", chain)
                        start_step = ses.get("steps_done", 0)
                        log(f"ACC{self.acc_id}_SESSION", f"Phiên #{ses_id} kích hoạt! Chuỗi {len(chain)} bước: {chain}", Fore.GREEN)
                    else:
                        code = d_start.get('code')
                        retry_in = d_start.get('retry_in_sec', 15)
                        log(f"ACC{self.acc_id}_START_FAIL", f"Thông báo: {code} (Chờ {retry_in}s)", Fore.YELLOW)
                        return False, retry_in
                else:
                    return False, 15
            except Exception as e:
                log(f"ACC{self.acc_id}_START_ERR", f"Lỗi khởi động ca ấp: {e}", Fore.RED)
                return False, 15

        # Thực hiện từng bước QC với độ trễ 5.2s siêu tốc
        total = len(chain)
        for idx in range(start_step, total):
            net = chain[idx]
            step_num = idx + 1
            log(f"ACC{self.acc_id}_STEP", f"Bước {step_num}/{total}: Xem QC {net.upper()} (Tối ưu 5.2s)...", Fore.YELLOW)

            if net == "adsgram":
                self.trigger_adsgram_events()
            elif net == "gigapub":
                time.sleep(5.2)
            elif net == "monetag":
                time.sleep(5.2)

            counted, updated_ses = self.report_step(ses_id, net, max_tries=16)
            if counted:
                log(f"ACC{self.acc_id}_STEP_OK", f"✓ Bước {step_num}/{total} ({net}) hoàn tất!", Fore.GREEN)
            else:
                log(f"ACC{self.acc_id}_STEP_FAIL", f"Chưa xác nhận được bước {step_num} ({net}). Dừng chuỗi để bảo vệ tài khoản...", Fore.YELLOW)
                try: self.http.post(f"{API_BASE}/api/fish/finish", headers=self.get_headers(), json={"session_id": ses_id}, timeout=8)
                except Exception: pass
                return False, 10

        # Hoàn tất ấp trứng
        log(f"ACC{self.acc_id}_FINISH", f"🐣 Hoàn tất ấp trứng phiên #{ses_id}...", Fore.CYAN)
        for attempt in range(4):
            try:
                r_fin = self.http.post(f"{API_BASE}/api/fish/finish", headers=self.get_headers(), json={"session_id": ses_id}, timeout=15)
                if r_fin.status_code == 200:
                    d_fin = r_fin.json()
                    if d_fin.get("ok"):
                        st = d_fin.get("state", {})
                        hen_count = len(st.get("fish", []))
                        power = st.get("power", {}).get("total", 0)
                        log(f"ACC{self.acc_id}_HATCHED", f"🎉 ẤP TRỨNG THÀNH CÔNG! Đàn gà: {hen_count} con | Năng suất: {power} ⚡ (trứng/giờ)!", Fore.GREEN)
                        # Gom trứng ngay sau khi nở
                        self.claim_basket(st)
                        return True, 1.0
                    else:
                        code = d_fin.get("code")
                        if code in ("session_closed", "fish_already_granted", "no_steps"):
                            return True, 1.0
                time.sleep(1.5)
            except Exception:
                time.sleep(1.5)

        return False, 10

    def print_status_dashboard(self, state=None):
        if not state:
            state = self.auth_state()
        if not state:
            return

        bal = float(state.get("balance", 0))
        power = state.get("power", {}).get("total", 0)
        vault = state.get("vault", {})
        pending = float(vault.get("pending", 0))
        cap = float(vault.get("capacity", 0))
        hens = len(state.get("fish", []))
        daily = state.get("daily", {})
        daily_used = daily.get("used", 0)
        daily_cap = daily.get("cap", 80)

        log(f"ACC{self.acc_id}_STATUS",
            f"💎 Số dư: {bal:.6f} GRAM | ⚡ Tốc độ: {power} quả/h | 🐔 Đàn gà: {hens} con | 🧺 Giỏ: {pending:.6f}/{cap:.6f} | 🎯 Hôm nay: {daily_used}/{daily_cap} gà",
            Fore.MAGENTA
        )


def dispatch_next_shift(repo, workflow_file, token):
    """Kích hoạt ca làm việc tiếp theo trước khi hết giờ (Chạy 24/7)"""
    log("HANDOVER", f"🔄 Đang kích hoạt ca kế tiếp trên repo {repo} ({workflow_file})...", Fore.YELLOW)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Eggram-247-Handover"
    }
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/dispatches"
    try:
        r = requests.post(url, headers=headers, json={"ref": "main"}, timeout=15)
        if r.status_code == 204:
            log("HANDOVER", "✓ Kích hoạt ca tiếp theo THÀNH CÔNG! Chuyển giao chạy liên tục 24/7.", Fore.GREEN)
            return True
        else:
            log("HANDOVER_ERR", f"Lỗi kích hoạt ca: HTTP {r.status_code} - {r.text}", Fore.RED)
    except Exception as e:
        log("HANDOVER_ERR", f"Lỗi mạng khi kích hoạt ca: {e}", Fore.RED)
    return False


def run_bot(acc_id=1, max_runtime=17500):
    start_time = time.time()
    bot = EggramBot(acc_id=acc_id)

    log(f"MAIN_ACC{acc_id}", f"🚀 KHỞI ĐỘNG AUTO EGGRAM SIÊU TỐC 24/7 CHO TÀI KHOẢN {acc_id}", Fore.GREEN)
    
    state = bot.auth_state()
    if not state:
        log(f"MAIN_ACC{acc_id}", "Không thể kết nối trò chơi. Đang thử lại...", Fore.RED)
        time.sleep(3)
        state = bot.auth_state()

    bot.print_status_dashboard(state)
    bot.check_tasks(state)
    bot.claim_basket(state)

    last_status_print = 0

    log(f"MAIN_ACC{acc_id}", f"🔥 BẬT CHẾ ĐỘ NGƯỜI THẬT: Phiên chơi 20-30p | Nghỉ 5-8p | Giờ ngủ VN 00:30-05:15!", Fore.GREEN)
    burst_mgr = SessionBurstManager(burst_min_mins=20, burst_max_mins=30, break_min_mins=5, break_max_mins=8)

    while True:
        # 1. Kiểm tra Giờ ngủ tự nhiên (00:30 - 05:15 VN)
        slept = handle_sleep_schedule_sync(log_func=lambda msg: log(f"MAIN_ACC{acc_id}", msg, Fore.MAGENTA))
        if slept:
            burst_mgr.start_new_burst()

        elapsed = time.time() - start_time
        gh_repo = os.getenv("GITHUB_REPOSITORY")
        gh_pat = os.getenv("GH_PAT") or os.getenv("PAT_TOKEN")
        gh_wf = os.getenv("WORKFLOW_NAME", f"game4_eggram_acc{acc_id}.yml")

        if max_runtime > 0 and elapsed >= max_runtime:
            log(f"MAIN_ACC{acc_id}", f"Đã chạy {elapsed/3600:.1f}h (đạt giới hạn 4.8h). Bắt đầu chuyển giao ca...", Fore.YELLOW)
            if gh_repo and gh_pat:
                dispatch_next_shift(gh_repo, gh_wf, gh_pat)
            break

        # 2. Hết phiên chơi -> Nghỉ giải lao tự nhiên (Human Break)
        if burst_mgr.is_burst_finished():
            break_sec = burst_mgr.get_break_duration()
            log(f"MAIN_ACC{acc_id}", f"☕ [PHIÊN #{burst_mgr.burst_count} XONG] Đóng app, nghỉ ngơi tự nhiên {break_sec//60} phút...", Fore.CYAN)
            
            slept_during_break = 0
            while slept_during_break < break_sec:
                in_sleep, _ = check_sleep_window()
                if in_sleep:
                    handle_sleep_schedule_sync(log_func=lambda msg: log(f"MAIN_ACC{acc_id}", msg, Fore.MAGENTA))
                    break
                step = min(60, break_sec - slept_during_break)
                time.sleep(step)
                slept_during_break += step
            
            log(f"MAIN_ACC{acc_id}", f"📱 [MỞ LẠI APP] Bắt đầu phiên chơi mới #{burst_mgr.burst_count + 1}...", Fore.GREEN)
            burst_mgr.start_new_burst()
            continue

        now_sec = time.time()
        if now_sec - last_status_print > 900:
            bot.print_status_dashboard()
            last_status_print = now_sec

        # 3. Trong phiên chơi: Ấp Trứng Vàng Tier 3
        try:
            ok, sleep_sec = bot.hatch_egg_chain()
        except Exception as e:
            log(f"MAIN_ACC{acc_id}_LOOP_ERR", f"Lỗi chu trình ấp trứng: {e}", Fore.RED)
            sleep_sec = 15

        sleep_sec = max(1.0, float(sleep_sec))
        time.sleep(sleep_sec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto Eggram 24/7 Cloud Bot")
    parser.add_argument("--acc", type=int, default=1, help="Account ID (1, 2, hoặc 3)")
    parser.add_argument("--runtime", type=int, default=17500, help="Max runtime in seconds before handover")
    parser.add_argument("--once", action="store_true", help="Run once then exit (for testing)")
    args = parser.parse_args()

    if args.once:
        bot = EggramBot(acc_id=args.acc)
        st = bot.auth_state()
        bot.print_status_dashboard(st)
        bot.claim_basket(st)
        bot.check_tasks(st)
        bot.hatch_egg_chain()
        bot.print_status_dashboard()
    else:
        run_bot(acc_id=args.acc, max_runtime=args.runtime)
