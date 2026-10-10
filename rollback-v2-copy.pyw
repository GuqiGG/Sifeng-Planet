#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""司凤星球 · a compact Bilibili music-video listening desk."""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

KEYWORDS = ("司凤版", "司凤", "隆德齐")
API = "https://api.bilibili.com/x/web-interface/search/type"


def clean_title(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def permitted(title: str) -> bool:
    return any(word in title for word in KEYWORDS)


def normalize_results(rows: list[dict], seen: set[str]) -> list[dict]:
    found = []
    for row in rows:
        title, bvid = clean_title(row.get("title", "")), str(row.get("bvid", ""))
        if not bvid.startswith("BV") or not permitted(title) or bvid in seen:
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
    print("MODIFIED: title filter, deduplication, repeat and next-index PASS")


if "--self-test" in sys.argv:
    self_test()
    raise SystemExit(0)

import requests
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QUrl
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget, QMenu,
)
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


def app_icon() -> QIcon:
    saved = Path(__file__).with_name("sifeng_planet.ico")
    if saved.exists():
        return QIcon(str(saved))
    pix = QPixmap(128, 128)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#8568ff"))
    p.drawRoundedRect(5, 5, 118, 118, 35, 35)
    p.setBrush(QColor("#b6e8ff"))
    p.drawEllipse(17, 16, 94, 94)
    p.setBrush(QColor("#211b39"))
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
        layout.setSpacing(9)
        cover = QLabel()
        cover.setFixedSize(292, 164)
        cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover.setObjectName("cover")
        pix = QPixmap()
        if item.get("image") and pix.loadFromData(item["image"]):
            cover.setPixmap(pix.scaled(292, 164, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        else:
            cover.setText("♫")
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("司凤星球 · 听见喜欢")
        self.setWindowIcon(app_icon())
        self.resize(1110, 760)
        self.setMinimumSize(770, 570)
        self.items: list[dict] = []
        self.index = -1
        self.page = 1
        self.worker = None
        self.search_error = ""
        self.ending_handled = False
        self.settings_path = Path.home() / "AppData" / "Roaming" / "SiFengPlanet" / "settings.json"
        self.repeat = self.load_repeat()
        self.build_ui()
        self.setup_tray()
        self.timer = QTimer(self)
        self.timer.setInterval(1200)
        self.timer.timeout.connect(self.poll_video)
        self.timer.start()
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
        outer.setContentsMargins(28, 20, 28, 22)
        outer.setSpacing(18)

        bar = QHBoxLayout()
        brand = QLabel("◉  司凤星球")
        brand.setObjectName("brand")
        bar.addWidget(brand)
        bar.addStretch()
        self.home_btn = self.button("发现", self.show_home)
        bar.addWidget(self.home_btn)
        self.player_btn = self.button("正在播放", self.show_player)
        bar.addWidget(self.player_btn)
        self.pref_btn = self.button("偏好设置", self.toggle_preferences)
        bar.addWidget(self.pref_btn)
        outer.addLayout(bar)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)
        self.build_home()
        self.build_player()
        self.build_preferences()

        self.status = QLabel("准备发现音乐…")
        self.status.setObjectName("muted")
        outer.addWidget(self.status)
        self.setStyleSheet("""
        QWidget#root { background: #12101d; color: #f5f2ff; font-family: 'Microsoft YaHei UI'; font-size: 13px; }
        QLabel { color: #f5f2ff; }
        QLabel#brand { font-size: 24px; font-weight: 800; color: #d9cbff; }
        QLabel#hero { font-size: 30px; font-weight: 800; }
        QLabel#section { font-size: 18px; font-weight: 700; }
        QLabel#muted { color: #aaa5bf; font-size: 11px; }
        QLabel#cardTitle { font-size: 13px; font-weight: 650; }
        QLabel#cover { background: #25203a; color: #a98eff; border-radius: 12px; font-size: 47px; }
        QFrame#videoCard { background: #211c32; border: 1px solid #383047; border-radius: 18px; }
        QFrame#videoCard:hover { background: #302747; border-color: #8469df; }
        QFrame#heroPanel { background: #352452; border: 1px solid #655180; border-radius: 22px; }
        QPushButton { background: #2b253c; border: 1px solid #433755; border-radius: 13px; padding: 9px 16px; color: #f3edff; font-weight: 650; }
        QPushButton:hover { background: #45365e; }
        QPushButton#primary { background: #9568ef; border-color: #9568ef; color: #160e25; }
        QPushButton#primary:hover { background: #b18cff; }
        QLineEdit { background: #211c32; color: white; border: 1px solid #514364; border-radius: 12px; padding: 10px 14px; }
        QScrollArea { border: none; background: transparent; }
        QScrollArea QWidget { background: transparent; }
        QCheckBox { spacing: 12px; font-size: 15px; }
        QCheckBox::indicator { width: 20px; height: 20px; }
        """)

    def build_home(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(15)
        hero = QFrame()
        hero.setObjectName("heroPanel")
        h = QVBoxLayout(hero)
        h.setContentsMargins(24, 20, 24, 20)
        title = QLabel("把喜欢的声音，留在这里。")
        title.setObjectName("hero")
        h.addWidget(title)
        line = QLabel("只收录标题含「司凤版」「司凤」「隆德齐」的视频 · 点开即播 · 听完接着听")
        line.setWordWrap(True)
        h.addWidget(line)
        v.addWidget(hero)
        controls = QHBoxLayout()
        label = QLabel("为你发现")
        label.setObjectName("section")
        controls.addWidget(label)
        controls.addStretch()
        self.query = QLineEdit()
        self.query.setPlaceholderText("在已筛选的标题中找一找…")
        self.query.setFixedWidth(270)
        self.query.textChanged.connect(self.render_cards)
        controls.addWidget(self.query)
        controls.addWidget(self.button("刷新", self.refresh, True))
        v.addLayout(controls)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.cards_host = QWidget()
        self.cards = QGridLayout(self.cards_host)
        self.cards.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.cards.setSpacing(16)
        scroll.setWidget(self.cards_host)
        v.addWidget(scroll, 1)
        more = self.button("发现更多 ↓", self.more)
        v.addWidget(more, 0, Qt.AlignmentFlag.AlignHCenter)
        self.stack.addWidget(page)

    def build_player(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(11)
        self.now_title = QLabel("选一首，开始听。")
        self.now_title.setObjectName("section")
        self.now_title.setWordWrap(True)
        v.addWidget(self.now_title)
        self.now_meta = QLabel("来自哔哩哔哩")
        self.now_meta.setObjectName("muted")
        v.addWidget(self.now_meta)
        self.web = None  # Do not start Chromium until the first play request.
        self.player_container = QWidget()
        self.player_layout = QVBoxLayout(self.player_container)
        self.player_layout.setContentsMargins(0, 0, 0, 0)
        self.player_hint = QLabel("♫  点一首歌，开始播放")
        self.player_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.player_hint.setObjectName("hero")
        self.player_layout.addWidget(self.player_hint)
        v.addWidget(self.player_container, 1)
        row = QHBoxLayout()
        row.addWidget(self.button("← 返回发现", self.show_home))
        row.addStretch()
        row.addWidget(self.button("上一首", self.previous))
        row.addWidget(self.button("下一首 →", self.next_video, True))
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
        v.addWidget(QLabel("一首播完以后…"))
        self.repeat_box = QCheckBox("重播当前视频")
        self.repeat_box.setChecked(self.repeat)
        self.repeat_box.toggled.connect(self.save_repeat)
        v.addWidget(self.repeat_box)
        hint = QLabel("关闭时缩到系统托盘，音乐继续播放。托盘菜单可以重新打开或彻底退出。")
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
        self.ending_handled = False
        self.now_title.setText(item["title"])
        self.now_meta.setText(f"{item['author']}  ·  {item['duration']}  ·  哔哩哔哩")
        self.stack.setCurrentIndex(1)
        self.ensure_web()
        self.web.setUrl(QUrl(f"https://player.bilibili.com/player.html?bvid={item['bvid']}&autoplay=1&danmaku=0"))
        self.status.setText(f"正在播放：{item['title']}")

    def ensure_web(self):
        if self.web is not None:
            return
        self.player_hint.deleteLater()
        self.web = QWebEngineView()
        self.web.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        self.web.loadFinished.connect(self.on_player_loaded)
        self.player_layout.addWidget(self.web)

    def on_player_loaded(self, ok: bool):
        if ok:
            QTimer.singleShot(1200, self.try_autoplay)
        else:
            self.status.setText("播放器加载失败，可点下一首再试")

    def try_autoplay(self):
        if self.web:
            self.web.page().runJavaScript("""(()=>{let v=document.querySelector('video'); if(v){v.play().catch(()=>{});return true}return false})()""")

    def poll_video(self):
        if self.index < 0 or self.ending_handled or self.web is None or self.web.url().isEmpty():
            return
        js = """(()=>{let v=document.querySelector('video'); return !!(v && (v.ended || (v.duration>1 && v.paused && v.currentTime>=v.duration-0.4)))})()"""
        self.web.page().runJavaScript(js, self.on_video_end_check)

    def on_video_end_check(self, ended):
        if ended and not self.ending_handled:
            self.ending_handled = True
            if self.repeat:
                self.web.page().runJavaScript("(()=>{let v=document.querySelector('video');if(v){v.currentTime=0;v.play().catch(()=>{});return true}return false})()", self.on_repeat)
            else:
                self.next_video()

    def on_repeat(self, success):
        if success:
            self.ending_handled = False
        else:
            self.play_item(self.items[self.index])

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
