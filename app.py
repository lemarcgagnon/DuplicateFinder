import os
import hashlib
import sys
import zlib
import subprocess  # nosec B404 — used for xdg-open/open, no shell injection
import platform
import difflib
import shutil
import logging
import re
import struct
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QFileDialog, QTreeWidget,
                             QTreeWidgetItem, QSplitter, QTextEdit, QStatusBar,
                             QMessageBox, QComboBox, QMenu, QProgressBar, QFrame,
                             QAction, QMenuBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush
from collections import defaultdict
from translations import LANGUAGES, RTL_LANGUAGES, get_translator

logging.basicConfig(
    filename="app.log", level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

# --- Constants ---

HEAD_SIZE = 4096
TAIL_SIZE = 4096
FUZZY_READ_LIMIT = 100_000
SIMHASH_BITS = 64
LSH_BANDS = 8          # number of bands
LSH_BITS_PER_BAND = 8   # bits per band (BANDS * BITS_PER_BAND = SIMHASH_BITS)

_WORD_RE = re.compile(r'[a-z0-9_]{2,}')


# --- Low-level I/O ---

def _read_bytes(path, offset, size):
    """Read `size` bytes at `offset`. Returns bytes or None on failure."""
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            return f.read(size)
    except OSError:
        return None


def get_sha256(path):
    """Full-content SHA-256."""
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except OSError as e:
        log.warning("sha256 failed for %s: %s", path, e)
        return None


# --- SimHash for fuzzy matching ---

def _shingle_hash64(data):
    """Fast 64-bit hash from two seeded crc32 calls.
    CRC32 alone is 32-bit; combining two with different seeds gives
    64-bit with good distribution — sufficient for SimHash accumulation.
    """
    c1 = zlib.crc32(data) & 0xFFFFFFFF
    c2 = zlib.crc32(data, 0x9E3779B9) & 0xFFFFFFFF
    return c1 | (c2 << 32)


def _tokenize_text(path):
    """Read and tokenize a text file into normalized words.
    Strips punctuation, collapses whitespace — makes fuzzy matching
    robust to reformatting (JSON indentation changes, etc.).
    """
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read(FUZZY_READ_LIMIT).lower()
        tokens = _WORD_RE.findall(text)
        return tokens if len(tokens) >= 10 else None
    except OSError:
        return None


def _text_shingle_hashes(tokens, n=4):
    """Generate 64-bit shingle hashes from a token list (4-gram shingles)."""
    hashes = []
    for i in range(len(tokens) - n + 1):
        s = " ".join(tokens[i:i + n]).encode('utf-8')
        hashes.append(_shingle_hash64(s))
    return hashes


def _binary_shingle_hashes(path, n=8):
    """Generate 64-bit shingle hashes from raw bytes (byte n-grams).
    Catches near-exact binary copies with minor metadata differences.
    Subsamples for performance on large files.
    """
    try:
        with open(path, 'rb') as f:
            data = f.read(FUZZY_READ_LIMIT)
        if len(data) < n + 10:
            return None
        hashes = []
        step = max(1, (len(data) - n) // 15000)
        for i in range(0, len(data) - n, step):
            hashes.append(_shingle_hash64(data[i:i + n]))
        return hashes if len(hashes) >= 5 else None
    except OSError:
        return None


def compute_simhash(shingle_hashes):
    """Compute a 64-bit SimHash from shingle hashes.

    For each bit position, count how many shingles have that bit set vs unset.
    Final bit = 1 if more shingles had it set, 0 otherwise.
    Similar documents produce SimHashes with small Hamming distance.
    """
    v = [0] * SIMHASH_BITS
    for h in shingle_hashes:
        for i in range(SIMHASH_BITS):
            if (h >> i) & 1:
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(SIMHASH_BITS):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def simhash_to_lsh_bands(sh):
    """Split 64-bit SimHash into LSH bands for indexing.

    With 4 bands of 16 bits: two files match if ANY 16-bit band is identical.
    This catches files within Hamming distance ~8 out of 64 bits,
    corresponding to ~87%+ fingerprint similarity.
    """
    bands = []
    for b in range(LSH_BANDS):
        band_val = (sh >> (b * LSH_BITS_PER_BAND)) & ((1 << LSH_BITS_PER_BAND) - 1)
        bands.append(f"SIM-B{b}-{band_val:04x}")
    return bands


def simhash_similarity(sh1, sh2):
    """Estimate similarity from SimHash Hamming distance."""
    xor = sh1 ^ sh2
    hamming = bin(xor).count('1')
    return 1.0 - hamming / SIMHASH_BITS


# --- File Record ---

class FileRecord:
    """Stores metadata and computed match keys for one file."""
    __slots__ = ('path', 'size', 'match_keys', 'simhash')

    def __init__(self, path, size):
        self.path = path
        self.size = size
        self.match_keys = []
        self.simhash = None  # 64-bit SimHash (fuzzy mode only)


# --- Platform Utilities ---

def open_in_file_manager(path):
    """Open a folder in the system's native file manager.

    Security note (Bandit B603/B606/B607): subprocess is called with a list
    (no shell interpolation). The path argument comes from user-selected
    directories within the app — not from untrusted external input.
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)  # nosec B606
        elif system == "Darwin":
            subprocess.Popen(["open", path])  # nosec B603 B607
        else:
            subprocess.Popen(["xdg-open", path])  # nosec B603 B607
    except OSError as e:
        log.warning("Failed to open file manager for %s: %s", path, e)


def keeper_score(path):
    """Score a file path for the smart wizard. Lower = more likely the original to keep."""
    name = os.path.basename(path).lower()
    path_lower = path.lower()
    score = 0.0

    copy_markers = ["copy", "copie", "(1)", "(2)", "(3)", " - copy",
                    "backup", ".bak", ".old", "duplicate", "~"]
    for m in copy_markers:
        if m in name:
            score += 10

    junk_folders = ["alloutput", "test", "tets", "tmp", "temp",
                    "processed", "output", "trash", "old", "archive"]
    for folder in junk_folders:
        if folder in path_lower:
            score += 5

    # Prefer shorter paths (closer to root = more likely canonical)
    score += len(path.split(os.sep)) * 0.5

    # Slight preference for newer files as tiebreaker
    try:
        score -= os.path.getmtime(path) / 1e12
    except OSError:
        pass

    return score


# --- Scan Worker ---

class ScanWorker(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(dict, dict, dict)

    def __init__(self, target_dir, sensitivity):
        super().__init__()
        self.target_dir = target_dir
        self.sensitivity = sensitivity
        self._count = 0

    def _emit(self, msg):
        self._count += 1
        self.progress.emit(msg, self._count)

    def run(self):
        # Phase 1: collect all file entries
        entries = []  # (path, size, rel_folder, is_quarantine)
        f_stats = defaultdict(lambda: {"count": 0, "dupes": 0, "size": 0})

        for root, _, files in os.walk(self.target_dir):
            rel_path = os.path.relpath(root, self.target_dir)
            if rel_path == ".":
                rel_path = os.path.basename(self.target_dir)
            is_q = "_FORENSIC_QUARANTINE" in root
            for fname in files:
                p = os.path.join(root, fname)
                try:
                    sz = os.path.getsize(p)
                    entries.append((p, sz, rel_path, is_q))
                    f_stats[rel_path]["count"] += 1
                    f_stats[rel_path]["size"] += sz
                except OSError:
                    continue

        self._emit(f"Collected {len(entries)} files")

        # Build file records
        file_records = {}
        for p, sz, _rel, _q in entries:
            file_records[p] = FileRecord(p, sz)

        # Phase 2: find duplicates (only among non-quarantine files)
        scannable = [(p, sz) for p, sz, _, is_q in entries if not is_q]

        if self.sensitivity == "Fuzzy":
            match_map = self._find_fuzzy(scannable, file_records)
        else:
            match_map = self._find_exact(scannable, file_records)

        # Phase 3: count dupes per folder (each file counted once)
        dupe_paths = set()
        for paths in match_map.values():
            if len(paths) > 1:
                dupe_paths.update(paths)
        for p in dupe_paths:
            rel_p = os.path.relpath(os.path.dirname(p), self.target_dir)
            if rel_p == ".":
                rel_p = os.path.basename(self.target_dir)
            if rel_p in f_stats:
                f_stats[rel_p]["dupes"] += 1

        self.finished.emit(dict(match_map), dict(f_stats), file_records)

    def _find_exact(self, files, records):
        """Progressive duplicate pipeline: size -> head(4KB) -> tail(4KB) -> hash.

        Strict: full SHA-256 as final confirmation (zero false positives).
        Balanced: stops at head+tail match (fast, near-zero false positives).

        This is the same strategy used by rmlint and jdupes.
        Each stage eliminates non-matching files before doing more I/O.
        """
        match_map = defaultdict(list)

        # Step 1: group by file size — different sizes can never be duplicates
        by_size = defaultdict(list)
        for path, size in files:
            by_size[size].append(path)

        candidates = {sz: paths for sz, paths in by_size.items() if len(paths) > 1}
        n_unique = len(by_size) - len(candidates)
        self._emit(f"Size filter: {n_unique} unique sizes eliminated")

        for size, paths in candidates.items():
            # Step 2: group by first HEAD_SIZE bytes
            by_head = defaultdict(list)
            for p in paths:
                self._emit(f"Head check: {os.path.basename(p)}")
                head = _read_bytes(p, 0, HEAD_SIZE)
                if head is not None:
                    hk = hashlib.sha256(head).digest()[:8]
                    by_head[hk].append(p)

            for head_key, head_paths in by_head.items():
                if len(head_paths) < 2:
                    continue

                # Step 3: group by last TAIL_SIZE bytes (skip if file fits in head)
                if size <= HEAD_SIZE:
                    tail_groups = [(head_key, head_paths)]
                else:
                    by_tail = defaultdict(list)
                    for p in head_paths:
                        tail = _read_bytes(p, max(0, size - TAIL_SIZE), TAIL_SIZE)
                        if tail is not None:
                            tk = hashlib.sha256(tail).digest()[:8]
                            by_tail[tk].append(p)
                    tail_groups = [(tk, tp) for tk, tp in by_tail.items() if len(tp) > 1]

                # Step 4: final verification
                for tail_key, group in tail_groups:
                    if self.sensitivity == "Strict":
                        # Full SHA-256 — definitive, zero false positives
                        by_hash = defaultdict(list)
                        for p in group:
                            self._emit(f"Full hash: {os.path.basename(p)}")
                            h = get_sha256(p)
                            if h:
                                by_hash[h].append(p)
                        for fk, hash_group in by_hash.items():
                            if len(hash_group) > 1:
                                for p in hash_group:
                                    match_map[fk].append(p)
                                    records[p].match_keys.append(fk)
                    else:
                        # Balanced: size + head + tail is sufficient
                        key = f"BAL-{size}-{head_key.hex()}-{tail_key.hex()}"
                        for p in group:
                            match_map[key].append(p)
                            records[p].match_keys.append(key)

        return dict(match_map)

    def _find_fuzzy(self, files, records):
        """SimHash + LSH pipeline for fuzzy duplicate detection.

        1. Tokenize text (or extract byte n-grams for binary files).
        2. Compute 64-bit SimHash from shingle hashes.
        3. Split into 4 LSH bands of 16 bits each.
        4. Files sharing ANY band value are candidate duplicates.

        SimHash approximates cosine similarity of feature vectors.
        Band matching catches files with Hamming distance <= ~8 bits,
        i.e. ~87%+ fingerprint similarity.
        """
        match_map = defaultdict(list)

        for path, size in files:
            self._emit(f"Fuzzy: {os.path.basename(path)}")

            # Try text tokenization first, fall back to binary shingles
            tokens = _tokenize_text(path)
            if tokens:
                shingles = _text_shingle_hashes(tokens)
            else:
                shingles = _binary_shingle_hashes(path)

            if not shingles or len(shingles) < 5:
                # Too small for fuzzy — exact hash fallback
                key = get_sha256(path)
                if key:
                    match_map[key].append(path)
                    records[path].match_keys.append(key)
                continue

            sh = compute_simhash(shingles)
            records[path].simhash = sh
            bands = simhash_to_lsh_bands(sh)
            records[path].match_keys = bands
            for band_key in bands:
                match_map[band_key].append(path)

        # Only keep groups with actual duplicates
        return {k: v for k, v in match_map.items() if len(v) > 1}


# --- UI Components ---

class SortableTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        text1, text2 = self.text(column), other.text(column)
        try:
            if "MB" in text1 or "KB" in text1:
                v1 = float(text1.split()[0]) * (1024 if "MB" in text1 else 1)
                v2 = float(text2.split()[0]) * (1024 if "MB" in text2 else 1)
                return v1 < v2
            return float(text1) < float(text2)
        except ValueError:
            return text1.lower() < text2.lower()


class WasteDonut(QWidget):
    """Small donut chart showing total size vs duplicate waste."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self._total = 0
        self._waste = 0
        self._label = ""
        self.setToolTip("Duplicate waste ratio")

    def set_data(self, total_bytes, waste_bytes):
        self._total = total_bytes
        self._waste = waste_bytes
        if total_bytes > 0:
            pct = waste_bytes / total_bytes * 100
            self._label = f"{pct:.0f}%"
            self.setToolTip(
                f"Duplicate waste: {self._fmt(waste_bytes)} / {self._fmt(total_bytes)} "
                f"({pct:.1f}%)"
            )
        else:
            self._label = ""
            self.setToolTip("No data — run Analyze first")
        self.update()

    @staticmethod
    def _fmt(b):
        if b >= 1024 * 1024 * 1024:
            return f"{b / 1024 / 1024 / 1024:.1f} GB"
        if b >= 1024 * 1024:
            return f"{b / 1024 / 1024:.1f} MB"
        return f"{b / 1024:.0f} KB"

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)

        # Background ring
        p.setPen(QPen(QColor("#ecf0f1"), 5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(rect)

        if self._total > 0:
            # Waste arc (red/orange)
            ratio = min(self._waste / self._total, 1.0)
            span = int(-ratio * 360 * 16)  # negative = clockwise
            color = QColor("#e74c3c") if ratio > 0.3 else QColor("#f39c12") if ratio > 0.1 else QColor("#27ae60")
            p.setPen(QPen(color, 5))
            p.drawArc(rect, 90 * 16, span)

            # Center label
            p.setPen(QPen(QColor("#2c3e50")))
            font = p.font()
            font.setPixelSize(10)
            font.setBold(True)
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter, self._label)

        p.end()


class ForensicVisualInspector(QMainWindow):

    # --- Design tokens (HIG: consistent visual language) ---
    STYLE_PRIMARY = """
        QPushButton {
            background-color: #27ae60; color: white;
            font-weight: bold; font-size: 14px;
            padding: 10px 28px; border: none; border-radius: 4px;
        }
        QPushButton:hover { background-color: #2ecc71; }
        QPushButton:pressed { background-color: #1e8449; }
    """
    STYLE_SECONDARY = """
        QPushButton {
            background-color: #ecf0f1; color: #2c3e50;
            font-weight: bold; font-size: 13px;
            padding: 10px 20px; border: 1px solid #bdc3c7; border-radius: 4px;
        }
        QPushButton:hover { background-color: #d5dbdb; }
        QPushButton:pressed { background-color: #bdc3c7; }
    """
    STYLE_ACCENT = """
        QPushButton {
            background-color: #8e44ad; color: white;
            font-weight: bold; padding: 5px 14px;
            border: none; border-radius: 3px;
        }
        QPushButton:hover { background-color: #9b59b6; }
    """
    STYLE_FLAT = """
        QPushButton {
            background: transparent; color: #2c3e50;
            padding: 4px 10px; border: none;
        }
        QPushButton:hover { background-color: #ecf0f1; border-radius: 3px; }
    """
    STYLE_WARNING = """
        QPushButton {
            background-color: #f39c12; color: white;
            padding: 4px 12px; border: none; border-radius: 3px;
        }
        QPushButton:hover { background-color: #f1c40f; }
    """
    STYLE_DESTRUCTIVE = """
        QPushButton {
            background-color: #c0392b; color: white;
            padding: 4px 12px; border: none; border-radius: 3px;
        }
        QPushButton:hover { background-color: #e74c3c; }
    """

    def __init__(self):
        super().__init__()
        self._lang = "en"
        self.tr_fn = get_translator(self._lang)
        self.setWindowTitle(self.tr_fn("window_title"))
        self.resize(1800, 1000)
        self.match_map = {}
        self.file_records = {}
        self.f_stats = {}
        self.init_ui()

    def init_ui(self):
        t = self.tr_fn
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(6)

        # ============================================================
        # ROW 1 — Target selection
        # ============================================================
        target_row = QHBoxLayout()
        target_row.setSpacing(6)

        self._target_label = QLabel(t("label_target"))
        self._target_label.setStyleSheet("font-weight: bold;")
        target_row.addWidget(self._target_label)

        self.path_input = QLineEdit(os.path.abspath(".."))
        self.path_input.setStyleSheet("padding: 6px; font-size: 13px;")
        self.path_input.setPlaceholderText(t("placeholder_select_directory"))
        self.path_input.textChanged.connect(self.clear_all_data)
        target_row.addWidget(self.path_input, 1)

        self._browse_btn = QPushButton(t("btn_browse"))
        self._browse_btn.setStyleSheet(self.STYLE_SECONDARY)
        self._browse_btn.clicked.connect(self.select_directory)
        target_row.addWidget(self._browse_btn)

        layout.addLayout(target_row)

        # ============================================================
        # ROW 2 — Analysis controls
        # ============================================================
        analysis_row = QHBoxLayout()
        analysis_row.setSpacing(8)

        self._sens_label = QLabel(t("label_sensitivity"))
        self._sens_label.setStyleSheet("color: #7f8c8d;")
        analysis_row.addWidget(self._sens_label)

        # Sensitivity combo: internal values are always English, display is translated
        self._sens_keys = ["Strict", "Balanced", "Fuzzy"]
        self.sens_combo = QComboBox()
        self.sens_combo.addItems([t("combo_strict"), t("combo_balanced"), t("combo_fuzzy")])
        self.sens_combo.setCurrentIndex(1)  # Balanced
        self.sens_combo.setToolTip(t("tooltip_sensitivity"))
        self.sens_combo.setStyleSheet("padding: 4px 8px;")
        self.sens_combo.currentIndexChanged.connect(self.clear_all_data)
        analysis_row.addWidget(self.sens_combo)

        analysis_row.addStretch()

        self._scan_btn = QPushButton(t("btn_analyze"))
        self._scan_btn.setStyleSheet(self.STYLE_PRIMARY)
        self._scan_btn.clicked.connect(self.start_scan)
        analysis_row.addWidget(self._scan_btn)

        layout.addLayout(analysis_row)

        # ============================================================
        # ROW 3 — Progress bar (hidden by default)
        # ============================================================
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # ============================================================
        # ROW 4 — Global actions
        # ============================================================
        global_row = QHBoxLayout()
        global_row.setSpacing(8)

        self.auto_wizard_btn = QPushButton(t("btn_auto_clean"))
        self.auto_wizard_btn.setStyleSheet(self.STYLE_ACCENT)
        self.auto_wizard_btn.setToolTip(t("tooltip_auto_clean"))
        self.auto_wizard_btn.clicked.connect(self.smart_auto_clean)
        global_row.addWidget(self.auto_wizard_btn)

        global_row.addStretch()

        self.open_q_btn = QPushButton(t("btn_open_quarantine"))
        self.open_q_btn.setStyleSheet(self.STYLE_FLAT)
        self.open_q_btn.clicked.connect(self.open_quarantine_folder)
        global_row.addWidget(self.open_q_btn)

        self.purge_q_btn = QPushButton(t("btn_empty_quarantine"))
        self.purge_q_btn.setStyleSheet(self.STYLE_DESTRUCTIVE)
        self.purge_q_btn.clicked.connect(self.purge_quarantine)
        global_row.addWidget(self.purge_q_btn)

        layout.addLayout(global_row)

        # ============================================================
        # MAIN CONTENT — Split view
        # ============================================================
        self.main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.main_splitter, 1)

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.top_splitter)

        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels([
            t("tree_folder"), t("tree_files"), t("tree_dupes"), t("tree_size")
        ])
        self.folder_tree.setSortingEnabled(True)
        self.folder_tree.itemClicked.connect(self.on_folder_click)
        self.top_splitter.addWidget(self.folder_tree)

        file_panel = QWidget()
        file_panel_layout = QVBoxLayout(file_panel)
        file_panel_layout.setContentsMargins(0, 0, 0, 0)
        file_panel_layout.setSpacing(3)

        file_actions = QHBoxLayout()
        file_actions.setSpacing(6)

        self.check_btn = QPushButton(t("btn_select_duplicates"))
        self.check_btn.setStyleSheet(self.STYLE_FLAT)
        self.check_btn.setToolTip(t("tooltip_select_duplicates"))
        self.check_btn.clicked.connect(self.check_all_duplicates)
        file_actions.addWidget(self.check_btn)

        self.uncheck_btn = QPushButton(t("btn_deselect_all"))
        self.uncheck_btn.setStyleSheet(self.STYLE_FLAT)
        self.uncheck_btn.clicked.connect(self.uncheck_all)
        file_actions.addWidget(self.uncheck_btn)

        file_actions.addStretch()

        self.move_checked_btn = QPushButton(t("btn_quarantine_selected"))
        self.move_checked_btn.setStyleSheet(self.STYLE_WARNING)
        self.move_checked_btn.clicked.connect(self.quarantine_checked)
        file_actions.addWidget(self.move_checked_btn)

        self.delete_checked_btn = QPushButton(t("btn_delete_selected"))
        self.delete_checked_btn.setStyleSheet(self.STYLE_DESTRUCTIVE)
        self.delete_checked_btn.clicked.connect(self.delete_checked)
        file_actions.addWidget(self.delete_checked_btn)

        file_panel_layout.addLayout(file_actions)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["", t("tree_filename"), t("tree_size"), t("tree_verdict")])
        self.file_tree.setColumnWidth(0, 40)
        self.file_tree.setSortingEnabled(True)
        self.file_tree.itemClicked.connect(self.on_file_click)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_context_menu)
        file_panel_layout.addWidget(self.file_tree)

        self.top_splitter.addWidget(file_panel)

        # ============================================================
        # BOTTOM — Comparison panel
        # ============================================================
        self.lab_frame = QFrame()
        self.lab_frame.setFrameShape(QFrame.StyledPanel)
        self.lab_layout = QVBoxLayout(self.lab_frame)
        self.lab_layout.setContentsMargins(6, 4, 6, 4)
        self.main_splitter.addWidget(self.lab_frame)

        self._lab_header = QLabel(t("label_comparison"))
        self._lab_header.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 12px;")
        self.lab_layout.addWidget(self._lab_header)

        self.lab_splitter = QSplitter(Qt.Horizontal)
        self.lab_layout.addWidget(self.lab_splitter, 1)
        self.diff_left = QTextEdit(readOnly=True)
        self.diff_right = QTextEdit(readOnly=True)
        self.diff_left.setFont(QFont("Consolas", 9))
        self.diff_right.setFont(QFont("Consolas", 9))
        self.lab_splitter.addWidget(self.diff_left)
        self.lab_splitter.addWidget(self.diff_right)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.waste_donut = WasteDonut()
        self.status_bar.addPermanentWidget(self.waste_donut)

        # ============================================================
        # MENU BAR
        # ============================================================
        menu_bar = self.menuBar()

        # Language menu
        self._lang_menu = menu_bar.addMenu(t("menu_language"))
        for code, name in LANGUAGES.items():
            act = QAction(name, self)
            act.setData(code)
            act.triggered.connect(self._on_language_changed)
            self._lang_menu.addAction(act)

        # Help menu
        self._help_menu = menu_bar.addMenu(t("menu_help"))

        self._how_it_works_act = QAction(t("menu_how_it_works"), self)
        self._how_it_works_act.triggered.connect(self.show_how_it_works)
        self._help_menu.addAction(self._how_it_works_act)

        self._about_act = QAction(t("menu_about"), self)
        self._about_act.triggered.connect(self.show_about)
        self._help_menu.addAction(self._about_act)

    # --- Language switching ---

    def _on_language_changed(self):
        action = self.sender()
        lang = action.data()
        if lang == self._lang:
            return
        self._lang = lang
        self.tr_fn = get_translator(lang)
        # RTL support
        if lang in RTL_LANGUAGES:
            self.setLayoutDirection(Qt.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LeftToRight)
        self._retranslate_ui()

    def _retranslate_ui(self):
        t = self.tr_fn
        self.setWindowTitle(t("window_title"))
        # Row 1
        self._target_label.setText(t("label_target"))
        self.path_input.setPlaceholderText(t("placeholder_select_directory"))
        self._browse_btn.setText(t("btn_browse"))
        # Row 2
        self._sens_label.setText(t("label_sensitivity"))
        idx = self.sens_combo.currentIndex()
        self.sens_combo.blockSignals(True)
        self.sens_combo.clear()
        self.sens_combo.addItems([t("combo_strict"), t("combo_balanced"), t("combo_fuzzy")])
        self.sens_combo.setCurrentIndex(idx)
        self.sens_combo.blockSignals(False)
        self.sens_combo.setToolTip(t("tooltip_sensitivity"))
        self._scan_btn.setText(t("btn_analyze"))
        # Row 4
        self.auto_wizard_btn.setText(t("btn_auto_clean"))
        self.auto_wizard_btn.setToolTip(t("tooltip_auto_clean"))
        self.open_q_btn.setText(t("btn_open_quarantine"))
        self.purge_q_btn.setText(t("btn_empty_quarantine"))
        # Folder tree
        self.folder_tree.setHeaderLabels([
            t("tree_folder"), t("tree_files"), t("tree_dupes"), t("tree_size")
        ])
        # File panel
        self.check_btn.setText(t("btn_select_duplicates"))
        self.check_btn.setToolTip(t("tooltip_select_duplicates"))
        self.uncheck_btn.setText(t("btn_deselect_all"))
        self.move_checked_btn.setText(t("btn_quarantine_selected"))
        self.delete_checked_btn.setText(t("btn_delete_selected"))
        self.file_tree.setHeaderLabels(["", t("tree_filename"), t("tree_size"), t("tree_verdict")])
        # Comparison
        self._lab_header.setText(t("label_comparison"))
        # Menus
        self._lang_menu.setTitle(t("menu_language"))
        self._help_menu.setTitle(t("menu_help"))
        self._how_it_works_act.setText(t("menu_how_it_works"))
        self._about_act.setText(t("menu_about"))
        # Waste donut
        self.waste_donut.setToolTip(t("tooltip_waste_donut"))

    # --- Help dialogs ---

    def show_how_it_works(self):
        t = self.tr_fn
        QMessageBox.information(self, t("menu_how_it_works"), t("help_how_it_works"))

    def show_about(self):
        t = self.tr_fn
        QMessageBox.about(self, t("menu_about"), t("help_about"))

    # --- Core actions ---

    def clear_all_data(self):
        self.match_map.clear()
        self.file_records.clear()
        self.f_stats.clear()
        self.folder_tree.clear()
        self.file_tree.clear()
        self.diff_left.clear()
        self.diff_right.clear()
        self.waste_donut.set_data(0, 0)
        self.status_bar.showMessage(self.tr_fn("status_settings_changed"))

    def select_directory(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr_fn("dialog_file_select"), self.path_input.text()
        )
        if path:
            self.path_input.setText(os.path.abspath(path))

    def _get_sensitivity_key(self):
        """Map current combo index back to the internal English key."""
        return self._sens_keys[self.sens_combo.currentIndex()]

    def start_scan(self):
        target = self.path_input.text()
        if not os.path.isdir(target):
            QMessageBox.warning(
                self, self.tr_fn("dialog_invalid_path"),
                self.tr_fn("msg_invalid_path", path=target)
            )
            return
        self.folder_tree.clear()
        self.file_tree.clear()
        self.diff_left.clear()
        self.diff_right.clear()
        self.progress_bar.setVisible(True)
        self.worker = ScanWorker(target, self._get_sensitivity_key())
        self.worker.progress.connect(self._on_scan_progress)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.start()

    def _on_scan_progress(self, message, count):
        self.status_bar.showMessage(message)

    def _on_scan_finished(self, match_map, stats, file_records):
        self.match_map = match_map
        self.f_stats = stats
        self.file_records = file_records
        self.progress_bar.setVisible(False)

        self.folder_tree.setSortingEnabled(False)
        self.folder_tree.clear()
        for folder, s in stats.items():
            size_mb = s["size"] / 1024 / 1024
            size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{s['size'] / 1024:.1f} KB"
            item = SortableTreeWidgetItem(
                [folder, str(s["count"]), str(s["dupes"]), size_str]
            )
            if "_FORENSIC_QUARANTINE" in folder:
                item.setForeground(0, QColor("#d35400"))
                item.setText(0, self.tr_fn("status_quarantine_label"))
            elif s["dupes"] > 0:
                item.setForeground(2, QColor("#e67e22"))
            self.folder_tree.addTopLevelItem(item)
        self.folder_tree.setSortingEnabled(True)

        total_files = sum(s["count"] for s in stats.values())
        total_size = sum(s["size"] for s in stats.values())
        dupe_groups = sum(1 for paths in match_map.values() if len(paths) > 1)
        dupe_files = sum(len(paths) - 1 for paths in match_map.values() if len(paths) > 1)

        # Compute waste: for each dupe group, all copies except one are waste
        waste_bytes = 0
        for paths in match_map.values():
            if len(paths) > 1:
                sizes = []
                for p in paths:
                    rec = file_records.get(p)
                    sizes.append(rec.size if rec else 0)
                sizes.sort(reverse=True)
                waste_bytes += sum(sizes[1:])  # all but the largest copy

        self.waste_donut.set_data(total_size, waste_bytes)
        waste_str = WasteDonut._fmt(waste_bytes)
        self.status_bar.showMessage(self.tr_fn(
            "status_scan_complete",
            total_files=total_files, dupe_groups=dupe_groups,
            dupe_files=dupe_files, waste_str=waste_str
        ))

    # --- Folder / file tree ---

    def on_folder_click(self, item):
        folder_rel = item.text(0)
        if folder_rel == self.tr_fn("status_quarantine_label"):
            folder_rel = "_FORENSIC_QUARANTINE"
        base = self.path_input.text()
        if folder_rel == os.path.basename(base):
            target_dir = base
        else:
            target_dir = os.path.join(base, folder_rel)
        self.populate_file_tree(target_dir)

    def populate_file_tree(self, target_dir):
        self.file_tree.setSortingEnabled(False)
        self.file_tree.clear()
        if os.path.isdir(target_dir):
            for f in sorted(os.listdir(target_dir)):
                p = os.path.join(target_dir, f)
                if os.path.isfile(p):
                    self._add_file_item(p, f)
        self.file_tree.setSortingEnabled(True)

    def _get_dupes_for(self, path):
        """All files sharing at least one match key with path (excluding itself)."""
        record = self.file_records.get(path)
        if not record or not record.match_keys:
            return []
        dupes = set()
        for key in record.match_keys:
            for p in self.match_map.get(key, []):
                if p != path:
                    dupes.add(p)
        return sorted(dupes)

    def _add_file_item(self, path, filename):
        record = self.file_records.get(path)
        if not record:
            return
        is_q = "_FORENSIC_QUARANTINE" in path
        dupes = [] if is_q else self._get_dupes_for(path)

        t = self.tr_fn
        if is_q:
            status = t("status_quarantined")
        elif dupes:
            status = t("status_match", count=len(dupes) + 1)
        else:
            status = t("status_unique")

        size_kb = record.size / 1024
        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"
        item = SortableTreeWidgetItem(["", filename, size_str, status])
        item.setCheckState(0, Qt.Unchecked)
        item.setData(0, Qt.UserRole, path)

        if is_q:
            item.setForeground(3, QColor("#d35400"))
        elif dupes:
            item.setForeground(3, QColor("#e67e22"))
            for op in dupes:
                rel = os.path.relpath(op, self.path_input.text())
                child = SortableTreeWidgetItem(["", f"-> {rel}", "-", t("status_match_child")])
                child.setCheckState(0, Qt.Unchecked)
                child.setData(0, Qt.UserRole, op)
                item.addChild(child)

        self.file_tree.addTopLevelItem(item)

    # --- Forensic Lab ---

    def on_file_click(self, item, col):
        path = item.data(0, Qt.UserRole)
        if not path or not os.path.exists(path):
            return
        t = self.tr_fn
        self.diff_left.clear()
        self.diff_right.clear()

        record_a = self.file_records.get(path)
        text_a = self._read_preview(path)
        size_a = record_a.size if record_a else 0

        self.diff_left.append(
            f"<b>{t('comp_file_a')}</b> {path}<br>"
            f"<b>{t('comp_size')}</b> {size_a / 1024:.1f} KB<br>"
            f"{'—' * 40}<br>{text_a[:8000]}"
        )

        dupes = self._get_dupes_for(path)
        if dupes:
            other = dupes[0]
            record_b = self.file_records.get(other)
            text_b = self._read_preview(other)
            size_b = record_b.size if record_b else 0

            text_sim = difflib.SequenceMatcher(
                None, text_a[:3000], text_b[:3000]
            ).ratio() * 100

            simhash_info = ""
            if (record_a and record_b
                    and record_a.simhash is not None
                    and record_b.simhash is not None):
                sh_sim = simhash_similarity(record_a.simhash, record_b.simhash) * 100
                hamming = bin(record_a.simhash ^ record_b.simhash).count('1')
                simhash_info = (
                    f"<br><b>{t('comp_simhash_sim')}</b> {sh_sim:.1f}% "
                    f"({t('comp_hamming')} {hamming}/{SIMHASH_BITS})"
                )

            size_info = ""
            if size_a != size_b:
                diff_kb = abs(size_a - size_b) / 1024
                size_info = f"<br><b>{t('comp_size_diff')}</b> {diff_kb:.1f} KB"

            color = "#27ae60" if text_sim > 95 else "#e67e22" if text_sim > 70 else "#c0392b"
            self.diff_right.append(
                f"<b>{t('comp_file_b')}</b> {other}<br>"
                f"<b>{t('comp_size')}</b> {size_b / 1024:.1f} KB{size_info}<br>"
                f"<b style='color:{color};'>{t('comp_text_sim')} {text_sim:.1f}%</b>"
                f"{simhash_info}<br>"
                f"{'—' * 40}<br>{text_b[:8000]}"
            )

    def _read_preview(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(15000)
        except OSError:
            return self.tr_fn("comp_binary")

    # --- Bulk actions ---

    def check_all_duplicates(self):
        t = self.tr_fn
        root = self.file_tree.invisibleRootItem()
        checked = 0
        for i in range(root.childCount()):
            item = root.child(i)
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, Qt.Checked)
                checked += 1
        if checked:
            self.status_bar.showMessage(t("status_checked", count=checked))
        else:
            self.status_bar.showMessage(t("status_no_dupes_to_check"))

    def uncheck_all(self):
        def recurse(item):
            item.setCheckState(0, Qt.Unchecked)
            for i in range(item.childCount()):
                recurse(item.child(i))
        root = self.file_tree.invisibleRootItem()
        for i in range(root.childCount()):
            recurse(root.child(i))

    def get_checked_paths(self):
        paths = set()
        def recurse(item):
            if item.checkState(0) == Qt.Checked:
                p = item.data(0, Qt.UserRole)
                if p and os.path.exists(p):
                    paths.add(p)
            for i in range(item.childCount()):
                recurse(item.child(i))
        recurse(self.file_tree.invisibleRootItem())
        return sorted(paths)

    def open_quarantine_folder(self):
        q_dir = os.path.join(self.path_input.text(), "_FORENSIC_QUARANTINE")
        open_in_file_manager(q_dir)

    def quarantine_checked(self):
        t = self.tr_fn
        paths = self.get_checked_paths()
        if not paths:
            self.status_bar.showMessage(t("status_nothing_checked"))
            return
        q_dir = os.path.join(self.path_input.text(), "_FORENSIC_QUARANTINE")
        answer = QMessageBox.question(
            self, t("dialog_quarantine"),
            t("msg_quarantine_confirm", count=len(paths))
        )
        if answer != QMessageBox.Yes:
            return
        os.makedirs(q_dir, exist_ok=True)
        moved = 0
        for p in paths:
            try:
                tag = zlib.adler32(p.encode()) & 0xFFFFFFFF
                target = os.path.join(q_dir, f"{tag}_{os.path.basename(p)}")
                shutil.move(p, target)
                moved += 1
            except OSError as e:
                log.warning("Failed to quarantine %s: %s", p, e)
        self.status_bar.showMessage(t("status_quarantined_files", moved=moved, total=len(paths)))
        self.start_scan()

    def delete_checked(self):
        t = self.tr_fn
        paths = self.get_checked_paths()
        if not paths:
            self.status_bar.showMessage(t("status_nothing_checked"))
            return
        answer = QMessageBox.warning(
            self, t("dialog_delete"),
            t("msg_delete_confirm", count=len(paths)),
            QMessageBox.Yes | QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return
        deleted = 0
        for p in paths:
            try:
                os.remove(p)
                deleted += 1
            except OSError as e:
                log.warning("Failed to delete %s: %s", p, e)
        self.status_bar.showMessage(t("status_deleted_files", deleted=deleted, total=len(paths)))
        self.start_scan()

    def smart_auto_clean(self):
        t = self.tr_fn
        dupe_sets = [list(paths) for paths in self.match_map.values() if len(paths) > 1]
        if not dupe_sets:
            self.status_bar.showMessage(t("status_no_dupes_found"))
            return

        already_kept = set()
        to_move = set()
        for paths in dupe_sets:
            working = sorted(paths, key=keeper_score)
            keeper = working[0]
            already_kept.add(keeper)
            for p in working[1:]:
                if p not in already_kept:
                    to_move.add(p)

        to_move -= already_kept

        if not to_move:
            self.status_bar.showMessage(t("status_no_redundant"))
            return

        answer = QMessageBox.question(
            self, t("dialog_auto_wizard"),
            t("msg_wizard_confirm", count=len(to_move))
        )
        if answer != QMessageBox.Yes:
            return

        q_dir = os.path.join(self.path_input.text(), "_FORENSIC_QUARANTINE")
        os.makedirs(q_dir, exist_ok=True)
        moved = 0
        for p in to_move:
            try:
                tag = zlib.adler32(p.encode()) & 0xFFFFFFFF
                dest = os.path.join(q_dir, f"auto_{tag}_{os.path.basename(p)}")
                shutil.move(p, dest)
                moved += 1
            except OSError as e:
                log.warning("Wizard failed to move %s: %s", p, e)
        self.status_bar.showMessage(t("status_wizard_moved", moved=moved, total=len(to_move)))
        self.start_scan()

    def purge_quarantine(self):
        t = self.tr_fn
        q_dir = os.path.join(self.path_input.text(), "_FORENSIC_QUARANTINE")
        if not os.path.isdir(q_dir):
            self.status_bar.showMessage(t("status_no_quarantine"))
            return
        files = [f for f in os.listdir(q_dir) if os.path.isfile(os.path.join(q_dir, f))]
        if not files:
            self.status_bar.showMessage(t("status_quarantine_empty"))
            return
        answer = QMessageBox.warning(
            self, t("dialog_purge"),
            t("msg_purge_confirm", count=len(files)),
            QMessageBox.Yes | QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return
        deleted = 0
        for f in files:
            try:
                os.remove(os.path.join(q_dir, f))
                deleted += 1
            except OSError as e:
                log.warning("Purge failed for %s: %s", f, e)
        self.status_bar.showMessage(t("status_purged", deleted=deleted, total=len(files)))
        self.start_scan()

    # --- Context menu ---

    def show_context_menu(self, pos):
        item = self.file_tree.itemAt(pos)
        if not item:
            return
        path = item.data(0, Qt.UserRole)
        if not path:
            return
        menu = QMenu()
        open_act = menu.addAction(self.tr_fn("context_open_folder"))
        open_act.triggered.connect(
            lambda: open_in_file_manager(os.path.dirname(path))
        )
        menu.exec_(self.file_tree.viewport().mapToGlobal(pos))


def main():
    app = QApplication(sys.argv)
    ex = ForensicVisualInspector()
    ex.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
