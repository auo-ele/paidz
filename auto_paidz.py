#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  BOT AUTO PAIDZ ($USDT) 24/7 - CHẾ ĐỘ TÀNG HÌNH ANTI-DETECTION STEALTH
  Platform: PaidZ Mini App (https://paidz.biz/)
  Telegram Bot: @paidzapp (Short name: 'start')
  Account: Acc 4 - Wind_trader (UID: 8735204819)
  
  BẢN TỐI ƯU HÓA 100% (PROTECT OFFICIAL CHANNEL + ANTI-DEADLOCK GATE):
    1. Bảo vệ kênh chính thức (@PAIDZ_NEWS / ID: 2307369718): Tự động Join
       nhưng TUYỆT ĐỐI KHÔNG RỜI KÊNH để duy trì điều kiện xem quảng cáo.
    2. Các kênh nhiệm vụ phụ khác: Tự động Join -> Claim -> Rời kênh 100%.
    3. Chống kẹt Deadlock Task Gate (HTTP 400) & Tự động dừng khi Max Limit.
=============================================================================
"""

import os
import sys
import time
import json
import struct
import random
import hashlib
import asyncio
import urllib.parse
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import init, Fore, Style
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError,
    UserAlreadyParticipantError,
    InviteHashExpiredError,
    UserNotParticipantError,
    ChannelPrivateError
)
from telethon.tl.functions.messages import (
    RequestAppWebViewRequest,
    ImportChatInviteRequest,
    DeleteChatUserRequest
)
from telethon.tl.functions.channels import (
    JoinChannelRequest,
    LeaveChannelRequest,
    GetParticipantRequest
)
from telethon.tl.types import (
    InputBotAppShortName,
    InputChannel,
    InputPeerChannel,
    InputPeerChat,
    Channel,
    Chat
)

init(autoreset=True)

# -----------------------------------------------------------------
# CẤU HÌNH HỆ THỐNG
# -----------------------------------------------------------------
def _safe_int(val, default):
    try:
        s = str(val).strip()
        return int(s) if s else default
    except (TypeError, ValueError):
        return default

TELEGRAM_API_ID = _safe_int(os.getenv("TELEGRAM_API_ID"), 34333329)
TELEGRAM_API_HASH = (os.getenv("TELEGRAM_API_HASH") or "4f9371f95000578c84dbc670aaf1f819").strip()
TELEGRAM_STRING_SESSION = (os.getenv("TELEGRAM_STRING_SESSION") or (
    "1BVtsOIIBuzNuH5Jfb4Uwek2dG7YRqSyFk-74KTokth0VB3_UTMwM8Edh_ikn83fJOGyN7JaWzIZXnro3ico"
    "Y8zsjYIlT5nQ4z_GgKknABQ74FRseCvNbz3yyTkPOfQ4xJfZnJIJHuY4EkzVOzQzYZFg_EJWOj_vvg6OVwSk"
    "Qv9Nd52tl_SlH4TofoxDXDNvxLJyFcoQFH6BegTybx-pFyX2tz0rMeR7AQujnGxqdWOd4zywoFVShzsCTFeq"
    "dsBP9itJvg1YB0ISmJEYXzGEQo37IddAFGw3PJcAIY4BBctxri9_Cw-FbxhMgLU9gsotA3Rrys2jLcGV4CGf"
    "Op_IzD0CmtNm845I="
)).strip()

API_BASE = "https://api.paidz.biz"
REPO_NAME = (os.getenv("GITHUB_REPOSITORY") or "auo-ele/paidz").strip()
WORKFLOW_FILE = (os.getenv("WORKFLOW_FILE") or "paidz_acc4.yml").strip()
MAX_RUNTIME_SECONDS = _safe_int(os.getenv("MAX_RUNTIME_SECONDS"), 17500)

# DANH SÁCH KÊNH CHÍNH THỨC BẮT BUỘC GIỮ LẠI (TUYỆT ĐỐI KHÔNG RỜI KÊNH)
PROTECTED_CHANNEL_IDS = {2307369718}
PROTECTED_USERNAMES = {"paidz_news", "paidz", "paidzapp", "paidz_chat", "paidz_community"}

# Các mạng QC server-to-server (bắt buộc server postback)
S2S_NETWORKS = {"adsgram", "usl", "adloop", "onclicka", "adsbitvex"}

# Danh sách mạng dự phòng khi API /ads/networks nghẽn
FALLBACK_NETWORKS = [
    {"id": "net_gigapub", "name": "gigapub", "reward": 0.0002, "remaining": 80},
    {"id": "net_tads", "name": "tads", "reward": 0.0002, "remaining": 65},
    {"id": "net_monetix", "name": "monetix", "reward": 0.0002, "remaining": 80},
    {"id": "net_richads", "name": "richads", "reward": 0.0002, "remaining": 65},
    {"id": "net_adexium", "name": "adexium", "reward": 0.0001, "remaining": 60},
    {"id": "net_telega", "name": "telega", "reward": 0.0001, "remaining": 30}
]

# -----------------------------------------------------------------
# PROTOBUF UTILS
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
    length = len(buf)
    while pos < length:
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return val, pos

def enc_string(field_num, s):
    if not s:
        return b''
    raw = s.encode('utf-8') if isinstance(s, str) else s
    return enc_varint((field_num << 3) | 2) + enc_varint(len(raw)) + raw

def enc_bytes(field_num, b):
    if not b:
        return b''
    return enc_varint((field_num << 3) | 2) + enc_varint(len(b)) + b

def enc_int32(field_num, v):
    if not v:
        return b''
    return enc_varint((field_num << 3) | 0) + enc_varint(v)

def enc_bool(field_num, b):
    if not b:
        return b''
    return enc_varint((field_num << 3) | 0) + b'\x01'

def enc_double(field_num, d):
    if d == 0:
        return b''
    return enc_varint((field_num << 3) | 1) + struct.pack('<d', float(d))

def decode_proto(data):
    if not data:
        return {}
    pos = 0
    length_data = len(data)
    fields = {}
    while pos < length_data:
        tag, pos = dec_varint(data, pos)
        field_num = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 0:
            val, pos = dec_varint(data, pos)
            fields[field_num] = val
        elif wire_type == 1:
            if pos + 8 > length_data:
                break
            fields[field_num] = struct.unpack('<d', data[pos:pos+8])[0]
            pos += 8
        elif wire_type == 2:
            length, pos = dec_varint(data, pos)
            val = data[pos:pos+length]
            pos += length
            if field_num in fields:
                if not isinstance(fields[field_num], list):
                    fields[field_num] = [fields[field_num]]
                fields[field_num].append(val)
            else:
                fields[field_num] = val
        elif wire_type == 5:
            if pos + 4 > length_data:
                break
            fields[field_num] = struct.unpack('<f', data[pos:pos+4])[0]
            pos += 4
        else:
            break
    return fields

def log(tag, msg, color=Fore.WHITE):
    t_str = time.strftime('%H:%M:%S')
    print(f"{Fore.LIGHTBLACK_EX}[{t_str}]{Style.RESET_ALL} {color}[{tag:12s}]{Style.RESET_ALL} {msg}", flush=True)

def extract_url_from_proto_fields(tf):
    candidates = []
    for val in tf.values():
        items = val if isinstance(val, list) else [val]
        for item in items:
            if isinstance(item, bytes):
                s = item.decode('utf-8', errors='ignore').strip()
                if "/i/userpic/" in s or s.lower().endswith((".jpg", ".png", ".jpeg", ".webp", ".gif", ".svg")):
                    continue
                if "t.me/" in s or "telegram.me/" in s:
                    return s
                if s.startswith("@") and len(s) > 3 and " " not in s and "/" not in s:
                    return f"https://t.me/{s[1:]}"
                if s.startswith("http"):
                    candidates.append(s)
    return candidates[0] if candidates else ""

def create_resilient_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def is_protected_entity(entity):
    """Kiểm tra xem kênh/nhóm có thuộc danh sách cấm rời (như @PAIDZ_NEWS) hay không."""
    if not entity:
        return False
    ent_id = getattr(entity, "id", None)
    ent_username = (getattr(entity, "username", None) or "").lower().strip()
    ent_title = (getattr(entity, "title", None) or "").lower().strip()

    if ent_id in PROTECTED_CHANNEL_IDS:
        return True
    if ent_username in PROTECTED_USERNAMES:
        return True
    if "paidz official" in ent_title or "paidz_news" in ent_title:
        return True
    return False

# -----------------------------------------------------------------
# CLIENT PAIDZ & TELETHON TỐI ƯU
# -----------------------------------------------------------------
class PaidZClient:
    def __init__(self):
        self.token = None
        self.init_data = None
        self.username = None
        self.balance = 0.0
        self.ads_watched = 0
        self.user_agent = (
            "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.135 "
            "Mobile Safari/537.36 Telegram-Android/11.5.0 (Samsung SM-S928B; Android 14; SDK 34; AVERAGE)"
        )
        self.visitor_id = hashlib.md5(TELEGRAM_STRING_SESSION.encode()).hexdigest()
        self.http = create_resilient_session()

        self.claimed_campaign_ids = set()
        self.exhausted_networks = set()
        self._skipped_gate_cache = set()
        self.gate_deadlocked_until = 0
        self.last_ad_claim_time = 0.0
        self.global_ad_cooldown_until = 0.0

        self.tg_client = TelegramClient(
            StringSession(TELEGRAM_STRING_SESSION),
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH,
            device_model="Samsung SM-S928B",
            system_version="Android 14",
            app_version="11.5.0",
            lang_code="vi",
            system_lang_code="vi-VN"
        )

    async def ensure_tg_connected(self):
        if not self.tg_client.is_connected():
            await self.tg_client.connect()
        if not await self.tg_client.is_user_authorized():
            log("TELEGRAM", "❌ StringSession không hợp lệ hoặc đã hết hạn!", Fore.RED)
            return False
        return True

    async def close_tg(self):
        if self.tg_client.is_connected():
            await self.tg_client.disconnect()

    async def fetch_tg_init_data(self):
        log("TELEGRAM", "Đang lấy tgWebAppData mới nhất từ @paidzapp...", Fore.CYAN)
        try:
            if not await self.ensure_tg_connected():
                return None

            bot_peer = await self.tg_client.get_input_entity("paidzapp")
            app = InputBotAppShortName(bot_id=bot_peer, short_name="start")

            res = await self.tg_client(RequestAppWebViewRequest(
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
                log("TELEGRAM", f"Lấy tgWebAppData thành công ({len(init_data)} ký tự).", Fore.GREEN)
                self.init_data = init_data
                return init_data
            else:
                frag = urllib.parse.urlparse(raw_url).fragment
                params = urllib.parse.parse_qs(frag)
                init_data = params.get("tgWebAppData", [None])[0]
                if init_data:
                    log("TELEGRAM", f"Lấy tgWebAppData từ fragment thành công ({len(init_data)} ký tự).", Fore.GREEN)
                    self.init_data = init_data
                    return init_data
        except Exception as e:
            log("TELEGRAM_ERR", f"Lỗi lấy session init_data: {e}", Fore.RED)
        return None

    async def tg_join_target(self, url: str):
        if not url or ("t.me/" not in url and "telegram.me/" not in url) or "/i/userpic/" in url:
            return None

        try:
            if not await self.ensure_tg_connected():
                return None

            parsed = urllib.parse.urlparse(url)
            path = parsed.path.strip("/")
            query = urllib.parse.parse_qs(parsed.query)

            invite_hash = None
            if path.startswith("+"):
                invite_hash = path[1:]
            elif path.startswith("joinchat/"):
                invite_hash = path.split("joinchat/")[1]

            if invite_hash:
                invite_hash = invite_hash.split("/")[0].split("?")[0]
                log("TG_JOIN", f"➕ Đang tham gia nhóm kín (Invite: {invite_hash[:10]}...)...", Fore.CYAN)
                try:
                    updates = await self.tg_client(ImportChatInviteRequest(invite_hash))
                    if hasattr(updates, "chats") and updates.chats:
                        chat_obj = updates.chats[0]
                        title = getattr(chat_obj, "title", "Nhóm kín")
                        log("TG_JOIN", f"✅ Đã tham gia '{title}' (ID: {chat_obj.id}) thành công!", Fore.GREEN)
                        return chat_obj
                except UserAlreadyParticipantError:
                    ent = await self.tg_client.get_entity(url)
                    log("TG_JOIN", "ℹ️ Đã ở trong nhóm từ trước.", Fore.CYAN)
                    return ent
                except InviteHashExpiredError:
                    log("TG_JOIN", "⚠️ Link invite đã hết hạn!", Fore.YELLOW)
                return None

            username = path.split("/")[0].replace("@", "").strip()
            if not username or username.lower() in ("i", "addstickers", "proxy", "socks", "share", "boost"):
                return None

            entity = await self.tg_client.get_entity(username)

            if getattr(entity, "bot", False):
                start_param = query.get("start", [query.get("startapp", [""])[0]])[0]
                cmd = f"/start {start_param}".strip()
                log("TG_BOT", f"🤖 Đang gửi '{cmd}' tới bot @{username}...", Fore.CYAN)
                await self.tg_client.send_message(entity, cmd)
                return entity

            title = getattr(entity, "title", username)
            log("TG_JOIN", f"➕ Đang tham gia kênh/nhóm @{username} ('{title}')...", Fore.CYAN)
            try:
                await self.tg_client(JoinChannelRequest(entity))
                log("TG_JOIN", f"✅ Đã tham gia @{username} (ID: {entity.id}) thành công!", Fore.GREEN)
            except UserAlreadyParticipantError:
                log("TG_JOIN", f"ℹ️ Đã có mặt trong @{username} (ID: {entity.id}).", Fore.CYAN)

            return entity

        except FloodWaitError as e:
            log("TG_FLOOD", f"⏳ Telegram FloodWait: Cần chờ {e.seconds}s...", Fore.YELLOW)
            await asyncio.sleep(min(e.seconds, 60))
        except Exception as e:
            log("TG_JOIN_ERR", f"⚠️ Không thể Join '{url}': {e}", Fore.YELLOW)
        return None

    async def tg_leave_target(self, entity):
        if not entity:
            return

        # KIỂM TRA BẢO VỆ KÊNH CHÍNH THỨC (@PAIDZ_NEWS / ID: 2307369718)
        if is_protected_entity(entity):
            title = getattr(entity, "title", None) or getattr(entity, "username", str(getattr(entity, "id", "Target")))
            log("TG_KEEP", f"🛡️ Giữ nguyên kênh chính thức '{title}' (ID: {getattr(entity, 'id', '')}) - Không rời kênh!", Fore.CYAN)
            return

        try:
            if not await self.ensure_tg_connected():
                return

            title = getattr(entity, "title", None) or getattr(entity, "username", str(getattr(entity, "id", "Target")))

            if getattr(entity, "bot", False):
                log("TG_CLEAN", f"🧹 Đang dọn dẹp hội thoại với bot '{title}'...", Fore.MAGENTA)
                await self.tg_client.delete_dialog(entity, revoke=True)
                log("TG_CLEAN", f"✅ Đã xóa hội thoại bot '{title}'!", Fore.GREEN)
                return

            log("TG_LEAVE", f"🚪 Đang rời khỏi '{title}' (ID: {entity.id})...", Fore.MAGENTA)

            if isinstance(entity, Channel) or hasattr(entity, "access_hash"):
                input_chan = InputChannel(channel_id=entity.id, access_hash=entity.access_hash)
                input_peer = InputPeerChannel(channel_id=entity.id, access_hash=entity.access_hash)

                try:
                    await self.tg_client(LeaveChannelRequest(channel=input_chan))
                except UserNotParticipantError:
                    pass
                except Exception:
                    pass

                try:
                    await self.tg_client.delete_dialog(input_peer, revoke=True)
                except Exception:
                    pass

                await asyncio.sleep(1.5)
                still_inside = False
                try:
                    await self.tg_client(GetParticipantRequest(channel=input_chan, participant="me"))
                    still_inside = True
                except (UserNotParticipantError, ChannelPrivateError):
                    still_inside = False
                except Exception:
                    still_inside = False

                if still_inside:
                    try:
                        await self.tg_client(LeaveChannelRequest(channel=input_chan))
                        await asyncio.sleep(1)
                    except Exception:
                        pass
                log("TG_LEAVE", f"✅ Đã rời khỏi '{title}' thành công 100% (Đã xác minh Server)!", Fore.GREEN)

            elif isinstance(entity, Chat):
                try:
                    await self.tg_client(DeleteChatUserRequest(chat_id=entity.id, user_id="me"))
                except Exception:
                    pass
                try:
                    await self.tg_client.delete_dialog(InputPeerChat(chat_id=entity.id), revoke=True)
                except Exception:
                    pass
                log("TG_LEAVE", f"✅ Đã rời khỏi nhóm '{title}' thành công!", Fore.GREEN)

            else:
                await self.tg_client.delete_dialog(entity, revoke=True)
                log("TG_LEAVE", f"✅ Đã rời khỏi '{title}' thành công!", Fore.GREEN)

        except Exception as e:
            log("TG_LEAVE_ERR", f"❌ Lỗi khi rời kênh: {e}", Fore.RED)

    def authenticate(self, init_data=None, silent=False):
        if init_data:
            self.init_data = init_data
        if not self.init_data:
            return False

        if not silent:
            log("AUTH", "Đang xác thực Protobuf với máy chủ PaidZ...", Fore.YELLOW)

        telemetry_bytes = b"".join([
            enc_string(1, self.visitor_id),
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
            enc_string(1, self.init_data),
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
            r = self.http.post(f"{API_BASE}/auth/telegram", data=req_body, headers=headers, timeout=15)
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
                        log("AUTH_BAN", "❌ Tài khoản đã bị máy chủ PaidZ đánh dấu cấm!", Fore.RED)
                        return False

                if not silent:
                    log("AUTH", f"✅ Đăng nhập thành công! User: @{self.username} | Số dư: {self.balance:.4f} USDT | Đã xem: {self.ads_watched} ads", Fore.GREEN)
                return True
            else:
                if not silent:
                    log("AUTH_ERR", f"Lỗi xác thực HTTP {r.status_code}: {r.text[:150]}", Fore.RED)
        except Exception as e:
            if not silent:
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

    def parse_claim_response(self, content: bytes, old_balance: float):
        if content and content.startswith(b"{"):
            try:
                j = json.loads(content.decode('utf-8', errors='ignore'))
                if j.get("error") or j.get("success") is False:
                    return False, 0.0, old_balance, str(j.get("message") or j.get("error"))
            except Exception:
                pass

        res = decode_proto(content) if content else {}
        for err_fld in [5, 6, 10, 11]:
            val = res.get(err_fld)
            if isinstance(val, bytes) and len(val) > 0:
                err_str = val.decode('utf-8', errors='ignore')
                if any(k in err_str.upper() for k in ["ERR", "FAIL", "ALREADY", "NOT_", "INVALID", "WAIT", "COMPLETED"]):
                    return False, 0.0, old_balance, err_str

        proto_bal = 0.0
        for val in res.values():
            if isinstance(val, float) and val > old_balance:
                proto_bal = val

        if proto_bal > old_balance:
            return True, proto_bal - old_balance, proto_bal, "OK (Proto)"

        self.authenticate(silent=True)
        if self.balance > old_balance:
            return True, self.balance - old_balance, self.balance, "OK (DB Verified)"

        return False, 0.0, self.balance, "Không cộng thêm tiền (Đã làm trước đó hoặc chưa đủ ĐK)"

    def fetch_clean_networks(self):
        try:
            r = self.http.get(f"{API_BASE}/ads/networks", headers=self.get_headers(), timeout=10)
            if r.status_code == 200:
                data = decode_proto(r.content)
                raw_nets = data.get(1, [])
                if not isinstance(raw_nets, list):
                    raw_nets = [raw_nets]
                
                clean_networks = []
                valid_client_nets_seen = 0

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

                        if is_honeypot or "honeypot" in net_name.lower() or net_name.startswith("secret_"):
                            continue

                        if net_name.lower() in S2S_NETWORKS:
                            continue

                        valid_client_nets_seen += 1

                        if net_name in self.exhausted_networks:
                            continue

                        rem = remaining if remaining is not None else max(0, daily_limit - watched_today)
                        if daily_limit > 0 and watched_today >= daily_limit:
                            rem = 0

                        if rem > 0:
                            clean_networks.append({
                                "id": net_id,
                                "name": net_name,
                                "reward": reward,
                                "remaining": rem
                            })
                        else:
                            self.exhausted_networks.add(net_name)
                
                clean_networks.sort(key=lambda x: x.get("reward", 0.0), reverse=True)
                all_maxed = (valid_client_nets_seen > 0 and len(clean_networks) == 0)
                return clean_networks, all_maxed

        except Exception as e:
            log("NETWORKS_ERR", f"Lỗi lấy danh sách ads: {e}", Fore.RED)

        fallback = [n for n in FALLBACK_NETWORKS if n["name"] not in self.exhausted_networks]
        all_maxed = (len(fallback) == 0)
        return fallback, all_maxed

    async def execute_campaign_flow(self, cid: str, title: str, url_str: str, tag_name="GATE"):
        headers = self.get_headers()
        old_balance = self.balance
        log(tag_name, f"▶️ Bắt đầu nhiệm vụ: '{title}' ({cid})...", Fore.CYAN)

        r_start = self.http.post(f"{API_BASE}/campaigns/{cid}/start", headers=headers, timeout=10)
        if r_start.status_code != 200:
            log(f"{tag_name}_SKIP", f"Bỏ qua '{title}' (HTTP {r_start.status_code} - Đã hoàn thành hoặc hết hạn)", Fore.YELLOW)
            return False

        start_data = decode_proto(r_start.content)
        dynamic_url = extract_url_from_proto_fields(start_data)
        if dynamic_url:
            url_str = dynamic_url

        joined_entity = None
        if url_str:
            log(tag_name, f"🔗 Mục tiêu nhiệm vụ: {url_str[:65]}", Fore.CYAN)
            if "t.me/" in url_str or "telegram.me/" in url_str:
                joined_entity = await self.tg_join_target(url_str)
            else:
                try:
                    self.http.get(url_str, headers={'User-Agent': self.user_agent}, timeout=10, allow_redirects=True)
                except Exception:
                    pass

        wait_sec = int(start_data.get(5, 22))
        if wait_sec < 12 or wait_sec > 45:
            wait_sec = 22
        log(tag_name, f"⏳ Đang chờ {wait_sec}s để hệ thống xác nhận...", Fore.CYAN)
        await asyncio.sleep(wait_sec)

        claimed = False
        claim_body = enc_string(1, cid)

        for attempt in range(2):
            r_c = self.http.post(f"{API_BASE}/campaigns/{cid}/claim", data=claim_body, headers=headers, timeout=10)
            if r_c.status_code != 200:
                claim_h2 = headers.copy()
                claim_h2['Content-Type'] = 'application/json'
                r_c = self.http.post(f"{API_BASE}/campaigns/{cid}/claim", headers=claim_h2, json={}, timeout=10)

            if r_c.status_code == 200:
                ok, rw, new_bal, reason = self.parse_claim_response(r_c.content, old_balance)
                if ok:
                    self.balance = new_bal
                    log(tag_name, f"🎉 CỘNG TIỀN THẬT: '{title}' | +{rw:.4f} USDT | Số dư mới: {self.balance:.4f} USDT", Fore.GREEN)
                    claimed = True
                else:
                    log(f"{tag_name}_INFO", f"ℹ️ Đã xử lý '{title}' (Số dư: {self.balance:.4f} USDT): {reason}", Fore.YELLOW)
                    claimed = True
                break
            else:
                err_info = decode_proto(r_c.content)
                log(f"{tag_name}_WARN", f"Claim lần {attempt+1} lỗi (HTTP {r_c.status_code}): {err_info}", Fore.YELLOW)
                await asyncio.sleep(4)

        if joined_entity and not is_protected_entity(joined_entity):
            await asyncio.sleep(4)
            await self.tg_leave_target(joined_entity)
        elif joined_entity:
            await self.tg_leave_target(joined_entity)

        return claimed

    async def check_and_unlock_task_gate(self):
        if time.time() < self.gate_deadlocked_until:
            return False

        try:
            headers = self.get_headers()
            r_gate = self.http.get(f"{API_BASE}/campaigns/gate", headers=headers, timeout=10)
            if r_gate.status_code != 200:
                log("GATE_ERR", f"Không thể lấy thông tin Gate (HTTP {r_gate.status_code})", Fore.RED)
                return False

            gate_data = decode_proto(r_gate.content)
            completed = gate_data.get(1, 0)
            required = gate_data.get(2, 0)
            raw_items = gate_data.get(4, [])
            if not isinstance(raw_items, list):
                raw_items = [raw_items]

            if completed >= required and required > 0:
                log("GATE", f"✅ Gate đã hoàn thành ({completed}/{required}), không cần mở khóa.", Fore.GREEN)
                return True

            if not raw_items:
                return False

            actionable_items = []
            for it in raw_items:
                if not isinstance(it, bytes):
                    continue
                tf = decode_proto(it)
                cid = tf.get(1, b'').decode('utf-8', errors='ignore') if isinstance(tf.get(1), bytes) else str(tf.get(1, ''))
                title = tf.get(2, b'').decode('utf-8', errors='ignore') if isinstance(tf.get(2), bytes) else str(tf.get(2, ''))
                if cid and cid not in self._skipped_gate_cache:
                    actionable_items.append((cid, title, extract_url_from_proto_fields(tf)))

            if not actionable_items:
                log("GATE_LOCK", "⚠️ Tất cả nhiệm vụ trong Task Gate hiện tại đều đã hết hạn (HTTP 400). Tạm khóa Gate 15 phút để tránh lặp vô tận!", Fore.MAGENTA)
                self.gate_deadlocked_until = time.time() + 900
                return False

            log("GATE", f"🚧 Phát hiện Task Gate ({completed}/{required}). Có {len(actionable_items)} nhiệm vụ khả dụng...", Fore.YELLOW)

            unlocked_any = False
            for cid, title, url_str in actionable_items:
                success = await self.execute_campaign_flow(cid, title, url_str, tag_name="GATE")
                if success:
                    completed += 1
                    unlocked_any = True
                    if required > 0 and completed >= required:
                        log("GATE", f"✅ Đã mở khóa đủ yêu cầu Task Gate ({completed}/{required})!", Fore.GREEN)
                        break
                else:
                    self._skipped_gate_cache.add(cid)

            if not unlocked_any:
                log("GATE_LOCK", "⚠️ Không thể hoàn thành nhiệm vụ Gate nào (lỗi phía Server). Tạm nghỉ Gate 15 phút!", Fore.MAGENTA)
                self.gate_deadlocked_until = time.time() + 900
                return False

            return True
        except Exception as e:
            log("GATE_ERR", f"Lỗi xử lý Task Gate: {e}", Fore.RED)
            return False

    def spin_lucky_wheel(self):
        try:
            headers = self.get_headers()
            rw = self.http.get(f"{API_BASE}/wheel/status", headers=headers, timeout=10)
            if rw.status_code == 200:
                wheel_data = decode_proto(rw.content)
                if wheel_data.get(3, False):
                    log("WHEEL", "🎡 Phát hiện lượt quay Lucky Wheel miễn phí! Đang quay...", Fore.CYAN)
                    old_bal = self.balance
                    nonce = str(int(time.time() * 1000))
                    r_spin = self.http.post(f"{API_BASE}/wheel/spin", data=enc_string(1, nonce), headers=headers, timeout=10)
                    if r_spin.status_code == 200:
                        ok, rw_amt, new_bal, _ = self.parse_claim_response(r_spin.content, old_bal)
                        if ok:
                            self.balance = new_bal
                            log("WHEEL", f"🎉 Quay trúng +{rw_amt:.4f} USDT! Số dư mới: {self.balance:.4f} USDT", Fore.GREEN)
                        else:
                            log("WHEEL", "✅ Đã hoàn thành lượt quay Lucky Wheel!", Fore.GREEN)
        except Exception as e:
            log("WHEEL_ERR", f"Lỗi quay thưởng wheel: {e}", Fore.RED)

    async def claim_available_tasks(self):
        try:
            headers = self.get_headers()
            r = self.http.get(f"{API_BASE}/tasks", headers=headers, timeout=10)
            if r.status_code == 200:
                data = decode_proto(r.content)
                tasks = data.get(1, [])
                if not isinstance(tasks, list):
                    tasks = [tasks]
                for t in tasks:
                    if isinstance(t, bytes):
                        tf = decode_proto(t)
                        tid = tf.get(1, b'').decode('utf-8', errors='ignore') if isinstance(tf.get(1), bytes) else str(tf.get(1))
                        title = tf.get(2, b'').decode('utf-8', errors='ignore') if isinstance(tf.get(2), bytes) else str(tf.get(2))
                        if not tf.get(11, 0):
                            old_bal = self.balance
                            url_str = extract_url_from_proto_fields(tf)
                            joined_entity = None
                            if url_str and ("t.me/" in url_str or "telegram.me/" in url_str):
                                joined_entity = await self.tg_join_target(url_str)
                                await asyncio.sleep(5)

                            r_c = self.http.post(f"{API_BASE}/tasks/{tid}/claim", data=enc_string(1, tid), headers=headers, timeout=10)
                            if r_c.status_code == 200:
                                ok, rw, new_bal, _ = self.parse_claim_response(r_c.content, old_bal)
                                if ok:
                                    self.balance = new_bal
                                    log("TASK", f"✅ Hoàn thành nhiệm vụ: '{title}' (+{rw:.4f} USDT) | Số dư: {self.balance:.4f} USDT", Fore.GREEN)

                            if joined_entity and not is_protected_entity(joined_entity):
                                await asyncio.sleep(4)
                                await self.tg_leave_target(joined_entity)
                            elif joined_entity:
                                await self.tg_leave_target(joined_entity)
        except Exception as e:
            log("TASK_ERR", f"Lỗi claim nhiệm vụ: {e}", Fore.RED)

    async def claim_community_campaigns(self):
        try:
            headers = self.get_headers()
            rf = self.http.get(f"{API_BASE}/campaigns/feed?page=1&limit=15", headers=headers, timeout=10)
            if rf.status_code == 200:
                fd = decode_proto(rf.content)
                c_items = fd.get(1, [])
                if not isinstance(c_items, list):
                    c_items = [c_items]
                
                for it in c_items:
                    if isinstance(it, bytes):
                        f = decode_proto(it)
                        cid = f.get(1, b'').decode('utf-8', errors='ignore') if isinstance(f.get(1), bytes) else str(f.get(1))
                        title = f.get(2, b'').decode('utf-8', errors='ignore') if isinstance(f.get(2), bytes) else str(f.get(2))
                        url_str = extract_url_from_proto_fields(f)
                        
                        if not cid or cid in self.claimed_campaign_ids:
                            continue

                        await self.execute_campaign_flow(cid, title, url_str, tag_name="CAMPAIGN")
                        self.claimed_campaign_ids.add(cid)
                        await asyncio.sleep(4)
        except Exception as e:
            log("CAMPAIGN_ERR", f"Lỗi nhiệm vụ cộng đồng: {e}", Fore.RED)

    async def watch_ad_stealth(self, network_name):
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
            r_start = self.http.post(f"{API_BASE}/ads/start", data=req_start, headers=self.get_headers(), timeout=12)
            if r_start.status_code != 200:
                err_data = decode_proto(r_start.content)
                err_code = err_data.get(5, b'')
                err_msg = err_data.get(6, b'')
                err_code_str = err_code.decode('utf-8', errors='ignore') if isinstance(err_code, bytes) else str(err_code)
                err_msg_str = err_msg.decode('utf-8', errors='ignore') if isinstance(err_msg, bytes) else str(err_msg)

                if b'TASK_GATE_REQUIRED' in err_code or b'TASK_GATE' in err_msg:
                    gate_ok = await self.check_and_unlock_task_gate()
                    if not gate_ok:
                        return False, 900
                    return False, 3

                if b'DAILY_LIMIT_REACHED' in err_code or b'Daily limit' in err_msg:
                    self.exhausted_networks.add(network_name)
                    log("MAX_LIMIT", f"🛑 Mạng '{network_name}' đã đạt giới hạn tối đa trong ngày!", Fore.MAGENTA)
                    return False, 0

                # Xử lý khi mạng hết quảng cáo khu vực (NO_FILL_COOLDOWN)
                if 'NO_FILL' in err_code_str or 'No ads available' in err_msg_str:
                    cd = random.randint(90, 150)
                    log("NO_FILL", f"⏸️ Mạng '{network_name}' tạm hết quảng cáo vùng. Tạm dừng {cd}s để ưu tiên mạng khác.", Fore.YELLOW)
                    return False, cd

                # Xử lý nếu bị AD_WATCH_TOO_FAST từ bước start
                if 'TOO_FAST' in err_code_str or 'Too fast' in err_msg_str or 'wait' in err_msg_str.lower():
                    m = re.search(r'wait (\d+) more second', err_msg_str, re.IGNORECASE)
                    wait_sec = (int(m.group(1)) + 1.5) if m else 8.0
                    log("TOO_FAST", f"⏱️ Máy chủ yêu cầu chờ {wait_sec:.1f}s giữa các lượt QC: {err_msg_str}", Fore.YELLOW)
                    self.global_ad_cooldown_until = time.time() + wait_sec
                    await asyncio.sleep(wait_sec)
                    return False, 5

                log("AD_START_WARN", f"Không thể bắt đầu ca xem ({network_name}): {err_code_str} - {err_msg_str}", Fore.YELLOW)
                return False, 15

            start_fields = decode_proto(r_start.content)
            session_token_raw = start_fields.get(2, b'')
            session_token = session_token_raw.decode('utf-8', errors='ignore') if isinstance(session_token_raw, bytes) else str(session_token_raw)
            min_duration = int(start_fields.get(4, 3))

            if not session_token:
                return False, 5

            # Thời lượng xem tự nhiên (8.5 - 11.5s) mô phỏng người dùng thật xem video/interstitial ad
            view_seconds = max(min_duration, 7) + round(random.uniform(1.8, 3.8), 2)
            log("WATCHING", f"🎬 Đang xem quảng cáo '{network_name}'... (thời lượng {view_seconds:.1f}s)", Fore.CYAN)
            await asyncio.sleep(view_seconds)

            # Đảm bảo khoảng cách giữa 2 lần claim QC cách nhau ít nhất 18.5s theo quy định máy chủ PaidZ
            elapsed_since_last_claim = time.time() - self.last_ad_claim_time
            if elapsed_since_last_claim < 18.5:
                extra_wait = round(18.5 - elapsed_since_last_claim, 1)
                await asyncio.sleep(extra_wait)

            duration_ms = view_seconds * 1000.0
            req_watch = b"".join([
                enc_string(1, network_name),
                enc_string(2, session_token),
                enc_double(3, duration_ms),
                enc_string(4, "")
            ])

            r_watch = self.http.post(f"{API_BASE}/ads/watch", data=req_watch, headers=self.get_headers(), timeout=12)
            if r_watch.status_code == 200:
                self.last_ad_claim_time = time.time()
                w_fields = decode_proto(r_watch.content)
                reward = float(w_fields.get(2, 0.0))
                self.balance = float(w_fields.get(3, self.balance + reward))
                self.ads_watched = int(w_fields.get(4, self.ads_watched + 1))
                cd = int(w_fields.get(5, 18))
                rem = int(w_fields.get(9, 0))
                log("REWARD", f"🎉 +{reward:.4f} USDT ({network_name}) | Số dư: {self.balance:.4f} USDT | Còn lại: {rem} | Tổng xem: {self.ads_watched}", Fore.GREEN)
                if rem <= 0:
                    self.exhausted_networks.add(network_name)
                return True, cd
            else:
                err = decode_proto(r_watch.content)
                err_code = err.get(10, b'')
                err_msg = err.get(11, b'')
                err_code_str = err_code.decode('utf-8', errors='ignore') if isinstance(err_code, bytes) else str(err_code)
                err_msg_str = err_msg.decode('utf-8', errors='ignore') if isinstance(err_msg, bytes) else str(err_msg)

                # Bắt lỗi AD_WATCH_TOO_FAST từ server
                if 'TOO_FAST' in err_code_str or 'Too fast' in err_msg_str or 'wait' in err_msg_str.lower():
                    m = re.search(r'wait (\d+) more second', err_msg_str, re.IGNORECASE)
                    wait_sec = (int(m.group(1)) + 1.5) if m else 7.5
                    log("TOO_FAST", f"⏱️ Máy chủ yêu cầu chờ {wait_sec:.1f}s trước khi claim QC tiếp ({network_name}): {err_msg_str}", Fore.YELLOW)
                    self.global_ad_cooldown_until = time.time() + wait_sec
                    await asyncio.sleep(wait_sec)
                    return False, 5
                else:
                    log("WATCH_ERR", f"Lỗi xác nhận ({network_name}): {err_code_str} {err_msg_str}", Fore.YELLOW)
                    return False, 10
        except Exception as e:
            log("WATCH_EXC", f"Ngoại lệ khi xem ad: {e}", Fore.RED)
        return False, 10


def trigger_next_shift():
    log("HANDOVER", f"🔄 Chuẩn bị chuyển giao ca làm việc tiếp theo trên {REPO_NAME}...", Fore.CYAN)
    pat = os.getenv("GH_PAT", "").strip()
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
# VÒNG LẶP CHÍNH
# -----------------------------------------------------------------
async def main_loop():
    print(Fore.YELLOW + """
=============================================================================
  BOT AUTO PAIDZ ($USDT) - CHẾ ĐỘ TÀNG HÌNH ANTI-DETECTION STEALTH
  Tối ưu hóa: Nghỉ siêu tốc 10-20s (Anti-Fatigue) | Giữ Kênh @PAIDZ_NEWS
=============================================================================
    """ + Style.RESET_ALL)

    bot = PaidZClient()
    try:
        init_data = await bot.fetch_tg_init_data()
        if not init_data:
            log("MAIN", "Không thể lấy tgWebAppData. Dừng chương trình.", Fore.RED)
            return

        if not bot.authenticate(init_data):
            log("MAIN", "Đăng nhập thất bại.", Fore.RED)
            return

        # Đảm bảo tài khoản luôn ở trong kênh chính thức @PAIDZ_NEWS ngay khi khởi động
        await bot.tg_join_target("https://t.me/PAIDZ_NEWS")

        await bot.check_and_unlock_task_gate()
        bot.spin_lucky_wheel()
        await bot.claim_available_tasks()
        await bot.claim_community_campaigns()

        start_time = time.time()
        last_refresh_time = time.time()
        last_task_check_time = time.time()
        ads_session_count = 0
        network_cooldowns = {}

        while True:
            try:
                networks, all_maxed = bot.fetch_clean_networks()

                if all_maxed or not networks:
                    log(
                        "DONE",
                        f"🏁 Tất cả các mạng quảng cáo hôm nay đã đạt giới hạn tối đa (Max Daily Limit)! "
                        f"Số dư hiện tại: {bot.balance:.4f} USDT | Tổng đã xem: {bot.ads_watched} ads. "
                        f"Bot sẽ nghỉ và tự động mở lại vào 00:00 ngày mai!",
                        Fore.GREEN
                    )
                    break

                if (time.time() - start_time) >= MAX_RUNTIME_SECONDS:
                    log("HANDOVER", "Hoàn thành ca trực 4.8 tiếng (vẫn còn lượt). Tự động chuyển giao ca tiếp theo...", Fore.CYAN)
                    trigger_next_shift()
                    break

                if (time.time() - last_refresh_time) >= 1800:
                    new_init = await bot.fetch_tg_init_data()
                    if new_init:
                        bot.authenticate(new_init)
                        bot._skipped_gate_cache.clear()
                        await bot.check_and_unlock_task_gate()
                        last_refresh_time = time.time()

                if (time.time() - last_task_check_time) >= 3600:
                    await bot.claim_available_tasks()
                    await bot.claim_community_campaigns()
                    last_task_check_time = time.time()

                now = time.time()

                # Kiểm tra cooldown toàn cục
                if now < bot.global_ad_cooldown_until:
                    sleep_g = bot.global_ad_cooldown_until - now
                    await asyncio.sleep(sleep_g)
                    now = time.time()

                ready_nets = [n for n in networks if now >= network_cooldowns.get(n["name"], 0) and n["name"] not in bot.exhausted_networks]

                if not ready_nets:
                    valid_cooldowns = [network_cooldowns.get(n["name"], now + 5) for n in networks if n["name"] not in bot.exhausted_networks]
                    wait_time = (min(valid_cooldowns) - now) if valid_cooldowns else 5.0
                    sleep_t = max(2.0, min(wait_time, 20.0))
                    await asyncio.sleep(sleep_t)
                    continue

                max_rw = max(n["reward"] for n in ready_nets)
                top_tier_nets = [n for n in ready_nets if n["reward"] >= max_rw]
                target_net = random.choice(top_tier_nets)
                net_name = target_net["name"]

                success, cd = await bot.watch_ad_stealth(net_name)
                if cd > 0:
                    network_cooldowns[net_name] = time.time() + cd

                if net_name in bot.exhausted_networks:
                    await asyncio.sleep(1.0)
                    continue

                if success:
                    ads_session_count += 1

                if ads_session_count >= random.randint(5, 7):
                    rest_seconds = round(random.uniform(10.0, 20.0), 1)
                    log("REST", f"☕ Nghỉ ngắn {rest_seconds}s (Anti‑Fatigue)...", Fore.MAGENTA)
                    await asyncio.sleep(rest_seconds)
                    ads_session_count = 0
                else:
                    gap_sleep = round(random.uniform(8.0, 11.0), 1)
                    await asyncio.sleep(gap_sleep)

            except KeyboardInterrupt:
                log("MAIN", "Người dùng dừng chương trình.", Fore.YELLOW)
                break
            except Exception as e:
                log("LOOP_ERR", f"Lỗi vòng lặp: {e}", Fore.RED)
                await asyncio.sleep(10)
    finally:
        await bot.close_tg()

if __name__ == '__main__':
    asyncio.run(main_loop())
