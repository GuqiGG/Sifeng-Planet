#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""司凤星球 · a compact Bilibili music-video listening desk."""

from __future__ import annotations

import html
import json
import math
import random
import re
import sys
import os
import ctypes
from ctypes import wintypes
import secrets
import threading
from datetime import datetime
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

KEYWORDS = ("司凤版", "司凤", "隆德齐")
API = "https://api.bilibili.com/x/web-interface/search/type"
PAGELIST_API = "https://api.bilibili.com/x/player/pagelist"
PLAYURL_API = "https://api.bilibili.com/x/player/playurl"


def clean_title(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def permitted(title: str, terms=KEYWORDS) -> bool:
    return any(word in title for word in terms)


def normalize_results(rows: list[dict], seen: set[str], terms=KEYWORDS) -> list[dict]:
    found = []
    for row in rows:
        title, bvid = clean_title(row.get("title", "")), str(row.get("bvid", ""))
        if not re.fullmatch(r"BV[0-9A-Za-z]+", bvid) or not permitted(title, terms) or bvid in seen:
            continue
        seen.add(bvid)
        found.append({
            "title": title,
            "bvid": bvid,
            "author": html.unescape(str(row.get("author") or "未知 UP 主")),
            "duration": str(row.get("duration") or ""),
            "pic": str(row.get("pic") or ""),
            "play": str(row.get("play") or ""),
        })
    return found


def next_index(current: int, count: int, repeat: bool) -> int:
    return current if repeat else ((current + 1) % count if count else -1)


def playback_next(current: int, count: int, mode: str, rng=None) -> int:
    if count <= 0:
        return -1
    if mode == "repeat":
        return current
    if mode == "random" and count > 1:
        choices = [i for i in range(count) if i != current]
        return (rng or random).choice(choices)
    return (current + 1) % count


def parse_terms(value: str) -> tuple[str, ...]:
    terms = tuple(dict.fromkeys(x.strip() for x in re.split(r"[,，、;；\n]+", value) if x.strip()))
    if not terms or len(terms) > 8 or any(len(x) > 24 for x in terms):
        raise ValueError("请输入 1–8 个搜索词，每个不超过 24 字")
    return terms


def hotkey_parts(sequence):
    if sequence.isEmpty():
        return None
    if sequence.count() != 1:
        raise ValueError("快捷键只支持一个组合")
    combo = sequence[0]
    key = int(combo.key())
    mods = combo.keyboardModifiers()
    if not (mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)):
        raise ValueError("快捷键需包含 Ctrl 或 Alt")
    if not (ord("A") <= key <= ord("Z") or ord("0") <= key <= ord("9")):
        raise ValueError("快捷键末键请用字母或数字")
    win_mods = 0x4000
    if mods & Qt.KeyboardModifier.AltModifier:
        win_mods |= 0x0001
    if mods & Qt.KeyboardModifier.ControlModifier:
        win_mods |= 0x0002
    if mods & Qt.KeyboardModifier.ShiftModifier:
        win_mods |= 0x0004
    return win_mods, key


def select_mp4(payload: dict) -> tuple[str, int]:
    if payload.get("code") != 0:
        raise ValueError(f"播放地址接口返回 {payload.get('code')}: {payload.get('message', '')}")
    data = payload.get("data") or {}
    durl = data.get("durl") or []
    if not durl or not str(durl[0].get("url", "")).startswith("https://"):
        raise ValueError("没有可播放的 MP4 地址")
    return durl[0]["url"], int(durl[0].get("size") or 0)


def self_test() -> None:
    assert clean_title('<em class="keyword">司凤</em>版 &amp; 音乐') == "司凤版 & 音乐"
    assert permitted("司凤版·现场") and permitted("隆德齐·音乐")
    assert not permitted("其他歌曲")
    seen: set[str] = set()
    rows = [
        {"title": "<em>司凤</em>版 歌曲", "bvid": "BV1abc"},
        {"title": "其他歌曲", "bvid": "BV2abc"},
        {"title": "司凤版 歌曲", "bvid": "BV1abc"},
    ]
    assert [x["bvid"] for x in normalize_results(rows, seen)] == ["BV1abc"]
    assert next_index(1, 3, False) == 2
    assert next_index(2, 3, False) == 0
    assert next_index(1, 3, True) == 1
    assert playback_next(1, 3, "repeat") == 1
    assert playback_next(2, 3, "continue") == 0
    assert playback_next(1, 3, "random", type("R", (), {"choice": lambda self, xs: xs[0]})()) == 0
    assert parse_terms("司凤、隆德齐，司凤") == ("司凤", "隆德齐")
    assert select_mp4({"code": 0, "data": {"durl": [{"url": "https://example.test/v.mp4", "size": 12}]}}) == ("https://example.test/v.mp4", 12)
    print("MODIFIED: onboarding settings, custom terms, random/repeat, MP4 selection PASS")


if "--self-test" in sys.argv:
    self_test()
    raise SystemExit(0)

import requests
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QUrl, QEvent, QVariantAnimation, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPen, QPalette, QKeySequence, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QKeySequenceEdit, QLineEdit, QMainWindow, QPushButton, QScrollArea, QSlider,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget, QMenu,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget


