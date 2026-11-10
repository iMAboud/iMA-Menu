# -*- coding: utf-8 -*-
import os
import sys
import json
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QPointF, Qt, QRectF, QEvent, QEasingCurve, QVariantAnimation
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtWidgets import QWidget

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
SEEN_FILE = os.path.join(CACHE_DIR, 'seen_state.json')

TAB_CATEGORIES = {
    'nav.plugins': ('plugins', 'apps'),
    'plugins.store': ('plugins',),
    'plugins.apps': ('apps',),
    'nav.theme': ('themes',),
    'theme.themes': ('themes',),
    'themes.explore': ('themes',),
    'nav.mouse': ('cursors',),
    'theme.mouse': ('cursors',),
    'cursors.explore': ('cursors',),
}

DOT_COLOR = QColor(231, 130, 132)


def collect_known_cursors(cursor_dir=None, *catalog_sources) -> list:
    lower_map = {}
    for src in catalog_sources:
        data = None
        if isinstance(src, dict):
            data = src
        elif isinstance(src, str) and os.path.isfile(src):
            try:
                with open(src, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = None
        if isinstance(data, dict):
            for k in data.keys():
                ks = str(k)
                if ks.lower() != 'windows default':
                    lower_map[ks.lower()] = ks

    if cursor_dir and os.path.isdir(cursor_dir):
        try:
            for entry in sorted(os.listdir(cursor_dir)):
                full_p = os.path.join(cursor_dir, entry)
                if os.path.isdir(full_p) and entry.lower() != 'windows default' and not entry.startswith('.'):
                    lower_map[entry.lower()] = entry
        except Exception:
            pass

    return list(lower_map.values())


def paint_dot(p: QPainter, center: QPointF, t: float):
    if t <= 0.001:
        return
    p.save()
    p.setRenderHint(QPainter.Antialiasing)

    # Outer soft halo
    halo_alpha = int(55 * t)
    if halo_alpha > 0:
        halo_r = 6.5 * (0.8 + 0.2 * t)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(231, 130, 132, halo_alpha))
        p.drawEllipse(center, halo_r, halo_r)

    # Core dot with subtle 1px border
    core_alpha = int(255 * min(1.0, t * 1.2))
    core_r = 3.5 * (0.7 + 0.3 * t)
    p.setPen(QPen(QColor(18, 18, 18, int(200 * t)), 1.0))
    p.setBrush(QColor(231, 130, 132, core_alpha))
    p.drawEllipse(center, core_r, core_r)
    p.restore()


class SeenTracker(QObject):
    changed = pyqtSignal()
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = SeenTracker()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._seen = {}
        self._acked = {}
        self._current_items = {}
        self._active_tabs = set()
        self._dirty = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1000)
        self._save_timer.timeout.connect(self._save_to_disk)

        self._load()

    def _load(self):
        if os.path.exists(SEEN_FILE):
            try:
                with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._seen = data.get('seen', {})
                    self._acked = data.get('acked', {})
            except Exception:
                self._seen = {}
                self._acked = {}

    def _save_debounced(self):
        self._dirty = True
        if not self._save_timer.isActive():
            self._save_timer.start()

    def _save_to_disk(self):
        if not self._dirty:
            return
        self._dirty = False
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = SEEN_FILE + '.tmp'
            payload = {
                'v': 1,
                'seen': self._seen,
                'acked': self._acked
            }
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp, SEEN_FILE)
        except Exception:
            pass

    def flush(self):
        if self._save_timer.isActive():
            self._save_timer.stop()
        self._save_to_disk()

    def report(self, category: str, items):
        if isinstance(items, (list, set, tuple)):
            items_dict = {str(k): "" for k in items}
        elif isinstance(items, dict):
            items_dict = {str(k): str(v or "") for k, v in items.items()}
        else:
            return

        prev_cur = dict(self._current_items.get(category, {}))
        prev_lower = {k.lower(): k for k in prev_cur}
        for k, v in items_dict.items():
            kl = k.lower()
            if kl in prev_lower and prev_lower[kl] != k:
                old_v = prev_cur.pop(prev_lower[kl], "")
                prev_cur[k] = v or old_v
            else:
                prev_cur[k] = v or prev_cur.get(k, "")
            prev_lower[kl] = k

        self._current_items[category] = prev_cur

        # First time seeing this category: establish baseline with zero dots
        if category not in self._seen:
            self._seen[category] = dict(prev_cur)
            self._save_debounced()
            return

        seen_cat = self._seen[category]
        seen_lower = {sk.lower(): sk for sk in seen_cat}

        # Normalize casing and backfill initial version if item was seeded without version metadata ("")
        for k, v in prev_cur.items():
            kl = k.lower()
            if kl in seen_lower:
                sk = seen_lower[kl]
                if sk != k:
                    seen_cat[k] = seen_cat.pop(sk, "")
                    seen_lower[kl] = k
                    self._dirty = True
                if v and not seen_cat.get(k):
                    seen_cat[k] = v
                    self._dirty = True

        # Auto-ack active tabs for any new or updated items
        for tab_id in self._active_tabs:
            if category in TAB_CATEGORIES.get(tab_id, ()):
                self.visit_tab(tab_id)

        self._save_debounced()
        self.changed.emit()

    def is_unseen(self, category: str, item_id: str) -> bool:
        item_id = str(item_id)
        seen_cat = self._seen.get(category)
        if seen_cat is None:
            return False
        cur_items = self._current_items.get(category, {})
        item_lower = item_id.lower()

        cur_key = item_id if item_id in cur_items else next((ck for ck in cur_items if ck.lower() == item_lower), None)
        if cur_key is None:
            return False

        seen_key = item_id if item_id in seen_cat else next((sk for sk in seen_cat if sk.lower() == item_lower), None)
        if seen_key is None:
            return True

        cur_ver = cur_items.get(cur_key)
        if cur_ver and seen_cat.get(seen_key) != cur_ver:
            return True
        return False

    def mark_seen(self, category: str, item_id: str):
        item_id = str(item_id)
        if category not in self._seen:
            self._seen[category] = {}
        cur_items = self._current_items.get(category, {})
        item_lower = item_id.lower()
        cur_key = item_id if item_id in cur_items else next((ck for ck in cur_items if ck.lower() == item_lower), item_id)
        cur_ver = cur_items.get(cur_key, "")

        seen_cat = self._seen[category]
        for sk in [k for k in seen_cat if k.lower() == item_lower and k != item_id]:
            seen_cat.pop(sk, None)
        seen_cat[item_id] = cur_ver

        prefix_lower = f"{category}:{item_lower}"
        for tab_id, keys in list(self._acked.items()):
            self._acked[tab_id] = [
                k for k in keys
                if not (k.lower().startswith(f"{prefix_lower}@") or k.lower() == prefix_lower)
            ]

        self._save_debounced()
        self.changed.emit()

    def visit_tab(self, tab_id: str):
        cats = TAB_CATEGORIES.get(tab_id, ())
        if not cats:
            return
        if tab_id not in self._acked:
            self._acked[tab_id] = []

        existing_lower = {k.lower() for k in self._acked[tab_id]}
        modified = False
        for cat in cats:
            for item_id, cur_ver in self._current_items.get(cat, {}).items():
                if self.is_unseen(cat, item_id):
                    key = f"{cat}:{item_id}@{cur_ver}"
                    if key.lower() not in existing_lower:
                        self._acked[tab_id].append(key)
                        existing_lower.add(key.lower())
                        modified = True
        if modified:
            self._save_debounced()
            self.changed.emit()

    def set_active_tabs(self, tab_ids):
        self._active_tabs = set(tab_ids)
        for tid in self._active_tabs:
            self.visit_tab(tid)
        self.changed.emit()

    def tab_has_dot(self, tab_id: str) -> bool:
        if tab_id in self._active_tabs:
            return False
        cats = TAB_CATEGORIES.get(tab_id, ())
        if not cats:
            return False
        acked_lower = {k.lower() for k in self._acked.get(tab_id, [])}
        for cat in cats:
            for item_id, cur_ver in self._current_items.get(cat, {}).items():
                if self.is_unseen(cat, item_id):
                    key = f"{cat}:{item_id}@{cur_ver}"
                    if key.lower() not in acked_lower:
                        return True
        return False


