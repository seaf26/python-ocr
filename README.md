# Python OCR Desktop App

A Tkinter-based desktop OCR application inspired by i2OCR. Extract text from images and multi-page PDFs using Tesseract, with a live preview and easy export.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

- Open images (PNG, JPG, BMP, TIFF, GIF, WEBP) or multi-page PDFs
- 20+ language support via Tesseract (English, Arabic, French, Chinese, Japanese, and more)
- Live page preview with previous/next navigation
- Progress bar during OCR processing (runs in a background thread)
- Save extracted text to `.txt` or copy to clipboard

## Screenshots

| Load & Preview | After OCR |
|---|---|
| Open a file → preview appears instantly | Click "Extract text" → text appears on the right |

## Requirements

- **Python 3.10+**
- **Tesseract OCR** installed on your system
- Python packages: `pytesseract`, `Pillow`, `PyMuPDF`

## Installation

### 1. Install Tesseract

**macOS (Homebrew):**
```bash
brew install tesseract
```

**Ubuntu / Debian:**
```bash
sudo apt install tesseract-ocr
```

**Windows:**
Download the installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), then set the path:
```bash
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 2. Install additional Tesseract language packs (optional)

**macOS — installs all languages at once:**
```bash
brew install tesseract-lang
```

> **macOS note:** Do NOT use `apt` — that is a Linux-only package manager. On macOS always use `brew`.

**Ubuntu / Debian:**
```bash
sudo apt install tesseract-ocr-ara tesseract-ocr-fra  # add languages as needed
```

### 3. Install Python dependencies

```bash
pip3 install -r requirements.txt
```

> **macOS note:** Use `pip3` (not `pip`) — on macOS `pip` is often not found. If `pip3` also fails, use `python3 -m pip install -r requirements.txt`.

## Usage

```bash
python3 main.py
```

1. Click **"Open image or PDF..."** and select a file
2. Choose a language from the dropdown (defaults to English)
3. Click **"Extract text"**
4. Use **"Save text..."** to export as `.txt` or **"Copy"** to copy to clipboard

### Custom Tesseract path (Windows / non-standard installs)

Set the `TESSERACT_CMD` environment variable before running:

```bash
TESSERACT_CMD=/usr/local/bin/tesseract python3 main.py
```

## Project Structure

```
python-ocr/
├── main.py          # Tkinter GUI application
├── ocr_engine.py    # OCR logic (Tesseract wrapper + PDF rendering)
├── requirements.txt
├── sample.pdf       # 3-page test PDF
└── sample_image.png # Test image
```

## Dependencies

| Package | Purpose |
|---|---|
| `pytesseract` | Python wrapper for Tesseract OCR |
| `Pillow` | Image loading and preview rendering |
| `PyMuPDF` | PDF page rasterization (no Poppler needed) |

## Known Issues

- On macOS 15+ with Homebrew Python 3.12, there may be a `libexpat` symbol mismatch. Use Python 3.14+ from python.org as a workaround.
- Only languages installed in your local Tesseract data directory are available.

## License

MIT