def app_icon() -> QIcon:
    saved = Path(__file__).with_name("sifeng_planet.ico")
    if saved.exists():
        return QIcon(str(saved))
    pix = QPixmap(128, 128)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(5, 5, 118, 118, 35, 35)
    p.setBrush(QColor("#f2f2f3"))
    p.drawEllipse(17, 16, 94, 94)
    p.setBrush(QColor("#111111"))
    p.drawEllipse(29, 28, 70, 70)
    p.setPen(QPen(QColor("#ffffff"), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(63, 34, 63, 76)
    p.drawEllipse(46, 73, 18, 16)
    p.end()
    return QIcon(pix)


def cover_url(pic: str) -> str:
    if pic.startswith("//"):
        return "https:" + pic
    return pic if pic.startswith("https://") else ""


@lru_cache(maxsize=1)
def placeholder_cover() -> QPixmap:
    pix = QPixmap(292, 164)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#f1f1f3"))
    painter.drawRoundedRect(0, 0, 292, 164, 14, 14)
    painter.setPen(QPen(QColor("#c3c4c9"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(154, 61, 154, 101)
    painter.drawLine(154, 61, 172, 57)
    painter.setBrush(QColor("#c3c4c9"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(131, 96, 24, 15)
    painter.end()
    return pix


class SearchWorker(QThread):
    batch = Signal(object)
    failed = Signal(str)

    def __init__(self, page: int, terms=KEYWORDS):
        super().__init__()
        self.page = page
        self.terms = tuple(terms)

    def run(self):
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://search.bilibili.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        seen: set[str] = set()
        try:
            # A homepage visit supplies ordinary anonymous session cookies.
            session.get("https://www.bilibili.com/", headers=headers, timeout=12)
            for keyword in self.terms:
                response = session.get(API, params={"search_type": "video", "keyword": keyword, "page": self.page}, headers=headers, timeout=12)
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") != 0:
                    raise RuntimeError(f"哔哩哔哩搜索返回 {payload.get('code')}: {payload.get('message', '')}")
                rows = (payload.get("data") or {}).get("result") or []
                items = normalize_results(rows, seen, self.terms)
                for item in items[:12]:
                    if self.isInterruptionRequested():
                        return
                    url = cover_url(item["pic"])
                    if url:
                        try:
                            image_response = session.get(url, headers=headers, timeout=5)
                            if image_response.ok and len(image_response.content) < 2_000_000:
                                item["image"] = image_response.content
                        except requests.RequestException:
                            pass
                self.batch.emit(items)
        except Exception as exc:
            self.failed.emit(str(exc))


class StreamSource:
    def __init__(self, bvid: str, url: str, size: int, cache_dir: Path):
        self.bvid, self.url, self.size = bvid, url, size
        self.final = cache_dir / f"{bvid}.mp4"
        self.partial = cache_dir / f"{bvid}.part"
        self.ranges = []
        self.lock = threading.Lock()

    def store(self, start: int, chunk: bytes):
        if not chunk or self.final.exists():
            return
        with self.lock:
            mode = "r+b" if self.partial.exists() else "w+b"
            with self.partial.open(mode) as output:
                output.seek(start)
                output.write(chunk)
            merged = []
            for first, last in sorted(self.ranges + [(start, start + len(chunk))]):
                if merged and first <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], last))
                else:
                    merged.append((first, last))
            self.ranges = merged
            if self.size and len(merged) == 1 and merged[0][0] == 0 and merged[0][1] >= self.size:
                try:
                    self.partial.replace(self.final)
                    self.prune_cache()
                except OSError:
                    pass

    def prune_cache(self):
        files = sorted(self.final.parent.glob("BV*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        total = 0
        for path in files:
            size = path.stat().st_size
            if path == self.final or total + size <= 150_000_000:
                total += size
            else:
                try:
                    path.unlink()
                except OSError:
                    pass


class StreamProxy:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sources = {}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler_class())
        self.server.daemon_threads = True
        self.server.sources = self.sources
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def add(self, bvid: str, url: str, size: int) -> str:
        token = secrets.token_urlsafe(16)
        self.sources.clear()
        self.sources[token] = StreamSource(bvid, url, size, self.cache_dir)
        return f"http://127.0.0.1:{self.server.server_port}/media/{token}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @staticmethod
    def handler_class():
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                pass

            def source(self):
                path = urlsplit(self.path).path
                if not path.startswith("/media/"):
                    return None
                return self.server.sources.get(path.rsplit("/", 1)[-1])

            def requested_range(self, size):
                match = re.fullmatch(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
                if not match:
                    return None
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else size - 1
                if start >= size or end < start:
                    return "invalid"
                return start, min(end, size - 1)

            def do_HEAD(self):
                source = self.source()
                if source is None:
                    self.send_error(404)
                    return
                size = source.final.stat().st_size if source.final.exists() else source.size
                if not size:
                    self.send_error(503)
                    return
                requested = self.requested_range(size)
                if requested == "invalid":
                    self.send_error(416)
                    return
                start, end = requested if requested else (0, size - 1)
                self.send_response(206 if requested else 200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(end - start + 1))
                if requested:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.end_headers()

            def do_GET(self):
                source = self.source()
                if source is None:
                    self.send_error(404)
                    return
                if source.final.exists():
                    self.serve_file(source)
                else:
                    self.serve_remote(source)

            def serve_file(self, source):
                size = source.final.stat().st_size
                requested = self.requested_range(size)
                if requested == "invalid":
                    self.send_error(416)
                    return
                start, end = requested if requested else (0, size - 1)
                self.send_response(206 if requested else 200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(end - start + 1))
                if requested:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.end_headers()
                try:
                    with source.final.open("rb") as stream:
                        stream.seek(start)
                        remaining = end - start + 1
                        while remaining:
                            chunk = stream.read(min(131072, remaining))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def serve_remote(self, source):
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
                    "Referer": "https://www.bilibili.com/",
                }
                if self.headers.get("Range"):
                    headers["Range"] = self.headers["Range"]
                try:
                    with requests.get(source.url, headers=headers, stream=True, timeout=(10, 30)) as upstream:
                        upstream.raise_for_status()
                        length = upstream.headers.get("Content-Length")
                        content_range = upstream.headers.get("Content-Range")
                        start = int(content_range.split(" ", 1)[1].split("-", 1)[0]) if content_range else 0
                        self.send_response(upstream.status_code)
                        self.send_header("Content-Type", "video/mp4")
                        self.send_header("Accept-Ranges", "bytes")
                        if length:
                            self.send_header("Content-Length", length)
                        if content_range:
                            self.send_header("Content-Range", content_range)
                        self.send_header("Connection", "close")
                        self.end_headers()
                        self.close_connection = True
                        offset = start
                        for chunk in upstream.iter_content(chunk_size=65536):
                            if not chunk:
                                continue
                            source.store(offset, chunk)
                            offset += len(chunk)
                            self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except requests.RequestException:
                    if not self.headers_sent():
                        self.send_error(502)

            def headers_sent(self):
                return getattr(self, "_headers_buffer", []) == [] and hasattr(self, "_headers_buffer")

        return Handler


class MediaWorker(QThread):
    ready = Signal(object)
    failed = Signal(str)
    cover_ready = Signal(bytes)

    def __init__(self, bvid: str, cache_dir: Path, token: int, cover: str = ""):
        super().__init__()
        self.bvid = bvid
        self.cache_dir = cache_dir
        self.token = token
        self.cover_url = cover

    def fetch_cover(self):
        if self.cover_url and not self.isInterruptionRequested():
            try:
                response = requests.get(self.cover_url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}, timeout=6)
                if response.ok and len(response.content) < 2_000_000:
                    self.cover_ready.emit(response.content)
            except requests.RequestException:
                pass

    def run(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        final = self.cache_dir / f"{self.bvid}.mp4"
        if final.exists() and final.stat().st_size > 10_000:
            self.ready.emit({"path": str(final)})
            self.fetch_cover()
            return
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        try:
            session.get("https://www.bilibili.com/", headers=headers, timeout=12)
            pages = session.get(PAGELIST_API, params={"bvid": self.bvid}, headers=headers, timeout=12)
            pages.raise_for_status()
            payload = pages.json()
            if payload.get("code") != 0 or not payload.get("data"):
                raise ValueError("未取得视频分段信息")
            cid = payload["data"][0]["cid"]
            response = session.get(PLAYURL_API, params={"bvid": self.bvid, "cid": cid, "qn": 16, "fnval": 0}, headers=headers, timeout=12)
            response.raise_for_status()
            url, size = select_mp4(response.json())
            if self.isInterruptionRequested():
                return
            self.ready.emit({"url": url, "size": size, "bvid": self.bvid})
            self.fetch_cover()
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
        finally:
            session.close()


class VideoCard(QFrame):
    def __init__(self, item: dict, on_play, on_favorite=None, is_favorite=False):
        super().__init__()
        self.setObjectName("videoCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.item = item
        self.on_play = on_play
        self.setFixedWidth(312)
        self.setFixedHeight(262)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 12)
        layout.setSpacing(8)
        cover = QLabel()
        cover.setFixedSize(292, 164)
        cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover.setObjectName("cover")
        pix = QPixmap()
        if item.get("image") and pix.loadFromData(item["image"]):
            cover.setPixmap(pix.scaled(292, 164, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        else:
            cover.setPixmap(placeholder_cover())
        if on_favorite:
            favorite = QPushButton("已收藏" if is_favorite else "收藏", cover)
            favorite.setObjectName("favoriteToggle")
            favorite.setCursor(Qt.CursorShape.PointingHandCursor)
            favorite.setFixedSize(60, 27)
            favorite.move(223, 10)
            favorite.clicked.connect(lambda: on_favorite(item))
        layout.addWidget(cover)
        title = QLabel(item["title"])
        title.setWordWrap(True)
        title.setMaximumHeight(42)
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        detail = f"{item['author']}  ·  {item['duration']}"
        if item.get("played_at"):
            detail += "  ·  " + str(item["played_at"])[5:16].replace("T", " ")
        meta = QLabel(detail)
        meta.setObjectName("muted")
        meta.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(meta)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_play(self.item)
        super().mousePressEvent(event)


class TitleBar(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setFixedHeight(46)
        self._drag_offset = None
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self.brand = QLabel("司凤星球")
        self.brand.setObjectName("brand")
        row.addWidget(self.brand)
        row.addStretch()
        self.nav_buttons = [
            owner.button("发现", owner.show_home),
            owner.button("本地收藏", owner.show_favorites),
            owner.button("司凤记录", owner.show_history),
            owner.button("正在播放", owner.show_player),
            owner.button("偏好设置", owner.toggle_preferences),
        ]
        for button in self.nav_buttons:
            row.addWidget(button)
        row.addSpacing(14)
        self.min_button = self.chrome_button("minimize.svg", "最小化", owner.showMinimized)
        self.max_button = self.chrome_button("maximize.svg", "最大化", owner.toggle_maximize)
        self.close_button = self.chrome_button("close.svg", "关闭到托盘", owner.close, close=True)
        row.addWidget(self.min_button)
        row.addWidget(self.max_button)
        row.addWidget(self.close_button)

    def chrome_button(self, filename, tip, callback, close=False):
        button = QPushButton()
        button.setObjectName("chromeClose" if close else "chrome")
        button.setFixedSize(34, 32)
        button.setIcon(QIcon(str(Path(__file__).with_name(filename))))
        button.setIconSize(QSize(18, 18))
        button.setToolTip(tip)
        button.clicked.connect(callback)
        return button

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.owner.windowHandle()
            if not (handle and handle.startSystemMove()):
                self._drag_offset = event.globalPosition().toPoint() - self.owner.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.owner.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.toggle_maximize()
        super().mouseDoubleClickEvent(event)


class IntroPage(QWidget):
    configure = Signal()
    skip = Signal()

    def __init__(self):
        super().__init__()
        self.started = False
        self.animations = []
        self.title = QLabel("司凤星球", self)
        font = self.title.font()
        font.setPointSize(56)
        font.setBold(True)
        self.title.setFont(font)
        self.title.adjustSize()
        self.tagline = QLabel("听你想听的，通透你想通透的", self)
        self.tagline.setStyleSheet("color:#74747b;font-size:18px;")
        self.tagline.adjustSize()
        self.tag_effect = QGraphicsOpacityEffect(self.tagline)
        self.tag_effect.setOpacity(0)
        self.tagline.setGraphicsEffect(self.tag_effect)
        self.start_button = QPushButton("开始配置  →", self)
        self.start_button.setObjectName("primary")
        self.start_button.setFixedSize(220, 58)
        shadow = QGraphicsDropShadowEffect(self.start_button)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 22))
        self.start_button.setGraphicsEffect(shadow)
        self.start_button.setVisible(False)
        self.start_button.clicked.connect(self.exit_left)
        self.skip_button = QPushButton("跳过配置", self)
        self.skip_button.clicked.connect(self.skip.emit)
        self.skip_button.adjustSize()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.started:
            self.started = True
            QTimer.singleShot(550, self.animate_intro)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.skip_button.move(self.width() - self.skip_button.width() - 36, 12)
        if not self.animations:
            self.title.move((self.width() - self.title.width()) // 2, int(self.height() * 0.48))
            self.tagline.move((self.width() - self.tagline.width()) // 2, int(self.height() * 0.62))

    def animate_intro(self):
        start_x = (self.width() - self.title.width()) // 2
        start_y = int(self.height() * 0.48)
        end_y = int(self.height() * 0.31)
        motion = QVariantAnimation(self)
        motion.setDuration(1500)
        motion.setStartValue(0.0)
        motion.setEndValue(1.0)
        motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        motion.valueChanged.connect(lambda t: self.title.move(
            round(start_x - 28 * math.sin(math.pi * float(t))),
            round(start_y + (end_y - start_y) * float(t))))
        motion.finished.connect(self.fade_tagline)
        self.animations.append(motion)
        motion.start()

    def fade_tagline(self):
        self.tagline.move((self.width() - self.tagline.width()) // 2, int(self.height() * 0.50))
        fade = QPropertyAnimation(self.tag_effect, b"opacity", self)
        fade.setDuration(1100)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.finished.connect(self.reveal_configure)
        self.animations.append(fade)
        fade.start()

    def reveal_configure(self):
        title_x, title_y = self.title.pos().x(), self.title.pos().y()
        target_x, target_y = 64, int(self.height() * 0.38)
        self.start_button.move(self.width() + 20, target_y + 22)
        self.start_button.show()
        shift = QVariantAnimation(self)
        shift.setDuration(1100)
        shift.setStartValue(0.0)
        shift.setEndValue(1.0)
        shift.setEasingCurve(QEasingCurve.Type.OutCubic)

        def update(value):
            t = float(value)
            font = self.title.font()
            font.setPointSizeF(56 - 8 * t)
            self.title.setFont(font)
            self.title.adjustSize()
            self.title.move(round(title_x + (target_x - title_x) * t), round(title_y + (target_y - title_y) * t))
            self.tagline.move(round((self.width() - self.tagline.width()) / 2 + (target_x - (self.width() - self.tagline.width()) / 2) * t), target_y + 82)
            self.start_button.move(round(self.width() + 20 + (self.width() - 300 - self.width() - 20) * t), target_y + 18)

        shift.valueChanged.connect(update)
        self.animations.append(shift)
        shift.start()

    def exit_left(self):
        self.start_button.setEnabled(False)
        remaining = [self.title, self.tagline, self.start_button, self.skip_button]
        duration = 650
        for widget in remaining:
            animation = QPropertyAnimation(widget, b"pos", self)
            animation.setDuration(duration)
            animation.setStartValue(widget.pos())
            animation.setEndValue(QPoint(-widget.width() - 60, widget.y()))
            animation.setEasingCurve(QEasingCurve.Type.InCubic)
            self.animations.append(animation)
            animation.start()
        QTimer.singleShot(duration + 30, self.configure.emit)


class RotatingCover(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(48, 48)
        self.image = QPixmap()
        self.angle = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.advance)

    def set_image(self, data: bytes):
        self.image = QPixmap()
        self.image.loadFromData(data or b"")
        self.angle = 0.0
        self.update()

    def advance(self):
        self.angle = (self.angle + 0.75) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(24, 24)
        painter.rotate(self.angle)
        path = QPainterPath()
        path.addEllipse(-22, -22, 44, 44)
        painter.setClipPath(path)
        if self.image.isNull():
            painter.setBrush(QColor("#eeeeef"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(-22, -22, 44, 44)
            painter.setBrush(QColor("#2a2a2d"))
            painter.drawEllipse(-8, -8, 16, 16)
        else:
            scaled = self.image.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(-22, -22, scaled)
        painter.end()


class MiniCapsule(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(320, 72)
        body = QFrame(self)
        body.setGeometry(4, 4, 312, 64)
        body.setObjectName("capsuleBody")
        body.setStyleSheet("QFrame#capsuleBody{background:#ffffff;border:1px solid #e5e5e9;border-radius:32px;}")
        shadow = QGraphicsDropShadowEffect(body)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 28))
        body.setGraphicsEffect(shadow)
        row = QHBoxLayout(body)
        row.setContentsMargins(9, 7, 14, 7)
        row.setSpacing(12)
        self.cover = RotatingCover()
        row.addWidget(self.cover)
        self.caption = QLabel("播放中：")
        self.caption.setStyleSheet("color:#1b1b1e;font-size:12px;font-weight:650;background:transparent;")
        row.addWidget(self.caption, 1)

    def set_track(self, item):
        self.cover.set_image(item.get("image") or b"")
        self.caption.setText(self.caption.fontMetrics().elidedText("播放中：" + item["title"], Qt.TextElideMode.ElideRight, 215))
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 22, area.bottom() - self.height() - 22)

    def set_playing(self, playing: bool):
        self.cover.timer.start() if playing else self.cover.timer.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.reopen()
            self.owner.show_player()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setContentsMargins(8, 8, 8, 8)
        self.setWindowTitle("司凤星球")
        self.setWindowIcon(app_icon())
        self.resize(1110, 760)
        self.setMinimumSize(770, 570)
        self.items: list[dict] = []
        self.index = -1
        self.page = 1
        self.worker = None
        self.media_workers = []
        self.media_token = 0
        self.cache_dir = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "SiFengPlanet" / "Cache"
        self.proxy = None
        self.search_error = ""
        self.ending_handled = False
        self.pending_refresh = False
        self._hotkey_registered = False
        self.settings_path = Path.home() / "AppData" / "Roaming" / "SiFengPlanet" / "settings.json"
        self.library_path = self.settings_path.with_name("library.json")
        self.settings = self.load_settings()
        self.favorites, self.history = self.load_library()
        self.history_token = -1
        self.onboarding_mode = not self.settings["onboarding_complete"]
        self.build_ui()
        self.mini_capsule = MiniCapsule(self)
        self.setup_tray()
        if self.onboarding_mode:
            self.stack.setCurrentIndex(3)
            self.set_onboarding_chrome(True)
            self.status.hide()
        else:
            QTimer.singleShot(250, self.search)
            QTimer.singleShot(600, self.register_hotkey)

    def load_settings(self) -> dict:
        defaults = {
            "search_terms": list(KEYWORDS),
            "playback_mode": "continue",
            "close_behavior": "tray",
            "next_hotkey": "Ctrl+Alt+N",
            "floating": False,
            "onboarding_complete": False,
        }
        try:
            saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                if "repeat" in saved and "playback_mode" not in saved:
                    saved["playback_mode"] = "repeat" if saved["repeat"] else "continue"
                defaults.update({key: value for key, value in saved.items() if key in defaults})
        except (OSError, ValueError, TypeError):
            pass
        if not isinstance(defaults["search_terms"], list) or not defaults["search_terms"]:
            defaults["search_terms"] = list(KEYWORDS)
        if defaults["playback_mode"] not in ("continue", "repeat", "random"):
            defaults["playback_mode"] = "continue"
        if defaults["close_behavior"] not in ("tray", "quit"):
            defaults["close_behavior"] = "tray"
        return defaults

    def save_settings(self):
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            self.status.setText("偏好设置暂未保存")

    def load_library(self):
        try:
            data = json.loads(self.library_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return [], []
            collections = []
            for name in ("favorites", "history"):
                rows = []
                source = data.get(name, [])
                for item in source if isinstance(source, list) else []:
                    if not isinstance(item, dict) or not re.fullmatch(r"BV[0-9A-Za-z]+", str(item.get("bvid", ""))):
                        continue
                    clean = {key: item.get(key, "") for key in ("bvid", "title", "author", "duration", "pic", "play", "played_at")}
                    cover = self.library_path.parent / "covers" / f"{clean['bvid']}.img"
                    if cover.exists():
                        clean["image"] = cover.read_bytes()
                    rows.append(clean)
                collections.append(rows[:100])
            return collections
        except (OSError, ValueError, TypeError):
            return [], []

    def save_library(self):
        try:
            self.library_path.parent.mkdir(parents=True, exist_ok=True)
            covers = self.library_path.parent / "covers"
            covers.mkdir(exist_ok=True)
            data = {}
            for name, rows in (("favorites", self.favorites), ("history", self.history)):
                data[name] = []
                for item in rows:
                    image = item.get("image")
                    if image:
                        (covers / f"{item['bvid']}.img").write_bytes(image)
                    data[name].append({key: item.get(key, "") for key in ("bvid", "title", "author", "duration", "pic", "play", "played_at")})
            temporary = self.library_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.library_path)
        except OSError:
            self.status.setText("收藏与记录暂未保存")

    def toggle_favorite(self, item):
        bvid = item["bvid"]
        if any(row["bvid"] == bvid for row in self.favorites):
            self.favorites = [row for row in self.favorites if row["bvid"] != bvid]
        else:
            self.favorites.insert(0, dict(item))
        self.save_library()
        self.render_cards()
        self.render_collection("favorites")
        self.render_collection("history")
        if self.index >= 0 and self.items[self.index]["bvid"] == bvid:
            self.favorite_button.setText("已收藏" if self.is_favorite(bvid) else "收藏")

    def is_favorite(self, bvid: str) -> bool:
        return any(item["bvid"] == bvid for item in self.favorites)

    def favorite_current(self):
        if self.index >= 0:
            self.toggle_favorite(self.items[self.index])

    def record_history(self, item):
        row = dict(item)
        row["played_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        self.history = [row] + [old for old in self.history if old["bvid"] != row["bvid"]]
        self.history = self.history[:100]
        self.save_library()
        self.render_collection("history")

    def button(self, label: str, callback, primary: bool = False) -> QPushButton:
        btn = QPushButton(label)
        shadow = QGraphicsDropShadowEffect(btn)
        shadow.setBlurRadius(14 if primary else 9)
        shadow.setOffset(0, 3 if primary else 2)
        shadow.setColor(QColor(0, 0, 0, 17 if primary else 9))
        btn.setGraphicsEffect(shadow)
        if primary:
            btn.setObjectName("primary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    def build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(36, 24, 36, 20)
        outer.setSpacing(24)
        self.titlebar = TitleBar(self)
        outer.addWidget(self.titlebar)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)
        self.build_home()
        self.build_player()
        self.build_preferences()
        self.build_intro()
        self.build_collection("favorites", "本地收藏", "喜欢的歌，随时再听。")
        self.build_collection("history", "司凤记录", "这里记着你听过的每一首。")

        self.status = QLabel("准备发现音乐…")
        self.status.setObjectName("muted")
        outer.addWidget(self.status)
        self.setStyleSheet("""
        QWidget#root { background: #ffffff; color: #17171a; border: 1px solid #e6e6e9; border-radius: 20px; font-family: 'Segoe UI', 'Microsoft YaHei UI'; font-size: 13px; }
        QWidget#root[maximized="true"] { border: none; border-radius: 0px; }
        QLabel { color: #17171a; }
        QLabel#brand { font-size: 19px; font-weight: 800; letter-spacing: 1px; }
        QLabel#hero { font-size: 34px; font-weight: 800; }
        QLabel#section { font-size: 19px; font-weight: 700; }
        QLabel#eyebrow { color: #e85468; font-size: 11px; font-weight: 750; letter-spacing: 2px; }
        QLabel#muted { color: #85858b; font-size: 12px; }
        QLabel#cardTitle { font-size: 13px; font-weight: 650; }
        QLabel#configLabel { font-size: 14px; font-weight: 650; }
        QLabel#cover { background: #f2f2f4; color: #bbbcc2; border-radius: 12px; font-size: 45px; }
        QFrame#videoCard { background: #ffffff; border: 1px solid transparent; border-radius: 16px; }
        QFrame#videoCard:hover { background: #fafafa; border-color: #ededf0; }
        QFrame#heroPanel { background: #ffffff; border: none; }
        QFrame#featured { background:#f5f5f6; border:none; border-radius:18px; }
        QPushButton { background: transparent; border: none; border-radius: 12px; padding: 9px 14px; color: #55555b; font-weight: 650; }
        QPushButton:hover { background: #f3f3f5; color: #151518; }
        QPushButton#favoriteToggle { color:#333338; background:#ffffff; border:none; border-radius:13px; padding:2px; font-size:11px; }
        QPushButton#favoriteToggle:hover { background:#ffecef; color:#cc3449; }
        QPushButton#primary { background: #1b1b1e; color: white; }
        QPushButton#primary:hover { background: #3a3a40; }
        QPushButton#chrome, QPushButton#chromeClose { background: transparent; border: none; border-radius: 9px; padding: 0; }
        QPushButton#chrome:hover { background: #f0f0f2; }
        QPushButton#chromeClose:hover { background: #ffe8eb; }
        QLineEdit { background: #f4f4f5; color: #17171a; border: 1px solid #f4f4f5; border-radius: 12px; padding: 10px 14px; }
        QLineEdit:focus { border-color: #c9c9cf; }
        QComboBox, QKeySequenceEdit { background:#f4f4f5; border:1px solid #f4f4f5; border-radius:12px; padding:10px 14px; color:#17171a; min-height:20px; }
        QComboBox::drop-down { border:none; width:26px; }
        QScrollArea { border: none; background: #ffffff; }
        QScrollArea QWidget { background: #ffffff; }
        QCheckBox { spacing: 12px; font-size: 15px; }
        QCheckBox::indicator { width: 20px; height: 20px; }
        QSlider::groove:horizontal { height: 4px; background: #e5e5e8; border-radius: 2px; }
        QSlider::sub-page:horizontal { background: #e85468; border-radius: 2px; }
        QSlider::handle:horizontal { background: #e85468; width: 12px; margin: -4px 0; border-radius: 6px; }
        """)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "titlebar"):
            maximized = self.isMaximized()
            self.setContentsMargins(*(0, 0, 0, 0) if maximized else (8, 8, 8, 8))
            self.centralWidget().setProperty("maximized", maximized)
            self.centralWidget().style().unpolish(self.centralWidget())
            self.centralWidget().style().polish(self.centralWidget())
            icon = "restore.svg" if maximized else "maximize.svg"
            self.titlebar.max_button.setIcon(QIcon(str(Path(__file__).with_name(icon))))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized() and self.windowHandle():
            pos = event.position()
            width, height = self.width(), self.height()
            edges = Qt.Edge(0)
            if pos.x() < 9:
                edges |= Qt.Edge.LeftEdge
            elif pos.x() > width - 9:
                edges |= Qt.Edge.RightEdge
            if pos.y() < 9:
                edges |= Qt.Edge.TopEdge
            elif pos.y() > height - 9:
                edges |= Qt.Edge.BottomEdge
            if edges and self.windowHandle().startSystemResize(edges):
                return
        super().mousePressEvent(event)

    def build_home(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(15)
        hero = QFrame()
        hero.setObjectName("heroPanel")
        h = QVBoxLayout(hero)
        h.setContentsMargins(0, 6, 0, 8)
        eyebrow = QLabel("SIFENG RADIO  /  BILIBILI")
        eyebrow.setObjectName("eyebrow")
        h.addWidget(eyebrow)
        title = QLabel("只听喜欢的。")
        title.setObjectName("hero")
        h.addWidget(title)
        line = QLabel("、".join(self.settings["search_terms"]) + "。轻轻点开，音乐就开始了。")
        self.home_subtitle = line
        line.setWordWrap(True)
        line.setObjectName("muted")
        h.addWidget(line)
        v.addWidget(hero)
        self.featured = QFrame()
        self.featured.setObjectName("featured")
        self.featured.setFixedHeight(142)
        feature_row = QHBoxLayout(self.featured)
        feature_row.setContentsMargins(10, 9, 22, 9)
        feature_row.setSpacing(24)
        self.feature_cover = QLabel()
        self.feature_cover.setFixedSize(218, 123)
        feature_row.addWidget(self.feature_cover)
        feature_copy = QVBoxLayout()
        feature_copy.setSpacing(5)
        feature_label = QLabel("现在就听")
        feature_label.setObjectName("eyebrow")
        feature_copy.addWidget(feature_label)
        self.feature_title = QLabel("")
        self.feature_title.setObjectName("section")
        self.feature_title.setWordWrap(True)
        feature_copy.addWidget(self.feature_title)
        self.feature_meta = QLabel("")
        self.feature_meta.setObjectName("muted")
        feature_copy.addWidget(self.feature_meta)
        feature_copy.addStretch()
        feature_row.addLayout(feature_copy, 1)
        self.feature_play = self.button("播放", lambda: self.play_item(self.items[0]) if self.items else None, True)
        feature_row.addWidget(self.feature_play, 0, Qt.AlignmentFlag.AlignVCenter)
        self.featured.hide()
        v.addWidget(self.featured)
        controls = QHBoxLayout()
        label = QLabel("发现")
        label.setObjectName("section")
        controls.addWidget(label)
        controls.addStretch()
        self.query = QLineEdit()
        self.query.setPlaceholderText("在已筛选的标题中找一找…")
        self.query.setFixedWidth(270)
        self.query.textChanged.connect(self.render_cards)
        controls.addWidget(self.query)
        controls.addWidget(self.button("刷新", self.refresh))
        v.addLayout(controls)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cards_host = QWidget()
        self.cards = QGridLayout(self.cards_host)
        self.cards.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.cards.setSpacing(16)
        scroll.setWidget(self.cards_host)
        v.addWidget(scroll, 1)
        more = self.button("查看更多", self.more)
        v.addWidget(more, 0, Qt.AlignmentFlag.AlignHCenter)
        self.stack.addWidget(page)

    def build_player(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)
        v.addWidget(self.button("←  返回发现", self.show_home), 0, Qt.AlignmentFlag.AlignLeft)
        self.now_title = QLabel("选一首，开始听。")
        self.now_title.setObjectName("hero")
        self.now_title.setWordWrap(True)
        v.addWidget(self.now_title)
        self.now_meta = QLabel("来自哔哩哔哩 · 原生播放")
        self.now_meta.setObjectName("muted")
        v.addWidget(self.now_meta)
        self.video_stack = QStackedWidget()
        self.video_stack.setMinimumHeight(280)
        self.player_hint = QLabel("♪  选择一首视频")
        self.player_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.player_hint.setStyleSheet("background:#f4f4f5;color:#909096;border-radius:18px;font-size:22px;")
        self.video = QVideoWidget()
        self.video.setStyleSheet("background:#111111;border-radius:18px;")
        video_palette = self.video.palette()
        video_palette.setColor(QPalette.ColorRole.Window, QColor("#111111"))
        self.video.setPalette(video_palette)
        self.video.setAutoFillBackground(True)
        self.video_stack.addWidget(self.player_hint)
        self.video_stack.addWidget(self.video)
        v.addWidget(self.video_stack, 1)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.75)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.positionChanged.connect(self.on_position)
        self.player.durationChanged.connect(self.on_duration)
        self.player.playbackStateChanged.connect(self.on_playback_state)
        self.player.errorOccurred.connect(self.on_playback_error)
        progress = QHBoxLayout()
        self.elapsed = QLabel("0:00")
        self.elapsed.setObjectName("muted")
        progress.addWidget(self.elapsed)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderMoved.connect(self.player.setPosition)
        progress.addWidget(self.seek, 1)
        self.total = QLabel("0:00")
        self.total.setObjectName("muted")
        progress.addWidget(self.total)
        v.addLayout(progress)
        row = QHBoxLayout()
        self.favorite_button = self.button("收藏", self.favorite_current)
        row.addWidget(self.favorite_button)
        row.addStretch()
        row.addWidget(self.button("上一首", self.previous))
        self.play_button = self.button("播放", self.toggle_play, True)
        self.play_button.setMinimumWidth(86)
        row.addWidget(self.play_button)
        row.addWidget(self.button("下一首", self.next_video))
        v.addLayout(row)
        self.stack.addWidget(page)

    def build_preferences(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setAlignment(Qt.AlignmentFlag.AlignTop)
        v.setContentsMargins(28, 18, 28, 20)
        v.setSpacing(14)
        self.pref_title = QLabel("偏好设置")
        self.pref_title.setObjectName("hero")
        v.addWidget(self.pref_title)
        self.pref_subtitle = QLabel("几项选择，让司凤星球更合你的习惯。")
        self.pref_subtitle.setObjectName("muted")
        v.addWidget(self.pref_subtitle)
        self.pref_progress = QLabel("")
        self.pref_progress.setObjectName("eyebrow")
        v.addWidget(self.pref_progress)
        grid = QGridLayout()
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(18)
        grid.setColumnStretch(1, 1)
        self.terms_edit = QLineEdit("、".join(self.settings["search_terms"]))
        self.terms_edit.setPlaceholderText("用逗号隔开，最多 8 个")
        self.terms_edit.setMinimumWidth(360)
        self.mode_combo = QComboBox()
        for label, value in [("顺序播放", "continue"), ("单曲循环", "repeat"), ("随机播放", "random")]:
            self.mode_combo.addItem(label, value)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(self.settings["playback_mode"]))
        self.exit_combo = QComboBox()
        self.exit_combo.addItem("关闭到托盘", "tray")
        self.exit_combo.addItem("完全退出", "quit")
        self.exit_combo.setCurrentIndex(self.exit_combo.findData(self.settings["close_behavior"]))
        self.hotkey_edit = QKeySequenceEdit()
        self.hotkey_edit.setKeySequence(QKeySequence(self.settings["next_hotkey"]))
        self.float_box = QCheckBox("显示正在播放的悬浮胶囊")
        self.float_box.setChecked(bool(self.settings["floating"]))
        self.pref_rows = []
        for row, (label, control) in enumerate([
            ("搜索词", self.terms_edit),
            ("播完之后", self.mode_combo),
            ("关闭窗口", self.exit_combo),
            ("下一首快捷键", self.hotkey_edit),
            ("悬浮窗", self.float_box),
        ]):
            name = QLabel(label)
            name.setObjectName("configLabel")
            grid.addWidget(name, row, 0)
            grid.addWidget(control, row, 1)
            self.pref_rows.append((name, control))
        v.addLayout(grid)
        self.pref_message = QLabel("搜索词需出现在视频标题中；快捷键可留空。")
        self.pref_message.setObjectName("muted")
        v.addWidget(self.pref_message)
        footer = QHBoxLayout()
        self.pref_back = self.button("返回发现", self.show_home)
        footer.addWidget(self.pref_back)
        footer.addStretch()
        self.pref_skip = self.button("跳过配置", self.skip_onboarding)
        footer.addWidget(self.pref_skip)
        self.pref_done = self.button("保存设置", self.advance_preferences, True)
        self.pref_done.setMinimumSize(128, 48)
        footer.addWidget(self.pref_done)
        v.addLayout(footer)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self.stack.addWidget(page)

    def build_intro(self):
        self.intro = IntroPage()
        self.intro.configure.connect(self.show_onboarding_preferences)
        self.intro.skip.connect(self.skip_onboarding)
        self.stack.addWidget(self.intro)

    def build_collection(self, name: str, heading: str, subtitle: str):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)
        title = QLabel(heading)
        title.setObjectName("hero")
        layout.addWidget(title)
        description = QLabel(subtitle)
        description.setObjectName("muted")
        layout.addWidget(description)
        count = QLabel("")
        count.setObjectName("muted")
        layout.addWidget(count)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        grid = QGridLayout(host)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        grid.setSpacing(16)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)
        self.stack.addWidget(page)
        if not hasattr(self, "collection_views"):
            self.collection_views = {}
        self.collection_views[name] = (grid, count)
        self.render_collection(name)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("司凤星球")
        menu = QMenu()
        menu.addAction("打开司凤星球", self.reopen)
        menu.addAction("下一首", self.next_video)
        menu.addSeparator()
        menu.addAction("退出", QApplication.instance().quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.reopen() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        if QSystemTrayIcon.isSystemTrayAvailable() and self.settings["close_behavior"] == "tray":
            self.tray.show()

    def closeEvent(self, event):
        if self.settings["close_behavior"] == "tray" and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage("司凤星球仍在运行", "双击托盘图标可重新打开。", QSystemTrayIcon.MessageIcon.Information, 2500)
        else:
            event.accept()
            QTimer.singleShot(0, QApplication.instance().quit)

    def reopen(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def show_home(self):
        if self.onboarding_mode:
            return
        self.transition_to(0)

    def show_player(self):
        if self.onboarding_mode:
            return
        self.transition_to(1)

    def show_favorites(self):
        if not self.onboarding_mode:
            self.render_collection("favorites")
            self.transition_to(4)

    def show_history(self):
        if not self.onboarding_mode:
            self.render_collection("history")
            self.transition_to(5)

    def toggle_preferences(self):
        if self.onboarding_mode:
            return
        self.pref_title.setText("偏好设置")
        self.pref_back.show()
        self.pref_skip.hide()
        self.pref_done.setText("保存设置")
        self.show_all_preferences()
        self.transition_to(0 if self.stack.currentIndex() == 2 else 2)

    def transition_to(self, index: int):
        if self.stack.currentIndex() == index:
            return
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", page)
        animation.setDuration(340)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: page.setGraphicsEffect(None) if page.graphicsEffect() is effect else None)
        self.page_animation = animation
        animation.start()

    def show_all_preferences(self):
        for name, control in self.pref_rows:
            name.show()
            control.show()
        self.pref_progress.hide()
        self.pref_subtitle.setText("几项选择，让司凤星球更合你的习惯。")

    def show_preference_step(self, step: int):
        self.pref_step = step
        labels = ["想听什么", "播完之后", "关闭窗口", "切歌快捷键", "悬浮胶囊"]
        self.pref_title.setText(labels[step])
        self.pref_subtitle.setText("按你的习惯选择，之后仍可在偏好设置中修改。")
        self.pref_progress.setText(f"{step + 1:02d}  /  05")
        self.pref_progress.show()
        for row, (name, control) in enumerate(self.pref_rows):
            name.setVisible(row == step)
            control.setVisible(row == step)
        self.pref_back.setText("上一步")
        self.pref_back.show()
        self.pref_done.setText("开始听" if step == 4 else "继续")
        if step == 0:
            self.pref_back.hide()

    def previous_preference_step(self):
        if self.onboarding_mode and getattr(self, "pref_step", 0) > 0:
            self.animate_preference_step(self.pref_step - 1)
        else:
            self.show_home()

    def animate_preference_step(self, step: int):
        page = self.stack.widget(2)
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        fade_out = QPropertyAnimation(effect, b"opacity", page)
        fade_out.setDuration(180)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)

        def reveal():
            self.show_preference_step(step)
            fade_in = QPropertyAnimation(effect, b"opacity", page)
            fade_in.setDuration(300)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.finished.connect(lambda: page.setGraphicsEffect(None) if page.graphicsEffect() is effect else None)
            self.step_animation = fade_in
            fade_in.start()

        fade_out.finished.connect(reveal)
        self.step_animation = fade_out
        fade_out.start()

    def advance_preferences(self):
        if not self.onboarding_mode:
            self.apply_preferences()
            return
        if self.pref_step == 0:
            try:
                parse_terms(self.terms_edit.text())
            except ValueError as exc:
                self.pref_message.setText(str(exc))
                return
        if self.pref_step == 3:
            try:
                hotkey_parts(self.hotkey_edit.keySequence())
            except ValueError as exc:
                self.pref_message.setText(str(exc))
                return
        self.pref_message.setText("")
        if self.pref_step < 4:
            self.animate_preference_step(self.pref_step + 1)
        else:
            self.apply_preferences()

    def set_onboarding_chrome(self, active: bool):
        self.titlebar.brand.setVisible(not active or self.stack.currentIndex() != 3)
        for button in self.titlebar.nav_buttons:
            button.setVisible(not active)

    def show_onboarding_preferences(self):
        if not self.onboarding_mode:
            return
        self.transition_to(2)
        self.set_onboarding_chrome(True)
        self.show_preference_step(0)
        self.pref_back.clicked.disconnect()
        self.pref_back.clicked.connect(self.previous_preference_step)
        self.pref_skip.show()
        self.pref_done.setText("继续")

    def finish_onboarding(self):
        self.settings["onboarding_complete"] = True
        self.save_settings()
        self.onboarding_mode = False
        self.transition_to(0)
        self.set_onboarding_chrome(False)
        self.status.show()
        self.search()
        QTimer.singleShot(100, self.register_hotkey)

    def skip_onboarding(self):
        if self.onboarding_mode:
            self.finish_onboarding()

    def apply_preferences(self):
        try:
            terms = parse_terms(self.terms_edit.text())
            sequence = self.hotkey_edit.keySequence()
            hotkey_parts(sequence)
        except ValueError as exc:
            self.pref_message.setText(str(exc))
            self.pref_message.setStyleSheet("color:#d5364b;")
            return
        old_terms = tuple(self.settings["search_terms"])
        self.settings.update({
            "search_terms": list(terms),
            "playback_mode": self.mode_combo.currentData(),
            "close_behavior": self.exit_combo.currentData(),
            "next_hotkey": sequence.toString(),
            "floating": self.float_box.isChecked(),
        })
        self.save_settings()
        self.home_subtitle.setText("、".join(terms) + "。轻轻点开，音乐就开始了。")
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show() if self.settings["close_behavior"] == "tray" else self.tray.hide()
        self.pref_message.setText("已保存")
        self.pref_message.setStyleSheet("color:#6c6c73;")
        if self.onboarding_mode:
            self.finish_onboarding()
        else:
            self.register_hotkey()
            self.update_capsule()
            self.show_home()
            if terms != old_terms:
                if self.worker and self.worker.isRunning():
                    self.pending_refresh = True
                else:
                    self.refresh()

    def register_hotkey(self):
        if os.name != "nt":
            return
        user32 = ctypes.windll.user32
        user32.RegisterHotKey.argtypes = [wintypes.HWND, wintypes.INT, wintypes.UINT, wintypes.UINT]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = [wintypes.HWND, wintypes.INT]
        user32.UnregisterHotKey.restype = wintypes.BOOL
        hwnd = int(self.winId())
        if self._hotkey_registered:
            user32.UnregisterHotKey(hwnd, 0x5346)
            self._hotkey_registered = False
        try:
            parts = hotkey_parts(QKeySequence(self.settings["next_hotkey"]))
        except ValueError:
            parts = None
        if parts:
            self._hotkey_registered = bool(user32.RegisterHotKey(hwnd, 0x5346, *parts))
            if not self._hotkey_registered and not self.onboarding_mode:
                self.status.setText("切歌快捷键已被其他程序占用，可在偏好设置中更换")

    def nativeEvent(self, event_type, message):
        if os.name == "nt":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == 0x5346:
                QTimer.singleShot(0, self.next_video)
                return True, 0
        return super().nativeEvent(event_type, message)

    def refresh(self):
        if self.worker and self.worker.isRunning():
            self.status.setText("正在发现音乐，请稍候再刷新")
            return
        self.page = 1
        self.items.clear()
        self.render_cards()
        self.search()

    def more(self):
        if self.worker and self.worker.isRunning():
            self.status.setText("正在发现音乐，请稍候再翻页")
            return
        self.page += 1
        self.search()

    def search(self):
        if self.worker and self.worker.isRunning():
            self.status.setText("正在发现音乐，请稍候…")
            return
        self.status.setText(f"正在从哔哩哔哩发现第 {self.page} 页…")
        self.search_error = ""
        self.worker = SearchWorker(self.page, self.settings["search_terms"])
        self.worker.batch.connect(self.add_batch)
        self.worker.failed.connect(self.on_search_error)
        self.worker.finished.connect(self.on_search_finished)
        self.worker.start()

    def on_search_error(self, message):
        self.search_error = message

    def on_search_finished(self):
        if self.pending_refresh:
            self.pending_refresh = False
            self.page = 1
            self.items.clear()
            self.render_cards()
            QTimer.singleShot(0, self.search)
            return
        if self.search_error:
            self.status.setText(f"搜索暂时未完成：{self.search_error}")
        else:
            self.status.setText(f"已收录 {len(self.items)} 个符合标题条件的视频")

    def shutdown(self):
        if self._hotkey_registered and os.name == "nt":
            ctypes.windll.user32.UnregisterHotKey(int(self.winId()), 0x5346)
            self._hotkey_registered = False
        self.mini_capsule.hide()
        self.mini_capsule.set_playing(False)
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(15000)
        for worker in list(self.media_workers):
            if worker.isRunning():
                worker.requestInterruption()
                worker.wait(30000)
        self.player.stop()
        if self.proxy:
            self.proxy.close()
            self.proxy = None

    def add_batch(self, batch):
        known = {x["bvid"] for x in self.items}
        self.items.extend(x for x in batch if x["bvid"] not in known)
        self.render_cards()

    def render_cards(self):
        while self.cards.count():
            slot = self.cards.takeAt(0)
            if slot.widget():
                slot.widget().deleteLater()
        query = self.query.text().strip().lower()
        shown = [x for x in self.items if query in x["title"].lower()]
        show_feature = bool(self.items and not query)
        if show_feature:
            item = self.items[0]
            self.feature_title.setText(item["title"])
            self.feature_meta.setText(f"{item['author']}  ·  {item['duration']}")
            pix = QPixmap()
            if item.get("image") and pix.loadFromData(item["image"]):
                self.feature_cover.setPixmap(pix.scaled(218, 123, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            else:
                self.feature_cover.setPixmap(placeholder_cover().scaled(218, 123, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.featured.show()
        else:
            self.featured.hide()
        grid_items = shown[1:] if show_feature else shown
        cols = max(1, min(3, (self.width() - 80) // 328))
        for number, item in enumerate(grid_items):
            self.cards.addWidget(VideoCard(item, self.play_item, self.toggle_favorite, self.is_favorite(item["bvid"])), number // cols, number % cols)
        if not shown:
            empty = QLabel("正在寻找你的下一首…" if not self.items else "没有匹配的标题")
            empty.setObjectName("muted")
            self.cards.addWidget(empty, 0, 0)

    def render_collection(self, name: str):
        grid, count = self.collection_views[name]
        while grid.count():
            slot = grid.takeAt(0)
            if slot.widget():
                slot.widget().deleteLater()
        rows = self.favorites if name == "favorites" else self.history
        count.setText(f"{len(rows)} 首" if name == "favorites" else f"最近 {len(rows)} 首")
        if not rows:
            empty = QLabel("还没有收藏。遇到喜欢的歌，点一下收藏。" if name == "favorites" else "听过的音乐会出现在这里。")
            empty.setObjectName("muted")
            grid.addWidget(empty, 0, 0)
            return
        current_images = {item["bvid"]: item.get("image") for item in self.items if item.get("image")}
        cols = max(1, min(3, (self.width() - 80) // 328))
        for number, row in enumerate(rows):
            item = dict(row)
            if item["bvid"] in current_images:
                item["image"] = current_images[item["bvid"]]
            grid.addWidget(VideoCard(item, self.play_item, self.toggle_favorite, self.is_favorite(item["bvid"])), number // cols, number % cols)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "cards"):
            self.render_cards()
        if hasattr(self, "collection_views"):
            for name in self.collection_views:
                self.render_collection(name)

    def play_item(self, item):
        try:
            self.index = next(i for i, x in enumerate(self.items) if x["bvid"] == item["bvid"])
        except StopIteration:
            self.items.append(item)
            self.index = len(self.items) - 1
        self.media_token += 1
        token = self.media_token
        for worker in self.media_workers:
            worker.requestInterruption()
        self.player.stop()
        self.ending_handled = False
        self.now_title.setText(item["title"])
        self.favorite_button.setText("已收藏" if self.is_favorite(item["bvid"]) else "收藏")
        self.now_meta.setText(f"{item['author']}  ·  {item['duration']}  ·  哔哩哔哩")
        self.transition_to(1)
        self.video_stack.setCurrentIndex(0)
        self.player_hint.setText("正在连接视频…")
        self.status.setText(f"正在获取：{item['title']}")
        worker = MediaWorker(item["bvid"], self.cache_dir, token, cover_url(item.get("pic", "")) if not item.get("image") else "")
        self.media_workers.append(worker)
        worker.ready.connect(lambda path, t=token: self.on_media_ready(t, path))
        worker.failed.connect(lambda message, t=token: self.on_media_error(t, message))
        worker.cover_ready.connect(lambda data, t=token: self.on_cover_ready(t, data))
        worker.finished.connect(lambda w=worker: self.on_media_finished(w))
        worker.start()

    def on_media_finished(self, worker):
        if worker in self.media_workers:
            self.media_workers.remove(worker)
        worker.deleteLater()

    def on_media_ready(self, token: int, source: dict):
        if token != self.media_token:
            return
        if "path" in source:
            address = QUrl.fromLocalFile(source["path"])
        else:
            if self.proxy is None:
                self.proxy = StreamProxy(self.cache_dir)
            address = QUrl(self.proxy.add(source["bvid"], source["url"], source["size"]))
        self.video_stack.setCurrentIndex(1)
        self.player.setSource(address)
        self.player.play()
        self.mini_capsule.set_track(self.items[self.index])
        self.update_capsule()
        self.status.setText(f"正在缓冲并播放：{self.items[self.index]['title']}")

    def on_media_error(self, token: int, message: str):
        if token == self.media_token:
            self.player_hint.setText("这首暂时没有取得播放文件")
            self.status.setText(f"播放准备失败：{message}")

    def on_cover_ready(self, token: int, data: bytes):
        if token == self.media_token and self.index >= 0:
            bvid = self.items[self.index]["bvid"]
            self.items[self.index]["image"] = data
            changed = False
            for row in self.favorites + self.history:
                if row["bvid"] == bvid:
                    row["image"] = data
                    changed = True
            if changed:
                self.save_library()
                self.render_collection("favorites")
                self.render_collection("history")
            self.mini_capsule.cover.set_image(data)

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and not self.ending_handled:
            self.ending_handled = True
            if self.settings["playback_mode"] == "repeat":
                self.player.setPosition(0)
                self.player.play()
                self.ending_handled = False
            else:
                self.next_video()

    def on_playback_error(self, error, message):
        if error != QMediaPlayer.Error.NoError:
            self.status.setText(f"播放器提示：{message}")

    def on_playback_state(self, state):
        self.play_button.setText("暂停" if state == QMediaPlayer.PlaybackState.PlayingState else "播放")
        if state == QMediaPlayer.PlaybackState.PlayingState and self.index >= 0 and self.history_token != self.media_token:
            self.history_token = self.media_token
            self.record_history(self.items[self.index])
        self.update_capsule()

    def update_capsule(self):
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        visible = bool(self.settings["floating"] and self.index >= 0 and playing)
        if visible:
            self.mini_capsule.show()
        else:
            self.mini_capsule.hide()
        self.mini_capsule.set_playing(visible)

    @staticmethod
    def format_time(milliseconds: int) -> str:
        seconds = max(0, milliseconds // 1000)
        return f"{seconds // 60}:{seconds % 60:02d}"

    def on_position(self, position: int):
        if not self.seek.isSliderDown():
            self.seek.setValue(position)
        self.elapsed.setText(self.format_time(position))

    def on_duration(self, duration: int):
        self.seek.setRange(0, max(0, duration))
        self.total.setText(self.format_time(duration))

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        elif not self.player.source().isEmpty():
            self.player.play()

    def next_video(self):
        if not self.items:
            return
        mode = "random" if self.settings["playback_mode"] == "random" else "continue"
        self.index = playback_next(self.index, len(self.items), mode)
        self.play_item(self.items[self.index])

    def previous(self):
        if not self.items:
            return
        self.index = (self.index - 1) % len(self.items)
        self.play_item(self.items[self.index])


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("司凤星球")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    app.aboutToQuit.connect(window.shutdown)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
