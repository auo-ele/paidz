#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  BOT AUTO PAIDZ ($USDT) 24/7 - CHẾ ĐỘ TÀNG HÌNH ANTI-DETECTION STEALTH
  Platform: PaidZ Mini App (https://paidz.biz/)
  Telegram Bot: @paidzapp (Short name: 'start')
  Account: Acc 4 - Wind_trader (UID: 8735204819)
  
  TÍNH NĂNG TÀNG HÌNH & TỐI ƯU HÓA ĐỘT PHÁ:
    1. Giả lập chữ ký thiết bị Android 14 (Samsung S24 Ultra, GPU Adreno 750).
    2. Giao thức nhị phân Protobuf chuẩn 100% khớp webapp.
    3. Tự động quét và triệt tiêu 100% các bẫy Honeypot ngầm.
    4. Tự động giải mã và vượt rào Task Gate (/campaigns/gate) nhận thêm USDT.
    5. Ưu tiên xem các mạng QC thưởng cao nhất (0.0002 USDT/lượt).
    6. Tối ưu thời gian nghỉ mệt siêu tốc 30 - 50 giây (Anti-Fatigue).
    7. Giãn cách an toàn 5.5 - 7.0s chống lỗi AD_WATCH_TOO_FAST.
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
from colorama import init, Fore, Style
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestAppWebViewRequest
from telethon.tl.types import InputBotAppShortName

init(autoreset=True)

# -----------------------------------------------------------------
# CẤU HÌNH HỆ THỐNG
# -----------------------------------------------------------------
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "34333329"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "4f9371f95000578c84dbc670aaf1f819")
TELEGRAM_STRING_SESSION = os.getenv("TELEGRAM_STRING_SESSION", "1BVtsOIIBuzNuH5Jfb4Uwek2dG7YRqSyFk-74KTokth0VB3_UTMwM8Edh_ikn83fJOGyN7JaWzIZXnro3icoY8zsjYIlT5nQ4z_GgKknABQ74FRseCvNbz3yyTkPOfQ4xJfZnJIJHuY4EkzVOzQzYZFg_EJWOj_vvg6OVwSkQv9Nd52tl_SlH4TofoxDXDNvxLJyFcoQFH6BegTybx-pFyX2tz0rMeR7AQujnGxqdWOd4zywoFVShzsCTFeqdsBP9itJvg1YB0ISmJEYXzGEQo37IddAFGw3PJcAIY4BBctxri9_Cw-FbxhMgLU9gsotA3Rrys2jLcGV4CGfOp_IzD0CmtNm845I=")

API_BASE = "https://api.paidz.biz"
REPO_NAME = os.getenv("GITHUB_REPOSITORY") or "auo-ele/paidz"
WORKFLOW_FILE = os.getenv("WORKFLOW_FILE", "paidz_acc4.yml")
MAX_RUNTIME_SECONDS = int(os.getenv("MAX_RUNTIME_SECONDS", "17500"))

# Các mạng QC server-to-server (không thể claim trực tiếp từ client)
S2S_NETWORKS = {"adsgram", "usl", "adloop", "onclicka", "adsbitvex"}

# -----------------------------------------------------------------
# TIỆN ÍCH PROTOBUF
# -----------------------------------------------------------------
def enc_varint(n):
    res = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            res.append(b | 0x80)
        else:
            res.append(b)
            break
    return bytes(res)

def dec_varint(buf, pos):
    val = 0
    shift = 0
    while True:
        if pos >= len(buf):
            break
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return val, pos

def enc_string(field_num, s):
    if not s:
        return b""
    raw = s.encode('utf-8') if isinstance(s, str) else s
    key = (field_num << 3) | 2
    return enc_varint(key) + enc_varint(len(raw)) + raw

def enc_bool(field_num, b):
    key = (field_num << 3) | 0
    return enc_varint(key) + enc_varint(1 if b else 0)

def enc_double(field_num, val):
    key = (field_num << 3) | 1
    return enc_varint(key) + struct.pack('<d', float(val))

def decode_proto(buf):
    fields = {}
    pos = 0
    while pos < len(buf):
        tag, pos = dec_varint(buf, pos)
        field_num = tag >> 3
        wire_type = tag & 0x07

        if wire_type == 0:
            val, pos = dec_varint(buf, pos)
            fields[field_num] = val
        elif wire_type == 1:
            if pos + 8 > len(buf):
                break
            val = struct.unpack('<d', buf[pos:pos+8])[0]
            pos += 8
            fields[field_num] = val
        elif wire_type == 2:
            length, pos = dec_varint(buf, pos)
            if pos + length > len(buf):
                break
            val = buf[pos:pos+length]
            pos += length
            if field_num in fields:
                if not isinstance(fields[field_num], list):
                    fields[field_num] = [fields[field_num]]
                fields[field_num].append(val)
            else:
                fields[field_num] = val
        elif wire_type == 5:
            if pos + 4 > len(buf):
                break
            val = struct.unpack('<f', buf[pos:pos+4])[0]
            pos += 4
            fields[field_num] = val
        else:
            break
    return fields

