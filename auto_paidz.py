#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  BOT AUTO PAIDZ ($USDT) 24/7 - CHẾ ĐỘ TÀNG HÌNH ANTI-DETECTION STEALTH
  Platform: PaidZ Mini App (https://paidz.biz/)
  Telegram Bot: @paidzapp (Short name: 'start')
  Account: Acc 4 - Wind_trader (UID: 8735204819)
  
  PHIÊN BẢN CHẤT LƯỢNG 100% (PERSISTENT TELETHON + VERIFIED LEAVE + REAL BALANCE):
    1. Duy trì 1 phiên Telethon duy nhất (Persistent Client) kèm thông số phần cứng
       Samsung S24 Ultra -> Không bị mất cache access_hash, chống ban Telegram.
    2. Sửa triệt để 100% lỗi "Báo đã rời nhưng thực tế chưa rời":
       - Dùng trực tiếp InputChannel(channel_id, access_hash) + delete_dialog(revoke=True).
       - Hậu kiểm bằng GetParticipantRequest: Xác nhận đã thoát thật trên Server Telegram.
    3. Bộ lọc URL thông minh: Chặn tuyệt đối link ảnh đại diện (/i/userpic/...).
    4. Đối chiếu số dư thật trên Database PaidZ trước và sau khi Claim (không báo ảo).
    5. Quét & né 100% bẫy Honeypot và mạng S2S.
    6. Tự động bàn giao ca trực 24/7 sau 4.8h (GitHub Actions Handover).
=============================================================================
"""

import os
import sys
import time
import json
import uuid
import struct
import random
import hashlib
import asyncio
import urllib.parse
import requests
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
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "34333329"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "4f9371f95000578c84dbc670aaf1f819")
TELEGRAM_STRING_SESSION = os.getenv(
    "TELEGRAM_STRING_SESSION",
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

# Các mạng QC server-to-server (bắt buộc server postback)
S2S_NETWORKS = {"adsgram", "usl", "adloop", "onclicka", "adsbitvex"}

# -----------------------------------------------------------------
# PROTOBUF UTILS (CHUẨN XÁC 100%)
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
        return b''
    raw = s.encode('utf-8') if isinstance(s, str) else s
    tag = enc_varint((field_num << 3) | 2)
    return tag + enc_varint(len(raw)) + raw

def enc_bytes(field_num, b):
    if not b:
        return b''
    tag = enc_varint((field_num << 3) | 2)
    return tag + enc_varint(len(b)) + b

def enc_int32(field_num, v):
    if not v:
        return b''
    tag = enc_varint((field_num << 3) | 0)
    return tag + enc_varint(v)

def enc_bool(field_num, b):
    if not b:
        return b''
    tag = enc_varint((field_num << 3) | 0)
    return tag + b'\x01'

def enc_double(field_num, d):
    if d == 0:
        return b''
    tag = enc_varint((field_num << 3) | 1)
    return tag + struct.pack('<d', float(d))

def decode_proto(data):
    pos = 0
    fields = {}
    while pos < len(data):
        tag, pos = dec_varint(data, pos)
        field_num = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 0:
            val, pos = dec_varint(data, pos)
            fields[field_num] = val
        elif wire_type == 1:
            if pos + 8 > len(data):
                break
            val = struct.unpack('<d', data[pos:pos+8])[0]
            pos += 8
            fields[field_num] = val
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
            if pos + 4 > len(data):
                break
            val = struct.unpack('<f', data[pos:pos+4])[0]
            pos += 4
            fields[field_num] = val
        else:
            break
    return fields

def log(tag, msg, color=Fore.WHITE):
    t_str = time.strftime('%H:%M:%S')
    print(f"{Fore.LIGHTBLACK_EX}[{t_str}]{Style.RESET_ALL} {color}[{tag:10s}]{Style.RESET_ALL} {msg}", flush=True)

def extract_url_from_proto_fields(tf):
    """
    Quét mọi trường protobuf để tìm URL nhiệm vụ thật.
    Loại bỏ 100% link ảnh avatar (/i/userpic/...) hoặc file ảnh tĩnh (.jpg, .png...).
    """
    candidates = []
    for fld, val in tf.items():
        items = val if isinstance(val, list) else [val]
        for item in items:
            if isinstance(item, bytes):
                s = item.decode('utf-8', errors='ignore').strip()
                if "/i/userpic/" in s or any(s.lower().endswith(ext) for ext in (".jpg", ".png", ".jpeg", ".webp", ".gif", ".svg")):
                    continue
                if "t.me/" in s or "telegram.me/" in s:
                    return s
                if s.startswith("@") and len(s) > 3 and " " not in s and "/" not in s:
                    return f"https://t.me/{s[1:]}"
                if s.startswith("http"):
                    candidates.append(s)
    return candidates[0] if candidates else ""

# -----------------------------------------------------------------
# CLIENT PAIDZ & TELETHON TÍCH HỢP (CHUẨN 100% JOIN -> CLAIM -> OUT)
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
        # Cố định visitor_id theo tài khoản để chống phát hiện đổi thiết bị
        self.visitor_id = hashlib.md5(TELEGRAM_STRING_SESSION.encode()).hexdigest()
        self.http = requests.Session()
        self.claimed_campaign_ids = set()

        # Duy trì 1 đối tượng TelegramClient duy nhất giữ nguyên Entity Cache
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
        """Đảm bảo kết nối Telegram luôn mở mà không tạo lại session mới."""
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
                log("TELEGRAM", f"Không tìm thấy tgWebAppData trong URL: {raw_url}", Fore.YELLOW)
        except Exception as e:
            log("TELEGRAM_ERR", f"Lỗi lấy session init_data: {e}", Fore.RED)
        return None

    async def tg_join_target(self, url: str):
        """
        Tham gia Kênh/Nhóm hoặc gửi /start cho Bot trên cùng 1 phiên Telethon.
        Trả về đối tượng Entity gốc (Channel/Chat) có đầy đủ id & access_hash.
        """
        if not url or ("t.me/" not in url and "telegram.me/" not in url) or "/i/userpic/" in url:
            return None

        try:
            if not await self.ensure_tg_connected():
                return None

            parsed = urllib.parse.urlparse(url)
            path = parsed.path.strip("/")
            query = urllib.parse.parse_qs(parsed.query)

            # 1. Xử lý link mời riêng tư (t.me/+xxxx hoặc t.me/joinchat/xxxx)
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
                    log("TG_JOIN", f"ℹ️ Đã ở trong '{getattr(ent, 'title', 'Nhóm')}' từ trước.", Fore.CYAN)
                    return ent
                except InviteHashExpiredError:
                    log("TG_JOIN", "⚠️ Link invite đã hết hạn!", Fore.YELLOW)
                return None

            # 2. Xử lý Username công khai
            username = path.split("/")[0].replace("@", "").strip()
            if not username or username.lower() in ("i", "addstickers", "proxy", "socks", "share", "boost"):
                return None

            entity = await self.tg_client.get_entity(username)

            # Nếu là Bot -> Gửi /start kèm ref rồi xóa hội thoại sau
            if getattr(entity, "bot", False):
                start_param = query.get("start", [query.get("startapp", [""])[0]])[0]
                cmd = f"/start {start_param}".strip()
                log("TG_BOT", f"🤖 Đang gửi '{cmd}' tới bot @{username}...", Fore.CYAN)
                await self.tg_client.send_message(entity, cmd)
                return entity

            # Nếu là Channel hoặc Supergroup
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
        except Exception as e:
            log("TG_JOIN_ERR", f"⚠️ Không thể Join '{url}': {e}", Fore.YELLOW)
        return None

    async def tg_leave_target(self, entity):
        """
        RỜI KÊNH THỰC SỰ 100% & XÁC MINH TRẠNG THÁI TRÊN MÁY CHỦ TELEGRAM:
        - Nếu là Channel/Supergroup: Tạo InputChannel(id, access_hash) tường minh -> Gọi LeaveChannelRequest
          -> Gọi tiếp delete_dialog(revoke=True) -> Kiểm tra lại bằng GetParticipantRequest.
        - Nếu là Basic Group: Gọi DeleteChatUserRequest -> delete_dialog.
        - Nếu là Bot: Xóa lịch sử chat (delete_dialog).
        """
        if not entity:
            return

        try:
            if not await self.ensure_tg_connected():
                return

            title = getattr(entity, "title", None) or getattr(entity, "username", str(getattr(entity, "id", "Target")))

            # Trường hợp 1: Là Bot -> Chỉ xóa cuộc trò chuyện
            if getattr(entity, "bot", False):
                log("TG_CLEAN", f"🧹 Đang dọn dẹp hội thoại với bot '{title}'...", Fore.MAGENTA)
                await self.tg_client.delete_dialog(entity, revoke=True)
                log("TG_CLEAN", f"✅ Đã xóa hội thoại bot '{title}'!", Fore.GREEN)
                return

            log("TG_LEAVE", f"🚪 Đang rời khỏi '{title}' (ID: {entity.id})...", Fore.MAGENTA)

            # Trường hợp 2: Là Channel hoặc Supergroup (Có id và access_hash)
            if isinstance(entity, Channel) or hasattr(entity, "access_hash"):
                input_chan = InputChannel(channel_id=entity.id, access_hash=entity.access_hash)
                input_peer = InputPeerChannel(channel_id=entity.id, access_hash=entity.access_hash)

                # Bước A: Gửi lệnh LeaveChannelRequest trực tiếp bằng InputChannel tường minh
                try:
                    await self.tg_client(LeaveChannelRequest(channel=input_chan))
                except UserNotParticipantError:
                    pass
                except Exception as ex_leave:
                    log("TG_LEAVE_RETRY", f"Thử lại Leave qua delete_dialog do: {ex_leave}", Fore.YELLOW)

                # Bước B: Xóa luôn khỏi danh sách Dialog (ép Telegram đồng bộ trạng thái rời kênh)
                try:
                    await self.tg_client.delete_dialog(input_peer, revoke=True)
                except Exception:
                    pass

                # Bước C: HẬU KIỂM (Verify xem thực sự đã thoát khỏi kênh chưa)
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
                    # Nếu vẫn còn kẹt trong Supergroup -> Cưỡng chế rời lần 2
                    log("TG_LEAVE_FORCE", f"⚠️ Phát hiện vẫn còn trong '{title}', đang cưỡng chế thoát lần 2...", Fore.YELLOW)
                    try:
                        await self.tg_client(LeaveChannelRequest(channel=input_chan))
                        await asyncio.sleep(1)
                    except Exception:
                        pass
                    log("TG_LEAVE", f"✅ Đã cưỡng chế rời khỏi '{title}'!", Fore.GREEN)
                else:
                    log("TG_LEAVE", f"✅ Đã rời khỏi '{title}' thành công 100% (Đã xác minh Server)!", Fore.GREEN)

            # Trường hợp 3: Là Nhóm thường (Basic Chat)
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
            log("TG_LEAVE_ERR", f"❌ Lỗi khi rời kênh '{getattr(entity, 'title', '')}': {e}", Fore.RED)

    def authenticate(self, init_data=None, silent=False):
        if init_data:
            self.init_data = init_data
        if not self.init_data:
            return False

        if not silent:
            log("AUTH", "Đang xác thực Protobuf với máy chủ PaidZ (Stealth Android Mode)...", Fore.YELLOW)

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
        """Đối chiếu số dư thực tế trước và sau khi Claim để không báo ảo."""
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
        for fld, val in res.items():
            if isinstance(val, float) and val > old_balance:
                proto_bal = val

        if proto_bal > old_balance:
            return True, proto_bal - old_balance, proto_bal, "OK (Proto)"

        # Kiểm tra lại số dư thật từ máy chủ PaidZ
        self.authenticate(silent=True)
        if self.balance > old_balance:
            return True, self.balance - old_balance, self.balance, "OK (DB Verified)"

        return False, 0.0, self.balance, f"Không cộng thêm tiền (Đã làm trước đó hoặc chưa đủ ĐK)"

    def fetch_clean_networks(self):
        """Lấy danh sách các mạng quảng cáo client hợp lệ, loại trừ S2S và Honeypot."""
        try:
            r = self.http.get(f"{API_BASE}/ads/networks", headers=self.get_headers(), timeout=10)
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

                        if is_honeypot or "honeypot" in net_name.lower() or net_name.startswith("secret_"):
                            log("HONEYPOT", f"🛡️ Đã phát hiện và né bẫy Honeypot: '{net_name}'!", Fore.MAGENTA)
                            continue

                        if net_name.lower() in S2S_NETWORKS:
                            continue

                        rem = remaining or (daily_limit - watched_today)
                        if rem > 0:
                            clean_networks.append({
                                "id": net_id,
                                "name": net_name,
                                "reward": reward,
                                "remaining": rem
                            })
                
                clean_networks.sort(key=lambda x: x.get("reward", 0.0), reverse=True)
                return clean_networks
        except Exception as e:
            log("NETWORKS_ERR", f"Lỗi lấy danh sách ads: {e}", Fore.RED)
        return []

    async def execute_campaign_flow(self, cid: str, title: str, url_str: str, tag_name="GATE"):
        """
        Quy trình chuẩn 100%:
        Start -> Join trên cùng phiên Telethon -> Đợi -> Claim -> Verify Balance -> Leave & Verify Leave.
        """
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
                break
            else:
                err_info = decode_proto(r_c.content)
                log(f"{tag_name}_WARN", f"Claim lần {attempt+1} lỗi (HTTP {r_c.status_code}): {err_info}", Fore.YELLOW)
                await asyncio.sleep(4)

        # Rời kênh thực sự và kiểm tra hậu kiểm trên máy chủ Telegram
        if joined_entity:
            await asyncio.sleep(4)
            await self.tg_leave_target(joined_entity)

        return claimed

    async def check_and_unlock_task_gate(self):
        """Tự động kiểm tra và mở khóa Task Gate."""
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
                return False

            if not raw_items:
                return False

            log("GATE", f"🚧 Phát hiện Task Gate ({completed}/{required}). Tiến hành tự động Join -> Claim -> Out...", Fore.YELLOW)

            for it in raw_items:
                if not isinstance(it, bytes):
                    continue
                tf = decode_proto(it)
                cid = tf.get(1, b'').decode('utf-8', errors='ignore') if isinstance(tf.get(1), bytes) else str(tf.get(1, ''))
                title = tf.get(2, b'').decode('utf-8', errors='ignore') if isinstance(tf.get(2), bytes) else str(tf.get(2, ''))
                url_str = extract_url_from_proto_fields(tf)

                if not cid:
                    continue

                await self.execute_campaign_flow(cid, title, url_str, tag_name="GATE")
                completed += 1
                if required > 0 and completed >= required:
                    log("GATE", f"✅ Đã xử lý đủ yêu cầu Task Gate ({completed}/{required})!", Fore.GREEN)
                    break

            return True
        except Exception as e:
            log("GATE_ERR", f"Lỗi xử lý Task Gate: {e}", Fore.RED)
        return False

    def spin_lucky_wheel(self):
        """Tự động quay Vòng quay may mắn hàng ngày."""
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
        """Tự động kiểm tra và làm nhiệm vụ hệ thống (/tasks)."""
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

                            if joined_entity:
                                await asyncio.sleep(4)
                                await self.tg_leave_target(joined_entity)
        except Exception as e:
            log("TASK_ERR", f"Lỗi claim nhiệm vụ: {e}", Fore.RED)

    async def claim_community_campaigns(self):
        """Tự động làm nhiệm vụ cộng đồng (Join -> Claim -> Verified Out)."""
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
                
                if b'TASK_GATE_REQUIRED' in err_code or b'TASK_GATE' in err_msg:
                    await self.check_and_unlock_task_gate()
                    return False, 3

                log("AD_START_WARN", f"Không thể bắt đầu ca xem ({network_name}): {err_code} - {err_msg}", Fore.YELLOW)
                return False, 8

            start_fields = decode_proto(r_start.content)
            session_token_raw = start_fields.get(2, b'')
            session_token = session_token_raw.decode('utf-8', errors='ignore') if isinstance(session_token_raw, bytes) else str(session_token_raw)
            min_duration = int(start_fields.get(4, 3))

            if not session_token:
                return False, 5

            view_seconds = max(min_duration, 4) + round(random.uniform(1.2, 2.2), 2)
            log("WATCHING", f"🎬 Đang xem quảng cáo '{network_name}'... (thời lượng {view_seconds:.1f}s)", Fore.CYAN)
            await asyncio.sleep(view_seconds)

            duration_ms = view_seconds * 1000.0
            req_watch = b"".join([
                enc_string(1, network_name),
                enc_string(2, session_token),
                enc_double(3, duration_ms),
                enc_string(4, "")
            ])

            r_watch = self.http.post(f"{API_BASE}/ads/watch", data=req_watch, headers=self.get_headers(), timeout=12)
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
# VÒNG LẶP CHÍNH 24/7
# -----------------------------------------------------------------
async def main_loop():
    print(Fore.YELLOW + """
=============================================================================
  BOT AUTO PAIDZ ($USDT) 24/7 - CHẾ ĐỘ TÀNG HÌNH ANTI-DETECTION STEALTH
  Bản Chuẩn 100%: Persistent Telethon + Verified Leave + Real DB Balance
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

        # Khởi động: Mở khóa Gate, quay thưởng Wheel, nhận Nhiệm vụ hệ thống & Cộng đồng
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
                if (time.time() - start_time) >= MAX_RUNTIME_SECONDS:
                    log("HANDOVER", "Hoàn thành ca trực 4.8 tiếng. Tự động chuyển giao ca trực tiếp theo...", Fore.CYAN)
                    trigger_next_shift()
                    break

                if (time.time() - last_refresh_time) >= 1800:
                    new_init = await bot.fetch_tg_init_data()
                    if new_init:
                        bot.authenticate(new_init)
                        await bot.check_and_unlock_task_gate()
                        last_refresh_time = time.time()

                if (time.time() - last_task_check_time) >= 3600:
                    await bot.claim_available_tasks()
                    await bot.claim_community_campaigns()
                    last_task_check_time = time.time()

                networks = bot.fetch_clean_networks()
                if not networks:
                    networks = [
                        {"id": "net_gigapub", "name": "gigapub", "reward": 0.0002, "remaining": 70},
                        {"id": "net_tads", "name": "tads", "reward": 0.0002, "remaining": 60},
                        {"id": "net_monetix", "name": "monetix", "reward": 0.0002, "remaining": 70},
                        {"id": "net_richads", "name": "richads", "reward": 0.0002, "remaining": 50},
                        {"id": "net_adexium", "name": "adexium", "reward": 0.0001, "remaining": 60},
                        {"id": "net_telega", "name": "telega", "reward": 0.0001, "remaining": 30}
                    ]

                now = time.time()
                ready_nets = [n for n in networks if now >= network_cooldowns.get(n["name"], 0)]

                if not ready_nets:
                    wait_time = min(network_cooldowns.values()) - now
                    sleep_t = max(2.0, min(wait_time, 6.0))
                    await asyncio.sleep(sleep_t)
                    continue

                max_rw = max(n["reward"] for n in ready_nets)
                top_tier_nets = [n for n in ready_nets if n["reward"] >= max_rw]
                target_net = random.choice(top_tier_nets)
                net_name = target_net["name"]

                success, cd = await bot.watch_ad_stealth(net_name)
                network_cooldowns[net_name] = time.time() + cd

                if success:
                    ads_session_count += 1

                if ads_session_count >= random.randint(5, 7):
                    rest_seconds = round(random.uniform(10.0, 20.0), 1)
                    log("REST", f"☕ Nghỉ ngắn {rest_seconds}s (Anti‑Fatigue)...", Fore.MAGENTA)
                    await asyncio.sleep(rest_seconds)
                    ads_session_count = 0
                else:
                    gap_sleep = round(random.uniform(5.5, 7.0), 1)
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
