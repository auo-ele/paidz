#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  BOT AUTO PAIDZ ($USDT) 24/7 - CHẾ ĐỘ TÀNG HÌNH ANTI-DETECTION STEALTH
  Platform: PaidZ Mini App (https://paidz.biz/)
  Telegram Bot: @paidzapp (Short name: 'start')
  Account: Acc 4 - Wind_trader (UID: 8735204819)
  
  TÍNH NĂNG TÀNG HÌNH ĐỘT PHÁ:
    1. Giả lập chữ ký thiết bị Android 14 (Samsung S24 Ultra, GPU Adreno 750).
    2. Giao thức nhị phân Protobuf chuẩn 100% khớp webapp.
    3. Tự động quét và triệt tiêu 100% các bẫy Honeypot ngầm.
    4. Mô phỏng tọa độ chạm ngón tay thật (relX, relY) & pointerType: touch.
    5. Xem quảng cáo với thời gian xem ngẫu nhiên tự nhiên (Anti-timing).
    6. Cơ chế nghỉ mệt tự nhiên (Anti-Fatigue) 2 - 3 phút sau mỗi đợt xem.
    7. Tự động nhận thưởng nhiệm vụ hệ thống (/tasks).
    8. Chuyển giao ca trực 24/7 tự động (Handover sau 4.8h).
=============================================================================
"""

import os
import sys
import time
import json
import uuid
import struct
import random
import asyncio
import urllib.parse
import requests
from datetime import datetime
from colorama import Fore, Style, init

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestAppWebViewRequest
from telethon.tl.types import InputBotAppShortName

init(autoreset=True)

# -----------------------------------------------------------------
# CẤU HÌNH TÀI KHOẢN ACC 4 (Wind_trader)
# -----------------------------------------------------------------
API_ID = int(os.getenv("TELEGRAM_API_ID", 34333329))
API_HASH = os.getenv("TELEGRAM_API_HASH", "4f9371f95000578c84dbc670aaf1f819")
STRING_SESSION = os.getenv("TELEGRAM_STRING_SESSION") or (
    "1BVtsOIIBuzNuH5Jfb4Uwek2dG7YRqSyFk-74KTokth0VB3_UTMwM8Edh_ikn83fJOGyN7JaWzIZXnro3ico"
    "Y8zsjYIlT5nQ4z_GgKknABQ74FRseCvNbz3yyTkPOfQ4xJfZnJIJHuY4EkzVOzQzYZFg_EJWOj_vvg6OVwSk"
    "Qv9Nd52tl_SlH4TofoxDXDNvxLJyFcoQFH6BegTybx-pFyX2tz0rMeR7AQujnGxqdWOd4zywoFVShzsCTFeq"
    "dsBP9itJvg1YB0ISmJEYXzGEQo37IddAFGw3PJcAIY4BBctxri9_Cw-FbxhMgLU9gsotA3Rrys2jLcGV4CGf"
    "Op_IzD0CmtNm845I="
)

API_BASE = "https://api.paidz.biz"
REPO_NAME = os.getenv("GITHUB_REPOSITORY") or "auo-ele/paidz"
WORKFLOW_FILE = os.getenv("WORKFLOW_FILE", "paidz_acc4.yml")
MAX_RUNTIME_SECONDS = int(os.getenv("MAX_RUNTIME_SECONDS", "17500"))

# -----------------------------------------------------------------
# PROTOBUF ENCODER & DECODER
# -----------------------------------------------------------------
def encode_varint(val):
    if val == 0:
        return b'\x00'
    res = bytearray()
    while val > 0x7F:
        res.append((val & 0x7F) | 0x80)
        val >>= 7
    res.append(val & 0x7F)
    return bytes(res)

def decode_varint(data, pos=0):
    val = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return val, pos

def enc_string(field_num, s):
    if not s:
        return b''
    raw = s.encode('utf-8')
    tag = encode_varint((field_num << 3) | 2)
    return tag + encode_varint(len(raw)) + raw

def enc_bytes(field_num, b):
    if not b:
        return b''
    tag = encode_varint((field_num << 3) | 2)
    return tag + encode_varint(len(b)) + b

def enc_int32(field_num, v):
    if not v:
        return b''
    tag = encode_varint((field_num << 3) | 0)
    return tag + encode_varint(v)

def enc_bool(field_num, b):
    if not b:
        return b''
    tag = encode_varint((field_num << 3) | 0)
    return tag + b'\x01'

def enc_double(field_num, d):
    if d == 0:
        return b''
    tag = encode_varint((field_num << 3) | 1)
    return tag + struct.pack('<d', float(d))

def decode_proto(data):
    pos = 0
    fields = {}
    while pos < len(data):
        tag, pos = decode_varint(data, pos)
        field_num = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 0:
            val, pos = decode_varint(data, pos)
            fields[field_num] = val
        elif wire_type == 1:
            val = struct.unpack('<d', data[pos:pos+8])[0]
            pos += 8
            fields[field_num] = val
        elif wire_type == 2:
            length, pos = decode_varint(data, pos)
            val = data[pos:pos+length]
            pos += length
            if field_num in fields:
                if not isinstance(fields[field_num], list):
                    fields[field_num] = [fields[field_num]]
                fields[field_num].append(val)
            else:
                fields[field_num] = val
        elif wire_type == 5:
            val = struct.unpack('<f', data[pos:pos+4])[0]
            pos += 4
            fields[field_num] = val
        else:
            break
    return fields

def log(tag, msg, color=Fore.WHITE):
    t_str = time.strftime('%H:%M:%S')
    print(f"{Fore.LIGHTBLACK_EX}[{t_str}]{Style.RESET_ALL} {color}[{tag:10s}]{Style.RESET_ALL} {msg}", flush=True)

# -----------------------------------------------------------------
# CORE BOT CLIENT
# -----------------------------------------------------------------
class PaidZClient:
    def __init__(self):
        self.token = None
        self.balance = 0.0
        self.ads_watched = 0
        self.username = "Wind_trader"
        self.user_agent = (
            "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.135 "
            "Mobile Safari/537.36 Telegram-Android/11.5.0 (Samsung SM-S928B; Android 14; SDK 34; AVERAGE)"
        )

    async def fetch_tg_init_data(self):
        log("TELETHON", "Đang kết nối Telegram lấy tgWebAppData mới...", Fore.CYAN)
        try:
            client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
            await client.connect()
            bot = await client.get_input_entity("paidzapp")
            bot_app = InputBotAppShortName(bot_id=bot, short_name="start")
            res = await client(RequestAppWebViewRequest(peer=bot, app=bot_app, platform="android"))
            await client.disconnect()

            frag = urllib.parse.urlparse(res.url).fragment
            params = urllib.parse.parse_qs(frag)
            init_data = params.get("tgWebAppData", [None])[0]
            if init_data:
                log("TELETHON", f"✅ Lấy tgWebAppData thành công ({len(init_data)} ký tự)!", Fore.GREEN)
                return init_data
        except Exception as e:
            log("TELETHON_ERR", f"Lỗi Telethon: {e}", Fore.RED)
        return None

    def authenticate(self, init_data):
        log("AUTH", "Đang xác thực Protobuf với máy chủ PaidZ (Stealth Android Mode)...", Fore.YELLOW)
        visitor_id = uuid.uuid4().hex
        telemetry_bytes = b"".join([
            enc_string(1, visitor_id),
            enc_string(2, "android"),
            enc_string(3, "1080x2400"),
            enc_string(4, self.user_agent),
            enc_string(5, "vi-VN"),
            enc_string(6, "Asia/Ho_Chi_Minh"),
            enc_string(7, "Qualcomm"),
            enc_string(8, "Adreno (TM) 750"),
            enc_int32(9, 8),
            enc_double(10, 8.0),
            enc_bool(11, False),
            enc_string(12, '"Android"'),
            enc_string(13, '?1'),
            enc_int32(14, 0),
            enc_string(15, "touch"),
            enc_int32(16, 5),
            enc_bool(17, True)
        ])

        req_body = b"".join([
            enc_string(1, init_data),
            enc_string(2, ""),
            enc_bytes(3, telemetry_bytes)
        ])

        headers = {
            'Content-Type': 'application/x-protobuf',
            'Accept': 'application/x-protobuf, application/json',
            'User-Agent': self.user_agent,
            'Origin': 'https://paidz.biz',
            'Referer': 'https://paidz.biz/'
        }

        try:
            r = requests.post(f"{API_BASE}/auth/telegram", data=req_body, headers=headers, timeout=15)
            if r.status_code == 200:
                fields = decode_proto(r.content)
                raw_token = fields.get(1)
                self.token = raw_token.decode('utf-8', errors='ignore') if isinstance(raw_token, bytes) else raw_token
                
                if 2 in fields and isinstance(fields[2], bytes):
                    u = decode_proto(fields[2])
                    raw_un = u.get(3, b'')
                    self.username = raw_un.decode('utf-8', errors='ignore') if isinstance(raw_un, bytes) else str(raw_un)
                    self.balance = float(u.get(11, 0.0))
                    self.ads_watched = int(u.get(12, 0))
                    is_banned = u.get(18, 0)
                    if is_banned:
                        log("AUTH_BAN", "❌ Tài khoản đã bị máy chủ đánh dấu cấm!", Fore.RED)
                        return False

                log("AUTH", f"✅ Đăng nhập thành công! User: @{self.username} | Số dư: {self.balance:.4f} USDT | Đã xem: {self.ads_watched} ads", Fore.GREEN)
                return True
            else:
                log("AUTH_ERR", f"Lỗi xác thực: {r.status_code} - {r.text[:150]}", Fore.RED)
        except Exception as e:
            log("AUTH_ERR", f"Ngoại lệ khi xác thực: {e}", Fore.RED)
        return False

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/x-protobuf',
            'Accept': 'application/x-protobuf, application/json',
            'User-Agent': self.user_agent,
            'Origin': 'https://paidz.biz',
            'Referer': 'https://paidz.biz/'
        }

    def fetch_clean_networks(self):
        try:
            r = requests.get(f"{API_BASE}/ads/networks", headers=self.get_headers(), timeout=10)
            if r.status_code == 200:
                data = decode_proto(r.content)
                # Field 1 is repeated AdNetwork
                raw_nets = data.get(1, [])
                if not isinstance(raw_nets, list):
                    raw_nets = [raw_nets]
                
                clean_networks = []
                for item in raw_nets:
                    if isinstance(item, bytes):
                        net_fields = decode_proto(item)
                        raw_id = net_fields.get(1, b'')
                        raw_name = net_fields.get(2, b'')
                        net_id = raw_id.decode('utf-8', errors='ignore') if isinstance(raw_id, bytes) else str(raw_id)
                        net_name = raw_name.decode('utf-8', errors='ignore') if isinstance(raw_name, bytes) else str(raw_name)
                        reward = float(net_fields.get(5, 0.0))
                        daily_limit = int(net_fields.get(6, 0))
                        watched_today = int(net_fields.get(8, 0))
                        remaining = int(net_fields.get(9, 0))
                        is_honeypot = bool(net_fields.get(11, False))

                        # BỘ LỌC HONEYPOT CHỐNG BAN TUYỆT ĐỐI
                        if is_honeypot or "honeypot" in net_name.lower() or net_name.startswith("secret_"):
                            log("HONEYPOT", f"🛡️ Đã phát hiện và né bẫy Honeypot: '{net_name}'!", Fore.MAGENTA)
                            continue

                        if remaining > 0 or (daily_limit > 0 and watched_today < daily_limit):
                            clean_networks.append({
                                "id": net_id,
                                "name": net_name,
                                "reward": reward,
                                "remaining": remaining or (daily_limit - watched_today)
                            })
                return clean_networks
        except Exception as e:
            log("NETWORKS_ERR", f"Lỗi lấy danh sách ads: {e}", Fore.RED)
        return []

    def watch_ad_stealth(self, network_name):
        # 1. Tọa độ chạm ngón tay người thật ngẫu nhiên
        rel_x = round(random.uniform(0.35, 0.68), 4)
        rel_y = round(random.uniform(0.42, 0.62), 4)

        req_start = b"".join([
            enc_string(1, network_name),
            enc_string(2, "touch"),
            enc_bool(3, True),
            enc_double(4, rel_x),
            enc_double(5, rel_y),
            enc_string(6, "")
        ])

        try:
            r_start = requests.post(f"{API_BASE}/ads/start", data=req_start, headers=self.get_headers(), timeout=12)
            if r_start.status_code != 200:
                err_data = decode_proto(r_start.content)
                err_code = err_data.get(5, b'')
                err_msg = err_data.get(6, b'')
                log("AD_START_WARN", f"Không thể bắt đầu ca xem ({network_name}): {err_code} - {err_msg}", Fore.YELLOW)
                return False, 10

            start_fields = decode_proto(r_start.content)
            session_token_raw = start_fields.get(2, b'')
            session_token = session_token_raw.decode('utf-8', errors='ignore') if isinstance(session_token_raw, bytes) else str(session_token_raw)
            min_duration = int(start_fields.get(4, 15))

            if not session_token:
                return False, 5

            # 2. Xem quảng cáo tự nhiên (thời gian tối thiểu + thời gian ngẫu nhiên 2.5s - 5.5s)
            view_seconds = min_duration + round(random.uniform(2.5, 5.5), 2)
            log("WATCHING", f"🎬 Đang xem quảng cáo '{network_name}'... (thời lượng tự nhiên {view_seconds:.1f}s)", Fore.CYAN)
            time.sleep(view_seconds)

            # 3. Gửi gói tin hoàn tất xem quảng cáo
            duration_ms = view_seconds * 1000.0
            req_watch = b"".join([
                enc_string(1, network_name),
                enc_string(2, session_token),
                enc_double(3, duration_ms),
                enc_string(4, "")
            ])

            r_watch = requests.post(f"{API_BASE}/ads/watch", data=req_watch, headers=self.get_headers(), timeout=12)
            if r_watch.status_code == 200:
                w_fields = decode_proto(r_watch.content)
                reward = float(w_fields.get(2, 0.0))
                self.balance = float(w_fields.get(3, self.balance + reward))
                self.ads_watched = int(w_fields.get(4, self.ads_watched + 1))
                log("REWARD", f"🎉 Nhận thành công +{reward:.4f} USDT | Số dư mới: {self.balance:.4f} USDT | Tổng đã xem: {self.ads_watched}", Fore.GREEN)
                return True, 5
            else:
                log("WATCH_ERR", f"Lỗi xác nhận thưởng: {r_watch.status_code}", Fore.YELLOW)
        except Exception as e:
            log("WATCH_EXC", f"Ngoại lệ khi xem ad: {e}", Fore.RED)
        return False, 10

    def claim_available_tasks(self):
        try:
            r = requests.get(f"{API_BASE}/tasks", headers=self.get_headers(), timeout=10)
            if r.status_code == 200:
                data = decode_proto(r.content)
                tasks = data.get(1, [])
                if not isinstance(tasks, list):
                    tasks = [tasks]
                for t in tasks:
                    if isinstance(t, bytes):
                        tf = decode_proto(t)
                        tid = tf.get(1, b'')
                        tid_str = tid.decode('utf-8', errors='ignore') if isinstance(tid, bytes) else str(tid)
                        is_completed = tf.get(11, 0)
                        if not is_completed:
                            # Try claim
                            req_c = enc_string(1, tid_str)
                            r_c = requests.post(f"{API_BASE}/tasks/{tid_str}/claim", data=req_c, headers=self.get_headers(), timeout=10)
                            if r_c.status_code == 200:
                                log("TASK", f"✅ Hoàn thành nhận thưởng nhiệm vụ: {tid_str}", Fore.GREEN)
        except Exception:
            pass

def trigger_next_shift():
    log("HANDOVER", f"🔄 Chuẩn bị chuyển giao ca làm việc tiếp theo trên {REPO_NAME}...", Fore.CYAN)
    pat = os.getenv("GH_PAT") or ("ghp_" + "4uoxqr79k4DnDki4jYmjIORTKybfeX1XnPbn")
    url = f"https://api.github.com/repos/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        r = requests.post(url, headers=headers, json={"ref": "main"}, timeout=15)
        if r.status_code == 204:
            log("HANDOVER", f"✅ Đã kích hoạt ca chạy tiếp theo trên {REPO_NAME} ({WORKFLOW_FILE})!", Fore.GREEN)
            return True
        else:
            log("HANDOVER", f"⚠️ Phản hồi dispatch: {r.status_code} {r.text}", Fore.YELLOW)
    except Exception as e:
        log("HANDOVER", f"Lỗi retrigger: {e}", Fore.RED)
    return False

# -----------------------------------------------------------------
# VÒNG LẶP CHÍNH 24/7 VỚI CƠ CHẾ NGHỈ MỆT TỰ NHIÊN (ANTI-FATIGUE)
# -----------------------------------------------------------------
async def main_loop():
    print(Fore.YELLOW + """
=============================================================================
  BOT AUTO PAIDZ ($USDT) 24/7 - CHẾ ĐỘ TÀNG HÌNH ANTI-DETECTION STEALTH
  Chạy an toàn độc quyền cho Acc 4 (Wind_trader)
=============================================================================
    """ + Style.RESET_ALL)

    bot = PaidZClient()
    init_data = await bot.fetch_tg_init_data()
    if not init_data:
        log("MAIN", "Không thể lấy tgWebAppData. Dừng chương trình.", Fore.RED)
        return

    if not bot.authenticate(init_data):
        log("MAIN", "Đăng nhập thất bại.", Fore.RED)
        return

    # Claim tasks đầu phiên
    bot.claim_available_tasks()

    start_time = time.time()
    last_refresh_time = time.time()
    ads_session_count = 0

    while True:
        try:
            # Kiểm tra thời lượng phiên 4.8 tiếng
            if (time.time() - start_time) >= MAX_RUNTIME_SECONDS:
                log("HANDOVER", "Hoàn thành ca trực 4.8 tiếng. Tự động chuyển giao ca trực tiếp theo...", Fore.CYAN)
                trigger_next_shift()
                break

            # Làm mới init_data sau mỗi 30 phút
            if (time.time() - last_refresh_time) >= 1800:
                new_init = await bot.fetch_tg_init_data()
                if new_init:
                    bot.authenticate(new_init)
                    last_refresh_time = time.time()

            # Lấy danh sách quảng cáo an toàn (đã lọc sạch Honeypot)
            networks = bot.fetch_clean_networks()
            if not networks:
                # Ưu tiên các mạng chuẩn nếu API trả danh sách trống
                networks = [
                    {"id": "net_adsgram", "name": "adsgram", "reward": 0.0006},
                    {"id": "net_gigapub", "name": "gigapub", "reward": 0.0002},
                    {"id": "net_tads", "name": "tads", "reward": 0.0002},
                    {"id": "net_telega", "name": "telega", "reward": 0.0006},
                    {"id": "net_richads", "name": "richads", "reward": 0.0002}
                ]

            # Chọn ngẫu nhiên 1 mạng quảng cáo
            target_net = random.choice(networks)
            net_name = target_net["name"]

            success, cooldown = bot.watch_ad_stealth(net_name)
            if success:
                ads_session_count += 1

            # NGHỈ MỆT TỰ NHIÊN (ANTI-FATIGUE CHECK):
            # Cứ xem 3 đến 5 quảng cáo liên tiếp -> Người thật sẽ mỏi mắt, dừng lại nghỉ 2 - 3 phút
            if ads_session_count >= random.randint(3, 5):
                rest_minutes = round(random.uniform(2.0, 3.0), 1)
                log("REST", f"☕ Mô phỏng người dùng nghỉ mệt tự nhiên {rest_minutes} phút (Anti-Fatigue)...", Fore.MAGENTA)
                time.sleep(rest_minutes * 60)
                ads_session_count = 0
            else:
                # Giãn cách giữa 2 lần xem liên tiếp (8 - 18 giây)
                gap_sleep = round(random.uniform(8.0, 18.0), 1)
                log("GAP", f"⏳ Giãn cách tự nhiên {gap_sleep}s trước lượt xem kế tiếp...", Fore.BLUE)
                time.sleep(gap_sleep)

        except KeyboardInterrupt:
            log("MAIN", "Người dùng dừng chương trình.", Fore.YELLOW)
            break
        except Exception as e:
            log("LOOP_ERR", f"Lỗi vòng lặp: {e}", Fore.RED)
            time.sleep(15)

if __name__ == '__main__':
    asyncio.run(main_loop())
