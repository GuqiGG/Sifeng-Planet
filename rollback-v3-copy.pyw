#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""司凤星球 · a compact Bilibili music-video listening desk."""

from __future__ import annotations

import html
import json
import re
import sys
import os
from functools import lru_cache
from pathlib import Path

KEYWORDS = ("司凤版", "司凤", "隆德齐")
API = "https://api.bilibili.com/x/web-interface/search/type"
PAGELIST_API = "https://api.bilibili.com/x/player/pagelist"
PLAYURL_API = "https://api.bilibili.com/x/player/playurl"


def clean_title(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def permitted(title: str) -> bool:
    return any(word in title for word in KEYWORDS)


def normalize_results(rows: list[dict], seen: set[str]) -> list[dict]:
    found = []
    for row in rows:
        title, bvid = clean_title(row.get("title", "")), str(row.get("bvid", ""))
        if not re.fullmatch(r"BV[0-9A-Za-z]+", bvid) or not permitted(title) or bvid in seen:
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
    assert select_mp4({"code": 0, "data": {"durl": [{"url": "https://example.test/v.mp4", "size": 12}]}}) == ("https://example.test/v.mp4", 12)
    print("MODIFIED: title filter, MP4 selection, repeat and next-index PASS")


if "--self-test" in sys.argv:
    self_test()
    raise SystemExit(0)

import requests
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QUrl, QEvent
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPen, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QScrollArea, QSlider,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget, QMenu,
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

    def __init__(self, page: int):
        super().__init__()
        self.page = page

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
            for keyword in KEYWORDS:
                response = session.get(API, params={"search_type": "video", "keyword": keyword, "page": self.page}, headers=headers, timeout=12)
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") != 0:
                    raise RuntimeError(f"哔哩哔哩搜索返回 {payload.get('code')}: {payload.get('message', '')}")
                rows = (payload.get("data") or {}).get("result") or []
                items = normalize_results(rows, seen)
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


class MediaWorker(QThread):
    ready = Signal(str)
    progress = Signal(int)
    failed = Signal(str)

    def __init__(self, bvid: str, cache_dir: Path, token: int):
        super().__init__()
        self.bvid = bvid
        self.cache_dir = cache_dir
        self.token = token

    def run(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        final = self.cache_dir / f"{self.bvid}.mp4"
        partial = self.cache_dir / f"{self.bvid}.{self.token}.part"
        if final.exists() and final.stat().st_size > 10_000:
            self.ready.emit(str(final))
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
            with session.get(url, headers=headers, stream=True, timeout=(10, 25)) as stream:
                stream.raise_for_status()
                total = size or int(stream.headers.get("Content-Length") or 0)
                count = 0
                with partial.open("wb") as output:
                    for chunk in stream.iter_content(chunk_size=131072):
                        if self.isInterruptionRequested():
                            return
                        if chunk:
                            output.write(chunk)
                            count += len(chunk)
                            if total:
                                self.progress.emit(min(99, round(count * 100 / total)))
            if count < 10_000 or (size and count != size):
                raise ValueError("视频文件未完整下载")
            partial.replace(final)
            self.prune_cache(final)
            self.ready.emit(str(final))
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
        finally:
            session.close()
            try:
                partial.unlink(missing_ok=True)
            except OSError:
                pass

    def prune_cache(self, keep: Path):
        files = sorted(self.cache_dir.glob("BV*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        total = 0
        for path in files:
            if path == keep:
                total += path.stat().st_size
                continue
            size = path.stat().st_size
            if total + size <= 150_000_000:
                total += size
            else:
                try:
                    path.unlink()
                except OSError:
                    pass


class VideoCard(QFrame):
    def __init__(self, item: dict, on_play):
        super().__init__()
        self.setObjectName("videoCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.item = item
        self.on_play = on_play
        self.setFixedWidth(312)
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
        layout.addWidget(cover)
        title = QLabel(item["title"])
        title.setWordWrap(True)
        title.setMaximumHeight(42)
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        meta = QLabel(f"{item['author']}  ·  {item['duration']}")
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
        brand = QLabel("司凤星球")
        brand.setObjectName("brand")
        row.addWidget(brand)
        row.addStretch()
        row.addWidget(owner.button("发现", owner.show_home))
        row.addWidget(owner.button("正在播放", owner.show_player))
        row.addWidget(owner.button("偏好设置", owner.toggle_preferences))
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
        self.search_error = ""
        self.ending_handled = False
        self.settings_path = Path.home() / "AppData" / "Roaming" / "SiFengPlanet" / "settings.json"
        self.repeat = self.load_repeat()
        self.build_ui()
        self.setup_tray()
        QTimer.singleShot(250, self.search)

    def load_repeat(self) -> bool:
        try:
            return bool(json.loads(self.settings_path.read_text(encoding="utf-8")).get("repeat", False))
        except (OSError, ValueError, TypeError):
            return False

    def save_repeat(self, value: bool):
        self.repeat = value
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps({"repeat": value}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            self.status.setText("偏好设置暂未保存")

    def button(self, label: str, callback, primary: bool = False) -> QPushButton:
        btn = QPushButton(label)
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
        QLabel#cover { background: #f2f2f4; color: #bbbcc2; border-radius: 12px; font-size: 45px; }
        QFrame#videoCard { background: #ffffff; border: 1px solid transparent; border-radius: 16px; }
        QFrame#videoCard:hover { background: #fafafa; border-color: #ededf0; }
        QFrame#heroPanel { background: #ffffff; border: none; }
        QPushButton { background: transparent; border: none; border-radius: 12px; padding: 9px 14px; color: #55555b; font-weight: 650; }
        QPushButton:hover { background: #f3f3f5; color: #151518; }
        QPushButton#primary { background: #1b1b1e; color: white; }
        QPushButton#primary:hover { background: #3a3a40; }
        QPushButton#chrome, QPushButton#chromeClose { background: transparent; border: none; border-radius: 9px; padding: 0; }
        QPushButton#chrome:hover { background: #f0f0f2; }
        QPushButton#chromeClose:hover { background: #ffe8eb; }
        QLineEdit { background: #f4f4f5; color: #17171a; border: 1px solid #f4f4f5; border-radius: 12px; padding: 10px 14px; }
        QLineEdit:focus { border-color: #c9c9cf; }
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
        h.setContentsMargins(0, 18, 0, 24)
        eyebrow = QLabel("SIFENG RADIO  /  BILIBILI")
        eyebrow.setObjectName("eyebrow")
        h.addWidget(eyebrow)
        title = QLabel("只听喜欢的。")
        title.setObjectName("hero")
        h.addWidget(title)
        line = QLabel("司凤版、司凤与隆德齐。轻轻点开，音乐就开始了。")
        line.setWordWrap(True)
        line.setObjectName("muted")
        h.addWidget(line)
        v.addWidget(hero)
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
        self.cards.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
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
        v = QVBoxLayout(page)
        v.setAlignment(Qt.AlignmentFlag.AlignTop)
        v.setContentsMargins(30, 35, 30, 30)
        v.setSpacing(20)
        title = QLabel("偏好设置")
        title.setObjectName("hero")
        v.addWidget(title)
        v.addWidget(QLabel("视频结束后"))
        self.repeat_box = QCheckBox("重播当前视频")
        self.repeat_box.setChecked(self.repeat)
        self.repeat_box.toggled.connect(self.save_repeat)
        v.addWidget(self.repeat_box)
        hint = QLabel("默认接着播放下一首。关闭窗口会收起到系统托盘，播放不会中断。")
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        v.addWidget(hint)
        v.addWidget(self.button("返回发现", self.show_home), 0, Qt.AlignmentFlag.AlignLeft)
        self.stack.addWidget(page)

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
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def closeEvent(self, event):
        if self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage("司凤星球还在播放", "双击托盘图标可重新打开。", QSystemTrayIcon.MessageIcon.Information, 2500)
        else:
            event.accept()

    def reopen(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def show_home(self):
        self.stack.setCurrentIndex(0)

    def show_player(self):
        self.stack.setCurrentIndex(1)

    def toggle_preferences(self):
        self.stack.setCurrentIndex(0 if self.stack.currentIndex() == 2 else 2)

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
        self.worker = SearchWorker(self.page)
        self.worker.batch.connect(self.add_batch)
        self.worker.failed.connect(self.on_search_error)
        self.worker.finished.connect(self.on_search_finished)
        self.worker.start()

    def on_search_error(self, message):
        self.search_error = message

    def on_search_finished(self):
        if self.search_error:
            self.status.setText(f"搜索暂时未完成：{self.search_error}")
        else:
            self.status.setText(f"已收录 {len(self.items)} 个符合标题条件的视频")

    def shutdown(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(15000)
        for worker in list(self.media_workers):
            if worker.isRunning():
                worker.requestInterruption()
                worker.wait(30000)
        self.player.stop()

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
        cols = max(1, min(3, (self.width() - 80) // 328))
        for number, item in enumerate(shown):
            self.cards.addWidget(VideoCard(item, self.play_item), number // cols, number % cols)
        if not shown:
            empty = QLabel("正在寻找你的下一首…" if not self.items else "没有匹配的标题")
            empty.setObjectName("muted")
            self.cards.addWidget(empty, 0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "cards"):
            self.render_cards()

    def play_item(self, item):
        try:
            self.index = next(i for i, x in enumerate(self.items) if x["bvid"] == item["bvid"])
        except StopIteration:
            return
        self.media_token += 1
        token = self.media_token
        for worker in self.media_workers:
            worker.requestInterruption()
        self.player.stop()
        self.ending_handled = False
        self.now_title.setText(item["title"])
        self.now_meta.setText(f"{item['author']}  ·  {item['duration']}  ·  哔哩哔哩")
        self.stack.setCurrentIndex(1)
        self.video_stack.setCurrentIndex(0)
        self.player_hint.setText("正在准备播放…")
        self.status.setText(f"正在获取：{item['title']}")
        worker = MediaWorker(item["bvid"], self.cache_dir, token)
        self.media_workers.append(worker)
        worker.ready.connect(lambda path, t=token: self.on_media_ready(t, path))
        worker.progress.connect(lambda percent, t=token: self.on_media_progress(t, percent))
        worker.failed.connect(lambda message, t=token: self.on_media_error(t, message))
        worker.finished.connect(lambda w=worker: self.on_media_finished(w))
        worker.start()

    def on_media_finished(self, worker):
        if worker in self.media_workers:
            self.media_workers.remove(worker)
        worker.deleteLater()

    def on_media_progress(self, token: int, percent: int):
        if token == self.media_token:
            self.player_hint.setText(f"正在准备播放… {percent}%")

    def on_media_ready(self, token: int, path: str):
        if token != self.media_token:
            return
        self.video_stack.setCurrentIndex(1)
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.status.setText(f"正在播放：{self.items[self.index]['title']}")

    def on_media_error(self, token: int, message: str):
        if token == self.media_token:
            self.player_hint.setText("这首暂时没有取得播放文件")
            self.status.setText(f"播放准备失败：{message}")

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and not self.ending_handled:
            self.ending_handled = True
            if self.repeat:
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
        self.index = next_index(self.index, len(self.items), False)
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