class NewDot(QWidget):
    def __init__(self, parent, category: str, item_id: str, anchor: str = 'top_right'):
        super().__init__(parent)
        self.category = category
        self.item_id = str(item_id)
        self.anchor = anchor
        self._t = 0.0
        self._anim = None

        self.setFixedSize(16, 16)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._dwell_timer = QTimer(self)
        self._dwell_timer.setSingleShot(True)
        self._dwell_timer.timeout.connect(self._on_dwell_timeout)

        if parent:
            parent.installEventFilter(self)

        SeenTracker.instance().changed.connect(self._sync_state)
        self.hide()
        self._sync_state()

    def _sync_state(self):
        unseen = SeenTracker.instance().is_unseen(self.category, self.item_id)
        if unseen:
            self._reposition()
            if not self.isVisible() or self._t < 1.0:
                self.show()
                self.raise_()
                self._animate_to(1.0, 220, QEasingCurve.OutBack)
        else:
            if self.isVisible() and self._t > 0.0:
                self._animate_to(0.0, 120, QEasingCurve.OutCubic, on_finished=self.hide)
            elif not self.isVisible():
                self._t = 0.0

    def _reposition(self):
        p = self.parent()
        if not p:
            return
        pw = p.width()
        if self.anchor == 'top_right':
            self.move(pw - self.width() - 8, 8)
        elif self.anchor == 'top_center':
            self.move((pw - self.width()) // 2, 8)
        elif self.anchor == 'top_left':
            self.move(8, 8)

    def _animate_to(self, target: float, duration: int, easing: QEasingCurve.Type, on_finished=None):
        if self._anim:
            self._anim.stop()
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(duration)
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(target)
        self._anim.setEasingCurve(easing)
        self._anim.valueChanged.connect(self._on_anim_val)
        if on_finished:
            self._anim.finished.connect(on_finished)
        self._anim.start()

    def _on_anim_val(self, val):
        self._t = float(val)
        self.update()

    def _on_dwell_timeout(self):
        SeenTracker.instance().mark_seen(self.category, self.item_id)

    def eventFilter(self, obj, event):
        if obj == self.parent():
            etype = event.type()
            if etype == QEvent.Resize:
                self._reposition()
            elif etype == QEvent.Enter:
                if SeenTracker.instance().is_unseen(self.category, self.item_id):
                    self._dwell_timer.start(50)
            elif etype == QEvent.Leave:
                self._dwell_timer.stop()
            elif etype == QEvent.MouseButtonPress:
                if SeenTracker.instance().is_unseen(self.category, self.item_id):
                    self._dwell_timer.stop()
                    SeenTracker.instance().mark_seen(self.category, self.item_id)
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        if self._t > 0.001:
            p = QPainter(self)
            paint_dot(p, QPointF(self.width() / 2.0, self.height() / 2.0), self._t)