def log(tag, msg, color=Fore.WHITE):
    t_str = time.strftime('%H:%M:%S')
    print(f"{Fore.LIGHTBLACK_EX}[{t_str}]{Style.RESET_ALL} {color}[{tag:10s}]{Style.RESET_ALL} {msg}", flush=True)

# -----------------------------------------------------------------
# CLIENT PAIDZ TÀNG HÌNH (STEALTH ENGINE)
# -----------------------------------------------------------------
class PaidZClient:
    def __init__(self):
        self.token = None
        self.username = None
        self.balance = 0.0
        self.ads_watched = 0
        self.user_agent = (
            "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.135 "
            "Mobile Safari/537.36 Telegram-Android/11.5.3 (Samsung SM-S928B; Android 14; SDK 34; AVERAGE)"
        )
        self.device_uuid = str(uuid.uuid4())

    async def fetch_tg_init_data(self):
        log("TELEGRAM", "Đang kết nối phiên Telegram để lấy tgWebAppData mới nhất...", Fore.CYAN)
        client = TelegramClient(StringSession(TELEGRAM_STRING_SESSION), TELEGRAM_API_ID, TELEGRAM_API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                log("TELEGRAM", "String session không hợp lệ hoặc đã hết hạn!", Fore.RED)
                return None

            bot_peer = await client.get_input_entity("paidzapp")
            app = InputBotAppShortName(bot_id=bot_peer, short_name="start")

            res = await client(RequestAppWebViewRequest(
                peer=bot_peer,
                app=app,
                platform="android",
                write_allowed=True,
                start_param="ref_8735204819"
            ))

            raw_url = res.url
            if "#tgWebAppData=" in raw_url:
                hash_part = raw_url.split("#tgWebAppData=")[1].split("&tgWebAppVersion=")[0]
                init_data = urllib.parse.unquote(hash_part)
                log("TELEGRAM", f"Lấy tgWebAppData thành công ({len(init_data)} bytes).", Fore.GREEN)
                return init_data
            else:
                log("TELEGRAM", f"Không tìm thấy tgWebAppData trong URL: {raw_url}", Fore.YELLOW)
        except Exception as e:
            log("TELEGRAM_ERR", f"Lỗi lấy session init_data: {e}", Fore.RED)
        finally:
            await client.disconnect()
        return None

    def authenticate(self, init_data):
        log("AUTH", "Đang xác thực Protobuf với máy chủ PaidZ (Stealth Android Mode)...", Fore.CYAN)
        parsed = dict(urllib.parse.parse_qsl(init_data))
        raw_user = parsed.get("user", "{}")
        try:
            user_obj = json.loads(raw_user)
            self.username = user_obj.get("username", "Wind_trader")
        except Exception:
            self.username = "Wind_trader"

        headers = {
            'Content-Type': 'application/x-protobuf',
            'Accept': 'application/x-protobuf',
            'x-device-platform': 'android',
            'x-device-model': 'SM-S928B',
            'x-app-version': '1.4.2',
            'x-device-uuid': self.device_uuid,
            'User-Agent': self.user_agent,
            'Origin': 'https://paidz.biz',
            'Referer': 'https://paidz.biz/'
        }

        req_body = b"".join([
            enc_string(1, init_data),
            enc_string(2, "ref_8735204819"),
            enc_string(3, "android"),
            enc_string(4, self.device_uuid),
            enc_string(5, "SM-S928B"),
            enc_string(6, "1.4.2")
        ])

        try:
            r = requests.post(f"{API_BASE}/auth/telegram", data=req_body, headers=headers, timeout=15)
            if r.status_code == 200:
                fields = decode_proto(r.content)
                raw_token = fields.get(1)
                self.token = raw_token.decode('utf-8', errors='ignore') if isinstance(raw_token, bytes) else raw_token
                
                # Cập nhật số dư & tiến độ
                user_fields = decode_proto(fields.get(2, b"")) if isinstance(fields.get(2), bytes) else {}
                self.balance = float(user_fields.get(4, 0.0))
                self.ads_watched = int(user_fields.get(5, 0))

                log("AUTH", f"✅ Đăng nhập thành công! User: @{self.username} | Số dư: {self.balance:.4f} USDT | Đã xem: {self.ads_watched} ads", Fore.GREEN)
                return True
            else:
                log("AUTH_ERR", f"Lỗi HTTP {r.status_code}: {r.text}", Fore.RED)
        except Exception as e:
            log("AUTH_ERR", f"Ngoại lệ đăng nhập: {e}", Fore.RED)
        return False

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/x-protobuf',
            'Accept': 'application/x-protobuf',
            'x-device-platform': 'android',
            'x-device-model': 'SM-S928B',
            'x-app-version': '1.4.2',
            'x-device-uuid': self.device_uuid,
            'User-Agent': self.user_agent,
            'Origin': 'https://paidz.biz',
            'Referer': 'https://paidz.biz/'
        }

    def fetch_clean_networks(self):
        """Lấy danh sách các mạng quảng cáo client hợp lệ, loại trừ S2S và Honeypot."""
        try:
            r = requests.get(f"{API_BASE}/ads/networks", headers=self.get_headers(), timeout=10)
            if r.status_code == 200:
                data = decode_proto(r.content)
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

                        # BỘ LỌC HONEYPOT CHỐNG BAN
                        if is_honeypot or "honeypot" in net_name.lower() or net_name.startswith("secret_"):
                            log("HONEYPOT", f"🛡️ Đã phát hiện và né bẫy Honeypot: '{net_name}'!", Fore.MAGENTA)
                            continue

                        # BỘ LỌC S2S (Loại các mạng bắt buộc webhook máy chủ)
                        if net_name.lower() in S2S_NETWORKS:
                            continue

                        if remaining > 0 or (daily_limit > 0 and watched_today < daily_limit):
                            clean_networks.append({
                                "id": net_id,
                                "name": net_name,
                                "reward": reward,
                                "remaining": remaining or (daily_limit - watched_today)
                            })
                
                # Sắp xếp ưu tiên mạng thưởng cao nhất (0.0002 USDT)
                clean_networks.sort(key=lambda x: x.get("reward", 0.0), reverse=True)
                return clean_networks
        except Exception as e:
            log("NETWORKS_ERR", f"Lỗi lấy danh sách ads: {e}", Fore.RED)
        return []

    def check_and_unlock_task_gate(self):
        """Tự động kiểm tra và mở khóa Task Gate nếu bị dừng xem quảng cáo."""
        try:
            headers = self.get_headers()
            r_gate = requests.get(f"{API_BASE}/campaigns/gate", headers=headers, timeout=10)
            if r_gate.status_code == 200:
                gate_data = decode_proto(r_gate.content)
                completed = gate_data.get(1, 0)
                required = gate_data.get(2, 0)
                raw_items = gate_data.get(4, [])
                if not isinstance(raw_items, list):
                    raw_items = [raw_items]

                if completed < required and raw_items:
                    log("GATE", f"🚧 Phát hiện Task Gate ({completed}/{required}). Tiến hành tự động vượt rào...", Fore.YELLOW)
                    for it in raw_items:
                        if isinstance(it, bytes):
                            tf = decode_proto(it)
                            cid = tf.get(1, b'').decode('utf-8', errors='ignore')
                            title = tf.get(2, b'').decode('utf-8', errors='ignore')
                            
                            log("GATE", f"▶️ Bắt đầu nhiệm vụ Gate: '{title}' ({cid})...", Fore.CYAN)
                            requests.post(f"{API_BASE}/campaigns/{cid}/start", headers=headers, timeout=10)
                            time.sleep(22) # Chờ 22s theo chuẩn quy định máy chủ

                            claim_headers = headers.copy()
                            claim_headers['Content-Type'] = 'application/json'
                            r_c = requests.post(f"{API_BASE}/campaigns/{cid}/claim", headers=claim_headers, json={}, timeout=10)
                            if r_c.status_code == 200:
                                res = decode_proto(r_c.content)
                                rw = float(res.get(3, 0.001))
                                self.balance = float(res.get(4, self.balance + rw))
                                log("GATE", f"🎉 Mở khóa thành công: '{title}' | Nhận thưởng: +{rw:.4f} USDT | Số dư: {self.balance:.4f} USDT", Fore.GREEN)
                                break
                    return True
        except Exception as e:
            log("GATE_ERR", f"Lỗi xử lý Task Gate: {e}", Fore.RED)
        return False

    def watch_ad_stealth(self, network_name):
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
                
                # Nếu bị Task Gate chặn -> Tự động xử lý ngay
                if b'TASK_GATE_REQUIRED' in err_code or b'TASK_GATE' in err_msg:
                    self.check_and_unlock_task_gate()
                    return False, 3

                log("AD_START_WARN", f"Không thể bắt đầu ca xem ({network_name}): {err_code} - {err_msg}", Fore.YELLOW)
                return False, 8

            start_fields = decode_proto(r_start.content)
            session_token_raw = start_fields.get(2, b'')
            session_token = session_token_raw.decode('utf-8', errors='ignore') if isinstance(session_token_raw, bytes) else str(session_token_raw)
            min_duration = int(start_fields.get(4, 3))

            if not session_token:
                return False, 5

            # Thời lượng xem tự nhiên (tối ưu hóa nhanh gọn)
            view_seconds = max(min_duration, 4) + round(random.uniform(1.2, 2.2), 2)
            log("WATCHING", f"🎬 Đang xem quảng cáo '{network_name}'... (thời lượng {view_seconds:.1f}s)", Fore.CYAN)
            time.sleep(view_seconds)

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
                cd = int(w_fields.get(5, 18))
                rem = int(w_fields.get(9, 0))
                log("REWARD", f"🎉 +{reward:.4f} USDT ({network_name}) | Số dư: {self.balance:.4f} USDT | Còn lại: {rem} | Tổng xem: {self.ads_watched}", Fore.GREEN)
                return True, cd
            else:
                err = decode_proto(r_watch.content)
                log("WATCH_ERR", f"Lỗi xác nhận ({network_name}): {err.get(10, b'')} {err.get(11, b'')}", Fore.YELLOW)
        except Exception as e:
            log("WATCH_EXC", f"Ngoại lệ khi xem ad: {e}", Fore.RED)
        return False, 8

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
# VÒNG LẶP CHÍNH 24/7 VỚI BỘ ĐIỀU PHỐI ƯU TIÊN & NGHỈ SIÊU TỐC
# -----------------------------------------------------------------
async def main_loop():
    print(Fore.YELLOW + """
=============================================================================
  BOT AUTO PAIDZ ($USDT) 24/7 - CHẾ ĐỘ TÀNG HÌNH ANTI-DETECTION STEALTH
  Tối ưu hóa tốc độ cao & Tự động mở khóa Task Gate
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

    # Mở khóa Gate & Claim nhiệm vụ đầu ca
    bot.check_and_unlock_task_gate()
    bot.claim_available_tasks()

    start_time = time.time()
    last_refresh_time = time.time()
    ads_session_count = 0
    network_cooldowns = {}

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
                    bot.check_and_unlock_task_gate()
                    last_refresh_time = time.time()

            # Lấy danh sách quảng cáo an toàn (đã lọc sạch Honeypot & S2S)
            networks = bot.fetch_clean_networks()
            if not networks:
                networks = [
                    {"id": "net_gigapub", "name": "gigapub", "reward": 0.0002, "remaining": 50},
                    {"id": "net_tads", "name": "tads", "reward": 0.0002, "remaining": 50},
                    {"id": "net_monetix", "name": "monetix", "reward": 0.0002, "remaining": 50},
                    {"id": "net_richads", "name": "richads", "reward": 0.0002, "remaining": 50},
                    {"id": "net_adexium", "name": "adexium", "reward": 0.0001, "remaining": 50},
                    {"id": "net_telega", "name": "telega", "reward": 0.0001, "remaining": 30}
                ]

            now = time.time()
            # Lọc các mạng đã hết cooldown
            ready_nets = [n for n in networks if now >= network_cooldowns.get(n["name"], 0)]

            if not ready_nets:
                # Nếu tất cả mạng đều đang cooldown -> Chờ mạng gần nhất
                wait_time = min(network_cooldowns.values()) - now
                sleep_t = max(2.0, min(wait_time, 6.0))
                time.sleep(sleep_t)
                continue

            # Ưu tiên nhóm có reward cao nhất
            max_rw = max(n["reward"] for n in ready_nets)
            top_tier_nets = [n for n in ready_nets if n["reward"] >= max_rw]
            target_net = random.choice(top_tier_nets)
            net_name = target_net["name"]

            success, cd = bot.watch_ad_stealth(net_name)
            # Lưu thời điểm hết cooldown của mạng này
            network_cooldowns[net_name] = time.time() + cd

            if success:
                ads_session_count += 1

            # NGHỈ MỆT TỰ NHIÊN (ANTI-FATIGUE CHECK):
            # Cứ xem 5 đến 7 quảng cáo liên tiếp -> Nghỉ nhanh 30 - 50 giây theo yêu cầu
            if ads_session_count >= random.randint(5, 7):
                rest_seconds = round(random.uniform(30.0, 50.0), 1)
                log("REST", f"☕ Mô phỏng người dùng nghỉ mệt {rest_seconds}s (Anti-Fatigue)...", Fore.MAGENTA)
                time.sleep(rest_seconds)
                ads_session_count = 0
            else:
                # Giãn cách an toàn giữa 2 lần xem (5.5 - 7.0s chống lỗi AD_WATCH_TOO_FAST)
                gap_sleep = round(random.uniform(5.5, 7.0), 1)
                time.sleep(gap_sleep)

        except KeyboardInterrupt:
            log("MAIN", "Người dùng dừng chương trình.", Fore.YELLOW)
            break
        except Exception as e:
            log("LOOP_ERR", f"Lỗi vòng lặp: {e}", Fore.RED)
            time.sleep(10)

if __name__ == '__main__':
    asyncio.run(main_loop())
