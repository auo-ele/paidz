# -*- coding: utf-8 -*-
"""
human_behavior.py - Module Giả Lập Hành Vi Con Người & Chống Ban 100%
Áp dụng cho toàn bộ 4 trò chơi: Gramstone, HashLane, REDRIG, Eggram.

1. GIỜ NGỦ TỰ NHIÊN (Circadian Rhythm):
   - Ngủ hoàn toàn từ 00:30 đến 05:15 sáng (Giờ VN - UTC+7).
   - Tự động ngắt kết nối và không gửi bất kỳ request nào trong đêm.
   - Khi thức dậy (sau 05:15), tự động bắt đầu chu kỳ ngày mới.

2. PHIÊN CHƠI NGẪU NHIÊN (Session Burst & Natural Breaks):
   - Phiên chơi hoạt động kéo dài 20 - 30 phút.
   - Sau mỗi phiên chơi, đóng app và nghỉ ngơi tự nhiên 5 - 8 phút.
   - Tạo biểu đồ hoạt động (activity curve) hoàn toàn giống người thật.

3. VÂN TAY THIẾT BỊ ĐỘC LẬP (Device Fingerprint Isolation):
   - Acc 1: Samsung Galaxy S24 Ultra (Android 14, Snapdragon 8 Gen 3, DPR 3.5)
   - Acc 2: Xiaomi 13 Pro (Android 14, Snapdragon 8 Gen 2, DPR 3.0)
   - Acc 3: Google Pixel 8 Pro (Android 14, Tensor G3, DPR 2.625)

4. BIOMETRIC TAP SIMULATION (Chống cờ Auto-Clicker):
   - Không gõ spam nhanh. Mỗi tap cách nhau 1.8s - 3.8s (Gaussian Jitter).
   - Có tọa độ chạm elip (X, Y) và khoảng nghỉ vi mô (Micro-pauses).
"""

import time
import random
import hashlib
import asyncio
from datetime import datetime, timezone, timedelta

VN_TZ = timezone(timedelta(hours=7))

# -------------------------------------------------------------
# 1. PROFILE THIẾT BỊ PHẦN CỨNG ĐỘC LẬP CHO TỪNG ACC
# -------------------------------------------------------------
DEVICE_PROFILES = {
    1: {
        "device_name": "Samsung Galaxy S24 Ultra",
        "model": "SM-S928B",
        "ua": (
            "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.135 "
            "Mobile Safari/537.36 Telegram-Android/11.5.0 (Samsung SM-S928B; Android 14; SDK 34; HIGH)"
        ),
        "platform": "Linux aarch64",
        "screen": "412x915x24",
        "dpr": "3.5",
        "cores": "8",
        "ram": "12",
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 750",
    },
    2: {
        "device_name": "Xiaomi 13 Pro",
        "model": "2210132C",
        "ua": (
            "Mozilla/5.0 (Linux; Android 14; 2210132C Build/UKQ1.230804.001; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.107 "
            "Mobile Safari/537.36 Telegram-Android/11.5.0 (Xiaomi 2210132C; Android 14; SDK 34; HIGH)"
        ),
        "platform": "Linux armv8l",
        "screen": "393x873x24",
        "dpr": "3.0",
        "cores": "8",
        "ram": "8",
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 740",
    },
    3: {
        "device_name": "Google Pixel 8 Pro",
        "model": "Pixel 8 Pro",
        "ua": (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/UD1A.231105.004; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.6668.100 "
            "Mobile Safari/537.36 Telegram-Android/11.5.0 (Google Pixel 8 Pro; Android 14; SDK 34; HIGH)"
        ),
        "platform": "Linux aarch64",
        "screen": "412x892x24",
        "dpr": "2.625",
        "cores": "8",
        "ram": "12",
        "webgl_vendor": "Google Inc. (ARM)",
        "webgl_renderer": "Mali-G715 Immortalis MC10",
    }
}


def get_device_profile(acc_id: int):
    """Lấy cấu hình thiết bị riêng biệt theo acc_id (1, 2 hoặc 3)"""
    return DEVICE_PROFILES.get(int(acc_id), DEVICE_PROFILES[1])


def get_hashlane_device_fp(acc_id: int):
    """Tạo mã băm X-Device riêng biệt chuẩn HashLane frontend"""
    p = get_device_profile(acc_id)
    parts = [
        p["ua"],
        "vi-VN",
        p["screen"],
        p["dpr"],
        "Asia/Ho_Chi_Minh",
        p["cores"],
        p["ram"],
        p["platform"],
        "android"
    ]
    return hashlib.sha256("|".join(parts).encode('utf-8')).hexdigest()


