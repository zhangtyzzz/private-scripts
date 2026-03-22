"""
PixPin OCR Screenshot - macOS 版
三级降级：PaddleOCR-VL-1.5 → PP-StructureV3 → 百度 OCR

PixPin 配置：
pixpin.screenShot(ShotAction.Copy)
pixpin.runSystem("python3 /Volumes/Data/agents/agent-scripts/pixpin_ocr_macos.py")
"""

import base64
import io
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# 读取配置文件
def load_config():
    """从 pixpin_ocr.env 读取配置"""
    config_path = Path(__file__).parent / "pixpin_ocr.env"
    config = {}

    if config_path.exists():
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

    return config

_config = load_config()

# ============ 配置 ============
DEBUG = _config.get('DEBUG', 'false').lower() == 'true'

# PaddleOCR-VL-1.5 (最强效果)
VL_API_URL = _config.get('VL_API_URL', "")
VL_TOKEN = _config.get('VL_TOKEN', "")
VL_TIMEOUT = int(_config.get('VL_TIMEOUT', 15))

# PP-StructureV3 (快速降级)
STRUCTURE_API_URL = _config.get('STRUCTURE_API_URL', "")
STRUCTURE_TOKEN = _config.get('STRUCTURE_TOKEN', "")
STRUCTURE_TIMEOUT = int(_config.get('STRUCTURE_TIMEOUT', 8))

# 百度 OCR (最终保底)
BAIDU_API_KEY = _config.get('BAIDU_API_KEY', "")
BAIDU_SECRET_KEY = _config.get('BAIDU_SECRET_KEY', "")
BAIDU_TIMEOUT = int(_config.get('BAIDU_TIMEOUT', 3))
# ================================


def get_clipboard_image():
    """从剪贴板获取图片"""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()

        if img is None:
            return None, "剪贴板中没有图片"

        if isinstance(img, list):
            for path in img:
                if Path(path).suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                    from PIL import Image
                    return Image.open(path), None
            return None, "剪贴板中没有支持的图片格式"

        return img, None
    except Exception as e:
        return None, f"获取剪贴板失败: {e}"


def image_to_base64(img, quality=85):
    """图片转 base64（使用 JPG 格式压缩）"""
    buffer = io.BytesIO()
    # 转为 RGB（JPG 不支持透明通道）
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    # 保存为 JPG，可指定质量
    img.save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def save_image_to_clipboard(img):
    """将图片写入剪贴板"""
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_path = f"{temp_dir}/pixpin_ocr_{timestamp}.png"
    img.save(img_path, "PNG")

    subprocess.run(['osascript', '-e', f'set the clipboard to (read POSIX file "{img_path}" as TIFF picture)'], capture_output=True)
    return img_path


def copy_text_to_clipboard(text):
    """将文本写入剪贴板"""
    if text:
        subprocess.run(['pbcopy'], input=text.encode('utf-8'))


def call_vl_ocr(image_base64):
    """调用 PaddleOCR-VL-1.5 API (最强效果，超时5s)"""
    import requests

    headers = {
        "Authorization": f"token {VL_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "file": image_base64,
        "fileType": 1,
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }

    try:
        response = requests.post(VL_API_URL, json=payload, headers=headers, timeout=VL_TIMEOUT)

        if response.status_code != 200:
            return None

        result = response.json().get("result", {})
        texts = []
        for res in result.get("layoutParsingResults", []):
            md_text = res.get("markdown", {}).get("text", "")
            if md_text:
                texts.append(md_text)

        text = "\n\n".join(texts)
        return text if text.strip() else None
    except:
        return None


def call_structure_ocr(image_base64):
    """调用 PP-StructureV3 API (快速降级，超时3s)"""
    import requests

    headers = {
        "Authorization": f"token {STRUCTURE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "file": image_base64,
        "fileType": 1,
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useTextlineOrientation": False,
        "useChartRecognition": False,
    }

    try:
        response = requests.post(STRUCTURE_API_URL, json=payload, headers=headers, timeout=STRUCTURE_TIMEOUT)

        if response.status_code != 200:
            return None

        result = response.json().get("result", {})
        texts = []
        for res in result.get("layoutParsingResults", []):
            md_text = res.get("markdown", {}).get("text", "")
            if md_text:
                texts.append(md_text)

        text = "\n\n".join(texts)
        return text if text.strip() else None
    except:
        return None


def call_baidu_ocr(image_base64):
    """调用百度 OCR API (最终保底，超时3s)"""
    import requests
    import urllib.parse

    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY
    }
    try:
        response = requests.post(url, params=params, timeout=BAIDU_TIMEOUT)
        access_token = response.json().get("access_token")
    except:
        return None

    if not access_token:
        return None

    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={access_token}"
    image_data = urllib.parse.quote_plus(image_base64)
    payload = f"image={image_data}&detect_direction=false&paragraph=false"

    try:
        response = requests.post(url, data=payload.encode("utf-8"), timeout=BAIDU_TIMEOUT)
        result = response.json()

        if "error_code" in result:
            return None

        words_result = result.get("words_result", [])
        if not words_result:
            return None

        texts = [item.get("words", "") for item in words_result]
        return "\n".join(texts)
    except:
        return None


def show_notification(title, message):
    """显示 macOS 通知 + 声音提示"""
    script = f'display notification "{message}" with title "{title}" sound name "Submarine"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def main():
    # 等待剪贴板有图片（最多等 3 秒）
    img = None
    for _ in range(6):
        img, error = get_clipboard_image()
        if img:
            break
        time.sleep(0.5)

    if not img:
        show_notification("OCR 失败", "剪贴板中没有图片")
        sys.exit(1)

    # 先写入图片到剪贴板（保底）
    save_image_to_clipboard(img)

    # OCR
    image_base64 = image_to_base64(img)

    # 1. 尝试 PaddleOCR-VL-1.5
    start = time.time()
    text = call_vl_ocr(image_base64)
    vl_time = time.time() - start
    source = "VL-1.5"

    # 2. 降级 PP-StructureV3
    if not text:
        start = time.time()
        text = call_structure_ocr(image_base64)
        struct_time = time.time() - start
        source = "PP-StructureV3"
    else:
        struct_time = 0

    # 3. 降级百度 OCR
    if not text:
        start = time.time()
        text = call_baidu_ocr(image_base64)
        baidu_time = time.time() - start
        source = "百度OCR"
    else:
        baidu_time = 0

    # 记录日志
    if DEBUG:
        with open("/tmp/pixpin_ocr.log", "a") as f:
            from datetime import datetime
            f.write(f"[{datetime.now()}] 图片尺寸: {img.size}, VL耗时: {vl_time:.1f}s, Struct耗时: {struct_time:.1f}s, 百度耗时: {baidu_time:.1f}s, 引擎: {source}, 字数: {len(text) if text else 0}\n")

    # 写入结果
    if text:
        copy_text_to_clipboard(text)
        show_notification("OCR 完成", f"({source}) {len(text)}字")
    else:
        show_notification("OCR 失败", "剪贴板保留图片")


if __name__ == "__main__":
    main()
