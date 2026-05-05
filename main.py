"""
i2OCR-style desktop OCR app.

A Tkinter GUI that lets you pick an image or PDF, choose a language,
extract text with Tesseract, preview each page, and save the result.
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import ocr_engine


# Friendly names for the most common Tesseract language codes.
LANG_LABELS = {
    "eng": "English",
    "ara": "Arabic",
    "fra": "French",
    "spa": "Spanish",
    "deu": "German",
    "ita": "Italian",
    "por": "Portuguese",
    "rus": "Russian",
    "chi_sim": "Chinese (Simplified)",
    "chi_tra": "Chinese (Traditional)",
    "jpn": "Japanese",
    "kor": "Korean",
    "hin": "Hindi",
    "tur": "Turkish",
    "nld": "Dutch",
    "pol": "Polish",
    "ukr": "Ukrainian",
    "heb": "Hebrew",
    "fas": "Persian",
    "urd": "Urdu",
}


def pretty_lang(code: str) -> str:
    return f"{LANG_LABELS.get(code, code.title())} ({code})"


class OcrApp(tk.Tk):
    PREVIEW_MAX = (520, 700)

    def __init__(self):
        super().__init__()
        self.title("Python OCR  -  i2OCR-style desktop client")
        self.geometry("1180x720")
        self.minsize(900, 600)

        self.current_file: str | None = None
        self.result: ocr_engine.OcrResult | None = None
        self.page_idx = 0
        self._preview_imgtk = None  # keep a reference so Tk doesn't GC the image

        self._build_ui()
        self._populate_languages()

    # ---------- UI construction ----------

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="Open image or PDF...", command=self.open_file).pack(side=tk.LEFT)

        ttk.Label(toolbar, text="  Language:").pack(side=tk.LEFT, padx=(12, 4))
        self.lang_var = tk.StringVar(value="eng")
        self.lang_combo = ttk.Combobox(toolbar, textvariable=self.lang_var, width=28, state="readonly")
        self.lang_combo.pack(side=tk.LEFT)

        self.run_btn = ttk.Button(toolbar, text="Extract text", command=self.run_ocr, state=tk.DISABLED)
        self.run_btn.pack(side=tk.LEFT, padx=(12, 0))

        self.save_btn = ttk.Button(toolbar, text="Save text...", command=self.save_text, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.copy_btn = ttk.Button(toolbar, text="Copy", command=self.copy_text, state=tk.DISABLED)
        self.copy_btn.pack(side=tk.LEFT, padx=(8, 0))

        # Status / progress on the right of the toolbar.
        self.progress = ttk.Progressbar(toolbar, mode="determinate", length=180)
        self.progress.pack(side=tk.RIGHT)
        self.status_var = tk.StringVar(value="Ready. Pick a file to begin.")
        ttk.Label(toolbar, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)

        # Main split: preview on the left, text on the right.
        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Preview side
        preview_frame = ttk.LabelFrame(body, text="Preview", padding=8)
        body.add(preview_frame, weight=1)

        self.preview_label = ttk.Label(preview_frame, anchor="center", text="(no file loaded)")
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        nav = ttk.Frame(preview_frame)
        nav.pack(fill=tk.X, pady=(8, 0))
        self.prev_btn = ttk.Button(nav, text="< Prev", command=self.prev_page, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT)
        self.page_var = tk.StringVar(value="Page 0 / 0")
        ttk.Label(nav, textvariable=self.page_var).pack(side=tk.LEFT, expand=True)
        self.next_btn = ttk.Button(nav, text="Next >", command=self.next_page, state=tk.DISABLED)
        self.next_btn.pack(side=tk.RIGHT)

        # Text side
        text_frame = ttk.LabelFrame(body, text="Extracted text", padding=8)
        body.add(text_frame, weight=2)

        self.text_box = tk.Text(text_frame, wrap=tk.WORD, font=("TkDefaultFont", 11), undo=True)
        self.text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_box.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_box.configure(yscrollcommand=scroll.set)

    def _populate_languages(self):
        codes = ocr_engine.list_languages()
        if not codes:
            codes = ["eng"]
        values = [pretty_lang(c) for c in codes]
        self.lang_combo["values"] = values
        self._lang_codes = codes
        # Default to English if present, else first.
        default_idx = codes.index("eng") if "eng" in codes else 0
        self.lang_combo.current(default_idx)

    def _selected_language(self) -> str:
        idx = self.lang_combo.current()
        if idx < 0:
            return "eng"
        return self._lang_codes[idx]

    # ---------- File handling ----------

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Choose an image or PDF",
            filetypes=[
                ("Images and PDFs", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.gif *.webp *.pdf"),
                ("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.gif *.webp"),
                ("PDF", "*.pdf"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        if not ocr_engine.is_supported(path):
            messagebox.showerror("Unsupported file", f"Cannot OCR this file type:\n{path}")
            return
        self.current_file = path
        self.result = None
        self.page_idx = 0
        self.text_box.delete("1.0", tk.END)
        self.run_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.page_var.set("Page 0 / 0")
        self.status_var.set(f"Loaded: {Path(path).name}")
        self._show_file_thumbnail(path)

    def _show_file_thumbnail(self, path: str):
        """Cheap preview before OCR is run."""
        try:
            if ocr_engine.is_pdf(path):
                # Render first page only as a teaser.
                first = next(ocr_engine._render_pdf_pages(path, dpi=120), None)
                img = first if first else None
            else:
                img = Image.open(path)
            if img is not None:
                self._set_preview_image(img)
        except Exception as e:
            self.preview_label.config(image="", text=f"(preview failed: {e})")

    def _set_preview_image(self, pil_img: Image.Image):
        img = pil_img.copy()
        img.thumbnail(self.PREVIEW_MAX, Image.LANCZOS)
        self._preview_imgtk = ImageTk.PhotoImage(img)
        self.preview_label.config(image=self._preview_imgtk, text="")

    # ---------- OCR run ----------

    def run_ocr(self):
        if not self.current_file:
            return
        lang = self._selected_language()
        self.run_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.status_var.set(f"Running OCR ({lang})...")
        self.progress.config(value=0, maximum=100)

        def worker():
            try:
                def progress(cur, total):
                    pct = int(cur / total * 100) if total else 100
                    self.after(0, lambda: self._on_progress(cur, total, pct))

                result = ocr_engine.run_ocr(self.current_file, language=lang, progress_callback=progress)
                self.after(0, lambda: self._on_done(result))
            except Exception as e:
                self.after(0, lambda: self._on_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, cur, total, pct):
        self.progress.config(value=pct)
        self.status_var.set(f"OCR page {cur} / {total}")

    def _on_done(self, result: ocr_engine.OcrResult):
        self.result = result
        self.page_idx = 0
        self.progress.config(value=100)
        self.status_var.set(f"Done. {len(result.pages)} page(s) processed.")
        self.run_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        self.copy_btn.config(state=tk.NORMAL)
        self._refresh_page_view()

    def _on_error(self, err: Exception):
        self.progress.config(value=0)
        self.status_var.set("Error")
        self.run_btn.config(state=tk.NORMAL)
        messagebox.showerror("OCR failed", str(err))

    # ---------- Page navigation ----------

    def _refresh_page_view(self):
        if not self.result:
            return
        total = len(self.result.pages)
        page = self.result.pages[self.page_idx]
        self._set_preview_image(page.image)
        self.text_box.delete("1.0", tk.END)
        # Show ALL pages joined in the text panel; navigation just scrolls preview.
        self.text_box.insert("1.0", self.result.full_text)
        self.page_var.set(f"Page {self.page_idx + 1} / {total}")
        self.prev_btn.config(state=tk.NORMAL if self.page_idx > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.page_idx + 1 < total else tk.DISABLED)

    def prev_page(self):
        if self.result and self.page_idx > 0:
            self.page_idx -= 1
            self._refresh_page_view()

    def next_page(self):
        if self.result and self.page_idx + 1 < len(self.result.pages):
            self.page_idx += 1
            self._refresh_page_view()

    # ---------- Output ----------

    def save_text(self):
        if not self.result:
            return
        default = Path(self.result.source_path).stem + ".txt"
        out = filedialog.asksaveasfilename(
            title="Save extracted text",
            defaultextension=".txt",
            initialfile=default,
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        )
        if not out:
            return
        Path(out).write_text(self.result.full_text, encoding="utf-8")
        self.status_var.set(f"Saved to {out}")

    def copy_text(self):
        if not self.result:
            return
        self.clipboard_clear()
        self.clipboard_append(self.result.full_text)
        self.status_var.set("Copied to clipboard.")


def main():
    app = OcrApp()
    app.mainloop()


if __name__ == "__main__":
    main()