def get_gramstone_fp(acc_id: int):
    """Tạo mã băm x-gs-fp riêng biệt chuẩn Gramstone"""
    p = get_device_profile(acc_id)
    raw = f"{p['model']}|{p['screen']}|{p['dpr']}|{p['webgl_renderer']}|acc_{acc_id}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def get_moonpool_device_payload(acc_id: int, app_name: str = "Eggram"):
    """
    Tạo payload đăng ký thiết bị chuẩn /api/device cho Eggram và REDRIG.
    Khớp 100% thuật toán fp.js của Moonpool Engine (SHA-256 32-char + summary).
    """
    p = get_device_profile(acc_id)
    screen_wh = p["screen"].split("x")[:2]
    screen_str = f"{screen_wh[0]}x{screen_wh[1]}"
    
    summary = {
        "tg_platform": "android",
        "tg_version": "11.5.0",
        "platform": p["platform"],
        "screen": screen_str,
        "dpr": float(p["dpr"]),
        "color_depth": 24,
        "tz": "Asia/Ho_Chi_Minh",
        "langs": "vi-VN,vi,en-US,en",
        "cores": int(p["cores"]),
        "memory": int(p["ram"]),
        "touch": 5,
        "gpu_vendor": p["webgl_vendor"],
        "gpu_renderer": p["webgl_renderer"]
    }
    
    canvas_sig_raw = f"{app_name}|canvasSig|{p['model']}|{p['webgl_renderer']}|acc_{acc_id}"
    canvas_hash = hashlib.sha256(canvas_sig_raw.encode("utf-8")).hexdigest()
    
    raw_traits = [
        str(summary["tg_platform"]),
        str(summary["tg_version"]),
        str(summary["platform"]),
        str(summary["screen"]),
        str(summary["dpr"]),
        str(summary["color_depth"]),
        str(summary["tz"]),
        str(summary["langs"]),
        str(summary["cores"]),
        str(summary["memory"]),
        str(summary["touch"]),
        str(summary["gpu_vendor"]),
        str(summary["gpu_renderer"]),
        canvas_hash
    ]
    raw_str = "|".join(raw_traits)
    fp = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:32]
    
    return {"fp": fp, "summary": summary}


def report_device_to_server(api_base: str, init_data: str, acc_id: int, app_name: str = "Eggram"):
    """
    Gửi báo cáo vân tay thiết bị lên /api/device như client web thật (reportDevice trong fp.js)
    """
    try:
        import requests
        dev = get_device_profile(acc_id)
        payload = get_moonpool_device_payload(acc_id, app_name)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": dev["ua"],
            "X-Telegram-Init-Data": init_data,
            "Origin": api_base,
            "Referer": f"{api_base}/"
        }
        res = requests.post(f"{api_base}/api/device", headers=headers, json=payload, timeout=10)
        if res.status_code == 200:
            return True, payload["fp"]
        return False, f"HTTP {res.status_code}"
    except Exception as e:
        return False, str(e)



# -------------------------------------------------------------
# 2. GIỜ NGỦ TỰ NHIÊN (00:30 - 05:15 SÁNG GIỜ VN)
# -------------------------------------------------------------
SLEEP_START_MIN = 30    # 00:30 VN
SLEEP_END_MIN = 315     # 05:15 VN


