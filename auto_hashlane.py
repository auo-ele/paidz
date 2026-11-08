#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  BOT AUTO HASHLANE ($TON) 24/7 PRO - TỐI ƯU HÓA TOÀN DIỆN CHUẨN MOONPOOL
  Platform: HashLane Mini App (https://46-101-192-249.sslip.io/app/)
  Telegram Bot: @hashlane_bot
  
  CÁC TÍNH NĂNG TỰ ĐỘNG HÓA VƯỢT TRỘI:
    1. Chuẩn hóa mã băm thiết bị X-Device SHA-256 + X-Tz-Offset.
    2. Điểm danh tự động Daily Streak 7 ngày (/api/checkin).
    3. Tự động THU HOẠCH NHÂN ĐÔI ĐIỂM (Double Collect 2x) bằng xem QC (/api/mining/collect double=true)
       -> Thu hoạch gấp đôi số điểm (+200 điểm/ca thay vì 100 điểm thông thường).
    4. Tự động GIA HẠN CA ĐÀO (Mining Extend +30 phút) bằng xem QC (/api/mining/extend via=ad)
       -> Mở rộng thời lượng và kho chứa hoàn toàn miễn phí.
    5. Tự động CÀY GEMS MIỄN PHÍ mỗi ngày (/api/ads/begin purpose=gem -> 5 Gems/ngày).
    6. Cơ chế Anti-429 Cooldown: Tự động điều tiết next_ad_at và giãn cách giữa các ca quảng cáo.
    7. Tự động NÂNG CẤP MÁY ĐÀO (Upgrades) khi đủ điểm:
       - Cooling: Tăng thời gian đào mỗi phiên (+900s)
       - PSU: Tăng tốc độ thu hoạch điểm (+5%)
       - Battery: Tăng số lượt gia hạn bằng QC
    8. Tự động LÀM VÀ NHẬN THƯỞNG NHIỆM VỤ (Tasks):
       - Tự động join channel Telegram chính thức và nhận điểm thưởng.
    9. Tự động KÍCH HOẠT CA ĐÀO MỚI ngay sau khi thu hoạch.
   10. Cơ chế Handover Chaining 24/7 tự động chuyển giao ca tiếp theo trên GitHub Actions.
=============================================================================
"""

import os
import sys
import time
import json
import random
import re
import hashlib
import asyncio
import urllib.parse
import requests
from colorama import init, Fore, Style

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestWebViewRequest
from telethon.tl.functions.channels import JoinChannelRequest

from human_behavior import (
    get_device_profile,
    get_hashlane_device_fp,
    handle_sleep_schedule_async,
    check_sleep_window,
    SessionBurstManager,
    get_vn_time
)

init(autoreset=True)

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

API_BASE = "https://46-101-192-249.sslip.io/api"
SESSION_FILE_PATH = os.getenv("TELEGRAM_SESSION_PATH", "C:/Users/Administrator/Downloads/kiemtien_autoplay/telepet_acc1.session")

def log(tag, msg, color=Fore.WHITE):
    t_str = time.strftime('%H:%M:%S')
    print(f"{Fore.LIGHTBLACK_EX}[{t_str}]{Style.RESET_ALL} {color}[{tag:<14}]{Style.RESET_ALL} {msg}")

class HashLaneBot:
    def __init__(self, acc_id=1, string_session=None, session_path=None):
        self.acc_id = int(acc_id)
        self.string_session = string_session or STRING_SESSION
        self.session_path = session_path
        self.init_data = None
        self.user_id = None
        self.username = None
        self.points = 0
        self.gems = 0
        self.next_ad_at = 0
        
        dev = get_device_profile(self.acc_id)
        self.device_name = dev["device_name"]
        self.ua = dev["ua"]
        self.dev_fp = get_hashlane_device_fp(self.acc_id)

    async def fetch_tg_init_data(self):
        log("TELEGRAM", "Đang kết nối Telegram để lấy tgWebAppData HashLane...", Fore.CYAN)
        client = None
        try:
            if self.session_path and os.path.exists(self.session_path):
                client = TelegramClient(self.session_path, API_ID, API_HASH)
            else:
                client = TelegramClient(StringSession(self.string_session), API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                log("TELEGRAM", "❌ Phiên Telegram không được ủy quyền!", Fore.RED)
                await client.disconnect()
                return False, None

            bot_entity = await client.get_entity("hashlane_bot")
            res = await client(RequestWebViewRequest(
                peer=bot_entity,
                bot=bot_entity,
                url="https://46-101-192-249.sslip.io/app/",
                platform="android"
            ))

            frag = res.url.split("#tgWebAppData=")[1].split("&tgWebAppVersion")[0]
            self.init_data = urllib.parse.unquote(frag)
            params = dict(urllib.parse.parse_qsl(self.init_data))
            user_obj = json.loads(params.get("user", "{}"))
            self.user_id = str(user_obj.get("id"))
            self.username = user_obj.get("username", self.user_id)
            log("TELEGRAM", f"✅ Lấy init_data thành công cho @{self.username} (ID: {self.user_id})", Fore.GREEN)
            return True, client
        except Exception as e:
            log("TELEGRAM_ERR", f"Lỗi lấy WebApp Data: {e}", Fore.RED)
            if client and client.is_connected():
                await client.disconnect()
            return False, None

    def get_headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Init-Data": self.init_data,
            "X-Device": self.dev_fp,
            "X-Tz-Offset": "420",
            "User-Agent": self.ua,
            "Origin": "https://46-101-192-249.sslip.io",
            "Referer": "https://46-101-192-249.sslip.io/app/"
        }

    def get_state(self):
        try:
            r = requests.get(f"{API_BASE}/me", headers=self.get_headers(), timeout=12)
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    d = data.get("data", {})
                    u = d.get("user", {})
                    b = d.get("balances", {})
                    self.points = b.get("points", 0)
                    self.gems = b.get("gems", 0)
                    ads_info = d.get("ads", {})
                    self.next_ad_at = ads_info.get("next_ad_at", 0)
                    m = d.get("mining", {})
                    ses = m.get("session") or {}
                    earned = ses.get("earned", 0)
                    capacity = ses.get("capacity", 100)
                    is_ready = ses.get("ready", False)
                    log("STATE", f"👤 User: @{u.get('username')} | Điểm: {self.points} 🪙 | Gems: {self.gems} 💎 | Kho: {earned}/{capacity} (Sẵn sàng: {is_ready})", Fore.CYAN)
                    return d
            else:
                log("STATE_ERR", f"Lỗi lấy trạng thái HTTP {r.status_code}", Fore.RED)
        except Exception as e:
            log("STATE_ERR", f"Ngoại lệ get_state: {e}", Fore.RED)
        return None

    def checkin(self):
        try:
            r = requests.post(f"{API_BASE}/checkin", headers=self.get_headers(), json={}, timeout=10)
            if r.status_code == 200:
                d = r.json().get("data", {})
                pts = d.get("points", 0)
                gems = d.get("gems", 0)
                log("CHECKIN", f"🎉 Điểm danh thành công Ngày {d.get('day', 1)}: +{pts} Điểm, +{gems} Gems!", Fore.GREEN)
                self.points += pts
                self.gems += gems
            elif r.status_code == 409:
                log("CHECKIN", "ℹ️ Hôm nay đã điểm danh rồi.", Fore.LIGHTBLACK_EX)
        except Exception:
            pass

    def check_ad_cooldown(self, srv_time):
        """Tự động kiểm tra và chờ hồi chiêu giữa 2 lần xem quảng cáo chống 429"""
        if self.next_ad_at and self.next_ad_at > srv_time:
            cd = int((self.next_ad_at - srv_time) / 1000)
            if cd > 0:
                wait_time = min(cd + 2, 35)
                log("AD_COOLDOWN", f"⏳ Ca quảng cáo đang trong thời gian hồi chiêu (còn {cd}s). Đang chờ {wait_time}s...", Fore.YELLOW)
                time.sleep(wait_time)

    def watch_ad_for_token(self, purpose, session_id=0, srv_time=0):
        """
        Khởi tạo và hoàn tất chuỗi xem quảng cáo để lấy token xác nhận:
        - purpose: 'collect_2x' (nhân đôi thu hoạch), 'extend' (gia hạn mỏ), 'gem' (nhận gem)
        """
        self.check_ad_cooldown(srv_time or int(time.time() * 1000))

        payload = {"purpose": purpose}
        if session_id:
            payload["session_id"] = session_id

        try:
            r_ab = requests.post(f"{API_BASE}/ads/begin", headers=self.get_headers(), json=payload, timeout=12)
            if r_ab.status_code == 429:
                log("AD_COOLDOWN", "Gặp giới hạn tần suất quảng cáo (HTTP 429). Chờ 30s...", Fore.YELLOW)
                time.sleep(30)
                return None

            if r_ab.status_code != 200:
                log("AD_WARN", f"Chưa thể khởi tạo QC cho {purpose} (HTTP {r_ab.status_code})", Fore.YELLOW)
                return None
            
            d = r_ab.json().get("data", {})
            token = d.get("token")
            networks = d.get("networks", [])
            if not token:
                log("AD_WARN", f"Không nhận được token QC cho {purpose}", Fore.YELLOW)
                return None

            log("AD_START", f"🎬 Bắt đầu xem QC ({purpose})... Đang chờ đủ 18s theo chuẩn chống gian lận máy chủ...", Fore.YELLOW)
            
            # Ping Adsgram thật nếu mạng trả về là adsgram
            net_code = "adsgram"
            if networks and isinstance(networks, list):
                first_net = networks[0]
                net_code = first_net.get("code", "adsgram")
                if net_code == "adsgram":
                    block_id = first_net.get("config", {}).get("block_id", "54722")
                    try:
                        ad_headers = {
                            'User-Agent': self.ua,
                            'Origin': 'https://46-101-192-249.sslip.io',
                            'Referer': 'https://46-101-192-249.sslip.io/app/',
                            'Accept': 'application/json',
                            'X-Requested-With': 'org.telegram.messenger'
                        }
                        adv_params = {
                            'blockId': str(block_id),
                            'tg_id': str(self.user_id),
                            'tg_platform': 'android',
                            'platform': 'Linux armv8l',
                            'language': 'vi',
                            'top_domain': 'sslip.io'
                        }
                        r_adv = requests.get('https://api.adsgram.ai/adv', headers=ad_headers, params=adv_params, timeout=8)
                        if r_adv.status_code == 200:
                            for ev in re.findall(r'https://api\.adsgram\.ai/event\?[^\s\'"]+', r_adv.text):
                                if 'type=render' in ev or 'type=show' in ev:
                                    requests.get(ev, headers=ad_headers, timeout=5)
                    except Exception:
                        pass

            # Chờ đủ 18 giây để vượt qua kiểm tra 'ad_too_fast' của server Hashlane
            time.sleep(18)

            # Gửi xác nhận hoàn tất quảng cáo
            complete_payload = {
                "token": token,
                "network": net_code,
                "attempts": [{"code": net_code, "result": "shown"}]
            }
            for attempt in range(5):
                r_comp = requests.post(f"{API_BASE}/ads/complete", headers=self.get_headers(), json=complete_payload, timeout=12)
                if r_comp.status_code == 200 and r_comp.json().get("ok"):
                    res_data = r_comp.json().get("data", {})
                    ads_meta = res_data.get("ads", {})
                    self.next_ad_at = ads_meta.get("next_ad_at", 0)
                    log("AD_SUCCESS", f"✓ Đã xem thành công QC ({purpose})! Nhận token xác thực.", Fore.GREEN)
                    return token
                elif r_comp.status_code == 409:
                    err_code = r_comp.json().get("error", {}).get("code", "")
                    if err_code == "ad_too_fast":
                        time.sleep(3)
                        continue
                    elif err_code == "ad_used":
                        return token
                time.sleep(2)
        except Exception as e:
            log("AD_ERR", f"Lỗi trong quy trình xem QC {purpose}: {e}", Fore.RED)
        return None

    def manage_mining(self, state_data):
        """Quản lý mỏ đào: Thu hoạch nhân đôi (2x), gia hạn mỏ, hoặc khởi động phiên mới"""
        m = state_data.get("mining", {}) if state_data else {}
        ses = m.get("session")
        srv_time = state_data.get("server_time", int(time.time() * 1000))

        if not ses:
            log("MINING", "▶️ Chưa có phiên đào, tiến hành khởi động máy đào...", Fore.YELLOW)
            try:
                r = requests.post(f"{API_BASE}/mining/start", headers=self.get_headers(), json={}, timeout=10)
                if r.status_code == 200:
                    log("MINING", "✅ Đã bắt đầu ca đào mới 3600s (100 điểm/giờ)!", Fore.GREEN)
            except Exception as e:
                log("MINING_ERR", f"Lỗi start mining: {e}", Fore.RED)
            return False

        is_ready = ses.get("ready", False)
        earned = ses.get("earned", 0)
        capacity = ses.get("capacity", 100)
        ses_id = ses.get("id")
        ads_info = state_data.get("ads", {})
        can_watch_ad = ads_info.get("rewarded_today", 0) < ads_info.get("rewarded_per_day", 40)

        # 1. Thu hoạch mỏ đào khi đầy hoặc sẵn sàng (Ưu tiên cày QC nhân đôi điểm 2x)
        if is_ready or earned >= capacity:
            log("COLLECT", f"⛏️ Kho đào đã đầy ({earned}/{capacity} điểm)! Chuẩn bị thu hoạch...", Fore.YELLOW)
            double = False
            token = ""
            if can_watch_ad:
                log("COLLECT_2X", "🚀 Kích hoạt cày QC để NHÂN ĐÔI ĐIỂM (Double Collect 2x)...", Fore.MAGENTA)
                ad_token = self.watch_ad_for_token("collect_2x", session_id=ses_id, srv_time=srv_time)
                if ad_token:
                    double = True
                    token = ad_token
            
            try:
                col_payload = {"double": double}
                if token:
                    col_payload["token"] = token
                r_c = requests.post(f"{API_BASE}/mining/collect", headers=self.get_headers(), json=col_payload, timeout=12)
                if r_c.status_code == 200:
                    cd = r_c.json().get("data", {})
                    pts_got = cd.get("points", earned * (2 if double else 1))
                    self.points = cd.get("balance", self.points + pts_got)
                    log("COLLECT_SUCCESS", f"🎉🎉🎉 THU HOẠCH THÀNH CÔNG {'[NHÂN ĐÔI 2X]' if double else ''} +{pts_got} ĐIỂM! Số dư mới: {self.points} điểm.", Fore.GREEN)
                    
                    # Tự động bắt đầu ca mới
                    time.sleep(2)
                    r_new = requests.post(f"{API_BASE}/mining/start", headers=self.get_headers(), json={}, timeout=10)
                    if r_new.status_code == 200:
                        log("MINING", "✅ Đã tự động kích hoạt ca đào mới 3600s!", Fore.GREEN)
                else:
                    log("COLLECT_ERR", f"Lỗi thu hoạch: {r_c.text[:100]}", Fore.YELLOW)
            except Exception as e:
                log("COLLECT_ERR", f"Lỗi collect: {e}", Fore.RED)
            return True

        # 2. Gia hạn ca đào (+30 phút) bằng QC nếu chưa gia hạn
        p = m.get("params", {})
        ad_ext_done = ses.get("ad_extends", 0)
        max_ad_ext = p.get("ad_extends", 1)
        if ad_ext_done < max_ad_ext and can_watch_ad:
            log("EXTEND", f"⏳ Phiên đào đang chạy ({earned}/{capacity} điểm). Tự động cày QC gia hạn thêm {p.get('extend_seconds', 1800)//60} phút...", Fore.CYAN)
            ext_token = self.watch_ad_for_token("extend", session_id=ses_id, srv_time=srv_time)
            if ext_token:
                try:
                    r_ext = requests.post(f"{API_BASE}/mining/extend", headers=self.get_headers(), json={"via": "ad", "token": ext_token}, timeout=10)
                    if r_ext.status_code == 200:
                        log("EXTEND_SUCCESS", "✅ Gia hạn mỏ đào thành công! Kho chứa và thời gian đào đã được mở rộng.", Fore.GREEN)
                        return True
                except Exception as e:
                    log("EXTEND_ERR", f"Lỗi extend: {e}", Fore.RED)
        else:
            log("MINING", f"⏳ Máy đào đang hoạt động: {earned}/{capacity} điểm. Vòng đào tiếp theo sẽ đầy sau.", Fore.CYAN)
        return False

    def claim_daily_gems(self, state_data):
        """Cày Gems miễn phí mỗi ngày (tối đa 5 Gems/ngày)"""
        ads_info = state_data.get("ads", {})
        gems_today = ads_info.get("gems_today", 0)
        gems_max = ads_info.get("gems_per_day", 5)
        srv_time = state_data.get("server_time", int(time.time() * 1000))

        if gems_today < gems_max:
            log("GEM_AD", f"💎 Tiến độ Gems hôm nay: {gems_today}/{gems_max}. Bắt đầu cày QC nhận +1 Gem...", Fore.MAGENTA)
            tok = self.watch_ad_for_token("gem", srv_time=srv_time)
            if tok:
                self.gems += 1
                log("GEM_SUCCESS", f"🎉 ĐÃ NHẬN THÊM +1 GEM MIỄN PHÍ! Tổng Gems: {self.gems}", Fore.GREEN)
                return True
        else:
            log("GEM_INFO", f"💎 Hôm nay đã cày đủ tối đa {gems_today}/{gems_max} Gems!", Fore.GREEN)
        return False

    def auto_upgrades(self, state_data):
        """Tự động nâng cấp giàn máy đào khi tích lũy đủ điểm"""
        upgrades = state_data.get("upgrades", [])
        if not upgrades:
            return

        order = {"cooling": 1, "psu": 2, "battery": 3}
        upgrades_sorted = sorted(upgrades, key=lambda x: order.get(x.get("code"), 99))

        for u in upgrades_sorted:
            code = u.get("code")
            lv = u.get("level", 0)
            max_lv = u.get("max", 3)
            next_cost = u.get("next_cost", 999999)

            if lv < max_lv and self.points >= next_cost:
                log("UPGRADE", f"⚡ Đủ điều kiện nâng cấp {code.upper()} lên Cấp {lv + 1} (Chi phí: {next_cost} điểm)...", Fore.YELLOW)
                try:
                    r = requests.post(f"{API_BASE}/upgrades/buy", headers=self.get_headers(), json={"code": code}, timeout=10)
                    if r.status_code == 200:
                        d = r.json()
                        if d.get("ok"):
                            self.points -= next_cost
                            log("UPGRADE_SUCCESS", f"🎉 NÂNG CẤP THÀNH CÔNG {code.upper()} LÊN CẤP {lv + 1}! Số dư điểm còn lại: {self.points}", Fore.GREEN)
                except Exception as e:
                    log("UPGRADE_ERR", f"Lỗi nâng cấp {code}: {e}", Fore.RED)

    async def process_tasks(self, client=None):
        """Tự động kiểm tra và hoàn thành các nhiệm vụ Tasks"""
        try:
            r = requests.get(f"{API_BASE}/tasks?tg_platform=android", headers=self.get_headers(), timeout=10)
            if r.status_code != 200:
                return
            tasks = r.json().get("data", {}).get("tasks", [])
            for t in tasks:
                t_id = t.get("id")
                state = t.get("state", "new")
                title = t.get("title", "")
                t_type = t.get("type", "")
                pts = t.get("reward_points", 0)
                gems = t.get("reward_gems", 0)

                if state in ["new", "started"]:
                    log("TASK", f"📋 Phát hiện nhiệm vụ: '{title}' (+{pts} Điểm, +{gems} Gems)...", Fore.CYAN)
                    if t_type == "join_channel" and client:
                        url = t.get("url", "")
                        channel_name = url.split("/")[-1]
                        try:
                            ch_entity = await client.get_entity(channel_name)
                            await client(JoinChannelRequest(ch_entity))
                            log("TASK", f"✅ Đã tự động join channel Telegram @{channel_name}", Fore.GREEN)
                        except Exception as e:
                            log("TASK_WARN", f"Không thể tự động join {channel_name}: {e}", Fore.YELLOW)
                    
                    if state == "new":
                        requests.post(f"{API_BASE}/tasks/start", headers=self.get_headers(), json={"id": t_id}, timeout=10)
                        await asyncio.sleep(t.get("min_seconds", 10) + 1)

                    r_chk = requests.post(f"{API_BASE}/tasks/check", headers=self.get_headers(), json={"id": t_id}, timeout=10)
                    if r_chk.status_code == 200 and r_chk.json().get("ok"):
                        log("TASK_SUCCESS", f"🎉 HOÀN THÀNH NHIỆM VỤ '{title}'! +{pts} Điểm, +{gems} Gems", Fore.GREEN)
                        self.points += pts
                        self.gems += gems
        except Exception as e:
            log("TASK_ERR", f"Lỗi xử lý Tasks: {e}", Fore.RED)

    async def run_cycle(self):
        ok, client = await self.fetch_tg_init_data()
        if not ok:
            return
        
        try:
            state = self.get_state()
            if not state:
                return

            # 1. Điểm danh nhận thưởng Daily Streak
            self.checkin()

            # 2. Xử lý nhiệm vụ kiếm thêm điểm & Gems
            await self.process_tasks(client)

            # 3. Thu hoạch & Khởi động mỏ đào (Ưu tiên cày QC nhân đôi điểm 2x hoặc gia hạn mỏ)
            ad_performed = self.manage_mining(state)

            # 4. Nếu chưa xem QC trong lượt này, tranh thủ cày Gems miễn phí (tối đa 5 Gems/ngày)
            if not ad_performed:
                self.claim_daily_gems(state)

            # 5. Tự động nâng cấp giàn máy khi đủ điểm
            self.auto_upgrades(state)
        finally:
            if client and client.is_connected():
                await client.disconnect()


def trigger_next_shift(workflow_file="game2_hashlane.yml"):
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

async def run_loop_247(bot_instance, interval_mins=15):
    raw_rt = os.getenv("MAX_RUNTIME_SECONDS", "17500").strip()
    max_runtime = int(raw_rt) if raw_rt.isdigit() else 17500
    start_time = time.time()
    cycle = 1
    
    log("HUMAN_ENGINE", f"🔥 BẬT CHẾ ĐỘ NGƯỜI THẬT: Phiên chơi 20-30p | Nghỉ 5-8p | Giờ ngủ VN 00:30-05:15!", Fore.GREEN)
    burst_mgr = SessionBurstManager(burst_min_mins=20, burst_max_mins=30, break_min_mins=5, break_max_mins=8)
    
    while True:
        # 1. Kiểm tra Giờ ngủ tự nhiên (00:30 - 05:15 VN)
        slept = await handle_sleep_schedule_async(log_func=lambda msg: log("SLEEP", msg, Fore.MAGENTA))
        if slept:
            burst_mgr.start_new_burst()

        elapsed = time.time() - start_time
        if elapsed >= max_runtime:
            log("HANDOVER", f"⏰ Hoàn thành ca trực ({elapsed/3600:.1f}h). Tự động chuyển giao ca tiếp theo...", Fore.CYAN)
            wf_target = f"game2_hashlane_acc{bot_instance.acc_id}.yml" if bot_instance.acc_id > 1 else "game2_hashlane.yml"
            trigger_next_shift(wf_target)
            break

        # 2. Hết phiên chơi -> Nghỉ giải lao tự nhiên (Human Break)
        if burst_mgr.is_burst_finished():
            break_sec = burst_mgr.get_break_duration()
            log("HUMAN_BREAK", f"☕ [PHIÊN #{burst_mgr.burst_count} XONG] Đóng app, nghỉ ngơi tự nhiên {break_sec//60} phút...", Fore.CYAN)
            
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

        # 3. Trong phiên chơi
        log("LOOP", f"🌀 === BẮT ĐẦU LƯỢT #{cycle} ({bot_instance.device_name}) ===", Fore.MAGENTA)
        try:
            await bot_instance.run_cycle()
        except Exception as e:
            log("CYCLE_ERR", f"Lỗi chu kỳ #{cycle}: {e}", Fore.RED)
        
        cycle += 1
        sub_wait = random.randint(480, 720)
        log("LOOP", f"⏳ Giãn cách {sub_wait//60} phút trước lượt tiếp theo trong phiên...", Fore.YELLOW)
        await asyncio.sleep(sub_wait)

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bot Auto HashLane ($TON) 24/7 PRO")
    parser.add_argument("--acc", type=int, default=1, choices=[1, 2, 3], help="Tài khoản Telegram (1, 2 hoặc 3)")
    parser.add_argument("--loop", type=int, default=0, help="Số phút lặp lại (0 để chạy 1 lần)")
    args, _ = parser.parse_known_args()

    session_map = {1: DEFAULT_SESSION_ACC1, 2: DEFAULT_SESSION_ACC2, 3: DEFAULT_SESSION_ACC3}
    session_str = os.getenv(f"TELEGRAM_STRING_SESSION_ACC{args.acc}") or os.getenv("TELEGRAM_STRING_SESSION") or session_map.get(args.acc, DEFAULT_SESSION_ACC1)
    
    session_file = f"C:/Users/Administrator/Downloads/kiemtien_autoplay/telepet_acc{args.acc}.session"
    if not os.path.exists(session_file):
        session_file = None

    print(Fore.YELLOW + f"""
=============================================================================
  BOT AUTO HASHLANE ($TON) 24/7 PRO - CHUẨN X-DEVICE FINGERPRINT & MOONPOOL
  Acc: {args.acc} | Tự động Thu Hoạch Nhân Đôi (2X) | Cày Gems Miễn Phí | Gia Hạn Mỏ
=============================================================================
    """ + Style.RESET_ALL)
    bot = HashLaneBot(acc_id=args.acc, string_session=session_str, session_path=session_file)
    if args.loop > 0:
        await run_loop_247(bot, interval_mins=args.loop)
    else:
        await bot.run_cycle()

if __name__ == "__main__":
    asyncio.run(main())
