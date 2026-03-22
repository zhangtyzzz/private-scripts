# PixPin OCR 截图脚本 (macOS)

截图后 OCR，将结果写入剪贴板。

## 安装依赖

```bash
pip3 install requests pillow
```

## PixPin 配置

打开 PixPin → 设置 → 快捷键/动作 → 添加新动作

| 字段 | 值 |
|------|-----|
| 名称 | 截图OCR |
| 快捷键 | 自定义 |
| 脚本 | 见下方 |

```
pixpin.screenShot(ShotAction.Copy)
pixpin.runSystem("python3 <脚本目录>/pixpin/pixpin_ocr_macos.py")
```

> 将 `<脚本目录>` 替换为实际路径，如 `/Volumes/Data/agents/agent-scripts`

## 配置文件

在 `pixpin` 目录下创建 `pixpin_ocr.env` 文件：

```ini
# 调试开关
DEBUG=false

# PaddleOCR-VL-1.5
VL_API_URL=https://xxx.aistudio-app.com/layout-parsing
VL_TOKEN=your_token_here
VL_TIMEOUT=15

# PP-StructureV3
STRUCTURE_API_URL=https://xxx.aistudio-app.com/layout-parsing
STRUCTURE_TOKEN=your_token_here
STRUCTURE_TIMEOUT=8

# 百度 OCR
BAIDU_API_KEY=your_api_key
BAIDU_SECRET_KEY=your_secret_key
BAIDU_TIMEOUT=3
```

## 特性

- **三级降级**：PaddleOCR-VL-1.5 (15s) → PP-StructureV3 (8s) → 百度 OCR (3s)
- **JPG 压缩**：自动压缩图片加速传输
- **容错保底**：先写入图片，OCR 成功再覆盖文本

## 文件

| 文件 | 说明 |
|------|------|
| `pixpin_ocr_macos.py` | 主脚本 |
| `pixpin_ocr.env` | 配置文件（需自行创建） |