def get_vn_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam (UTC+7)"""
    return datetime.now(VN_TZ)


def check_sleep_window():
    """
    Kiểm tra xem hiện tại có nằm trong Giờ Ngủ Tự Nhiên (00:30 - 05:15 VN) không.
    Trả về (is_sleeping: bool, seconds_left: int)
    """
    now = get_vn_time()
    curr_min = now.hour * 60 + now.minute
    
    if SLEEP_START_MIN <= curr_min < SLEEP_END_MIN:
        wake_min = SLEEP_END_MIN
        minutes_left = wake_min - curr_min
        seconds_left = minutes_left * 60 - now.second + random.randint(30, 480)
        return True, max(60, seconds_left)
    return False, 0


async def handle_sleep_schedule_async(log_func=print):
    """Kiểm tra và thực hiện ngủ ban đêm (async)"""
    in_sleep, sec_left = check_sleep_window()
    if in_sleep:
        wake_time_str = (get_vn_time() + timedelta(seconds=sec_left)).strftime("%H:%M:%S")
        log_func(f"🌙 [GIỜ NGỦ TỰ NHIÊN] Hiện là ban đêm (00:30 - 05:15 VN). Bot tạm dừng mọi hoạt động cày/tap để bảo vệ tài khoản.")
        log_func(f"💤 Đang ngủ tự nhiên {sec_left/3600:.2f} tiếng... Dự kiến thức dậy lúc {wake_time_str} VN.")
        
        while sec_left > 0:
            step = min(sec_left, 1800)  # Cập nhật log mỗi 30 phút
            await asyncio.sleep(step)
            sec_left -= step
            if sec_left > 0:
                log_func(f"💤 [SLEEP HEARTBEAT] Đang nghỉ ngơi... Còn {sec_left/3600:.2f} tiếng trước ca sáng 05:15.")
        
        log_func("☀️ [THỨC DẬY] Đã qua giờ ngủ tự nhiên! Bot bắt đầu ca cày ngày mới...")
        return True
    return False


def handle_sleep_schedule_sync(log_func=print):
    """Kiểm tra và thực hiện ngủ ban đêm (sync)"""
    in_sleep, sec_left = check_sleep_window()
    if in_sleep:
        wake_time_str = (get_vn_time() + timedelta(seconds=sec_left)).strftime("%H:%M:%S")
        log_func(f"🌙 [GIỜ NGỦ TỰ NHIÊN] Hiện là ban đêm (00:30 - 05:15 VN). Bot tạm dừng mọi hoạt động cày/tap để bảo vệ tài khoản.")
        log_func(f"💤 Đang ngủ tự nhiên {sec_left/3600:.2f} tiếng... Dự kiến thức dậy lúc {wake_time_str} VN.")
        
        while sec_left > 0:
            step = min(sec_left, 1800)
            time.sleep(step)
            sec_left -= step
            if sec_left > 0:
                log_func(f"💤 [SLEEP HEARTBEAT] Đang nghỉ ngơi... Còn {sec_left/3600:.2f} tiếng trước ca sáng 05:15.")
        
        log_func("☀️ [THỨC DẬY] Đã qua giờ ngủ tự nhiên! Bot bắt đầu ca cày ngày mới...")
        return True
    return False


# -------------------------------------------------------------
# 3. QUẢN LÝ PHIÊN CHƠI NGẪU NHIÊN (SESSION BURST & BREAK)
# -------------------------------------------------------------
class SessionBurstManager:
    """
    Quản lý phiên chơi ngẫu nhiên:
    - Phiên hoạt động: 20 - 30 phút.
    - Nghỉ giải lao tự nhiên: 5 - 8 phút.
    """
    def __init__(self, burst_min_mins=20, burst_max_mins=30, break_min_mins=5, break_max_mins=8):
        self.burst_min = burst_min_mins * 60
        self.burst_max = burst_max_mins * 60
        self.break_min = break_min_mins * 60
        self.break_max = break_max_mins * 60
        
        self.session_start = time.time()
        self.session_target_duration = random.randint(self.burst_min, self.burst_max)
        self.burst_count = 1

    def is_burst_finished(self):
        """Kiểm tra xem phiên chơi hiện tại đã hoàn thành chưa"""
        return (time.time() - self.session_start) >= self.session_target_duration

    def get_break_duration(self):
        """Lấy thời lượng nghỉ giải lao ngẫu nhiên (giây)"""
        return random.randint(self.break_min, self.break_max)

    def start_new_burst(self):
        """Bắt đầu một phiên chơi mới sau giờ nghỉ"""
        self.session_start = time.time()
        self.session_target_duration = random.randint(self.burst_min, self.burst_max)
        self.burst_count += 1


# -------------------------------------------------------------
# 4. MICRO-TAP ANTI-AUTOCLICKER (GRAMSTONE)
# -------------------------------------------------------------
def get_human_tap_delay():
    """Tạo độ trễ gõ màn hình ngẫu nhiên chuẩn Gauss 1.8s - 3.8s"""
    delay = random.gauss(2.5, 0.45)
    return round(max(1.8, min(3.8, delay)), 3)


def get_human_touch_coords():
    """Tạo tọa độ ngón tay cái chạm màn hình dao động tự nhiên theo hình elip"""
    center_x = 540
    center_y = 1520
    radius_x = 90
    radius_y = 120
    
    offset_x = random.gauss(0, radius_x / 2.5)
    offset_y = random.gauss(0, radius_y / 2.5)
    
    return {
        "x": int(center_x + offset_x),
        "y": int(center_y + offset_y),
        "hold_duration_ms": random.randint(75, 135)
    }
