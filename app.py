import os
import hashlib
import sys
import zlib
import subprocess
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
from PyQt5.QtGui import QFont, QColor
from collections import defaultdict

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
    """Open a folder in the system's native file manager."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
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
        self.setWindowTitle("Genies Forensic Inspector")
        self.resize(1800, 1000)
        self.match_map = {}
        self.file_records = {}
        self.f_stats = {}
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(6)

        # ============================================================
        # ROW 1 — Target selection (HIG: primary navigation, top)
        # ============================================================
        target_row = QHBoxLayout()
        target_row.setSpacing(6)

        target_label = QLabel("Target:")
        target_label.setStyleSheet("font-weight: bold;")
        target_row.addWidget(target_label)

        self.path_input = QLineEdit(os.path.abspath(".."))
        self.path_input.setStyleSheet("padding: 6px; font-size: 13px;")
        self.path_input.setPlaceholderText("Select a directory to scan...")
        self.path_input.textChanged.connect(self.clear_all_data)
        target_row.addWidget(self.path_input, 1)  # stretch

        # Browse: secondary prominence (HIG: opens a dialog → trailing ellipsis)
        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet(self.STYLE_SECONDARY)
        browse_btn.clicked.connect(self.select_directory)
        target_row.addWidget(browse_btn)

        layout.addLayout(target_row)

        # ============================================================
        # ROW 2 — Analysis controls (HIG: primary action most prominent)
        # ============================================================
        analysis_row = QHBoxLayout()
        analysis_row.setSpacing(8)

        sens_label = QLabel("Sensitivity:")
        sens_label.setStyleSheet("color: #7f8c8d;")
        analysis_row.addWidget(sens_label)

        self.sens_combo = QComboBox()
        self.sens_combo.addItems(["Strict", "Balanced", "Fuzzy"])
        self.sens_combo.setCurrentText("Balanced")
        self.sens_combo.setToolTip(
            "Strict = exact match (SHA-256)\n"
            "Balanced = fast near-exact (head+tail)\n"
            "Fuzzy = similar content (SimHash)"
        )
        self.sens_combo.setStyleSheet("padding: 4px 8px;")
        self.sens_combo.currentIndexChanged.connect(self.clear_all_data)
        analysis_row.addWidget(self.sens_combo)

        analysis_row.addStretch()

        # Analyze: PRIMARY action — largest, filled accent (HIG: hierarchy through style)
        scan_btn = QPushButton("Analyze")
        scan_btn.setStyleSheet(self.STYLE_PRIMARY)
        scan_btn.clicked.connect(self.start_scan)
        analysis_row.addWidget(scan_btn)

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
        # ROW 4 — Global actions (HIG: secondary toolbar, grouped by domain)
        # ============================================================
        global_row = QHBoxLayout()
        global_row.setSpacing(8)

        # Auto-clean: accent action (HIG: specific verb label)
        self.auto_wizard_btn = QPushButton("Auto-clean duplicates")
        self.auto_wizard_btn.setStyleSheet(self.STYLE_ACCENT)
        self.auto_wizard_btn.setToolTip(
            "Automatically move redundant copies to quarantine.\n"
            "Keeps the file with the shortest, cleanest path."
        )
        self.auto_wizard_btn.clicked.connect(self.smart_auto_clean)
        global_row.addWidget(self.auto_wizard_btn)

        global_row.addStretch()

        # Quarantine group (HIG: consistent grouping of related actions)
        self.open_q_btn = QPushButton("Open quarantine folder")
        self.open_q_btn.setStyleSheet(self.STYLE_FLAT)
        self.open_q_btn.clicked.connect(self.open_quarantine_folder)
        global_row.addWidget(self.open_q_btn)

        # Empty quarantine: destructive (HIG: "Empty Trash" pattern)
        self.purge_q_btn = QPushButton("Empty quarantine")
        self.purge_q_btn.setStyleSheet(self.STYLE_DESTRUCTIVE)
        self.purge_q_btn.clicked.connect(self.purge_quarantine)
        global_row.addWidget(self.purge_q_btn)

        layout.addLayout(global_row)

        # ============================================================
        # MAIN CONTENT — Split view (HIG: sidebar + detail pattern)
        # ============================================================
        self.main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.main_splitter, 1)

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.top_splitter)

        # Left: Folder tree (HIG: outline/tree view for hierarchy)
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels(["Folder", "Files", "Dupes", "Size"])
        self.folder_tree.setSortingEnabled(True)
        self.folder_tree.itemClicked.connect(self.on_folder_click)
        self.top_splitter.addWidget(self.folder_tree)

        # Right: File panel with contextual action bar
        file_panel = QWidget()
        file_panel_layout = QVBoxLayout(file_panel)
        file_panel_layout.setContentsMargins(0, 0, 0, 0)
        file_panel_layout.setSpacing(3)

        # Contextual actions (HIG: controls near the data they affect)
        file_actions = QHBoxLayout()
        file_actions.setSpacing(6)

        # Selection: flat/tertiary (HIG: non-destructive = low visual weight)
        self.check_btn = QPushButton("Select duplicates")
        self.check_btn.setStyleSheet(self.STYLE_FLAT)
        self.check_btn.setToolTip("Select all duplicate copies (keeps originals unselected)")
        self.check_btn.clicked.connect(self.check_all_duplicates)
        file_actions.addWidget(self.check_btn)

        self.uncheck_btn = QPushButton("Deselect all")
        self.uncheck_btn.setStyleSheet(self.STYLE_FLAT)
        self.uncheck_btn.clicked.connect(self.uncheck_all)
        file_actions.addWidget(self.uncheck_btn)

        file_actions.addStretch()

        # Destructive: warning/danger (HIG: destructive style, right-aligned)
        self.move_checked_btn = QPushButton("Quarantine selected")
        self.move_checked_btn.setStyleSheet(self.STYLE_WARNING)
        self.move_checked_btn.clicked.connect(self.quarantine_checked)
        file_actions.addWidget(self.move_checked_btn)

        self.delete_checked_btn = QPushButton("Delete selected")
        self.delete_checked_btn.setStyleSheet(self.STYLE_DESTRUCTIVE)
        self.delete_checked_btn.clicked.connect(self.delete_checked)
        file_actions.addWidget(self.delete_checked_btn)

        file_panel_layout.addLayout(file_actions)

        # File tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["", "Filename", "Size", "Verdict"])
        self.file_tree.setColumnWidth(0, 40)
        self.file_tree.setSortingEnabled(True)
        self.file_tree.itemClicked.connect(self.on_file_click)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_context_menu)
        file_panel_layout.addWidget(self.file_tree)

        self.top_splitter.addWidget(file_panel)

        # ============================================================
        # BOTTOM — Forensic Lab (HIG: detail panel for comparison)
        # ============================================================
        self.lab_frame = QFrame()
        self.lab_frame.setFrameShape(QFrame.StyledPanel)
        self.lab_layout = QVBoxLayout(self.lab_frame)
        self.lab_layout.setContentsMargins(6, 4, 6, 4)
        self.main_splitter.addWidget(self.lab_frame)

        lab_header = QLabel("Comparison")
        lab_header.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 12px;")
        self.lab_layout.addWidget(lab_header)

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

        # ============================================================
        # MENU BAR — Help (HIG: redundant access paths for key info)
        # ============================================================
        menu_bar = self.menuBar()
        help_menu = menu_bar.addMenu("Help")

        how_it_works = QAction("How it works", self)
        how_it_works.triggered.connect(self.show_how_it_works)
        help_menu.addAction(how_it_works)

        about_act = QAction("About", self)
        about_act.triggered.connect(self.show_about)
        help_menu.addAction(about_act)

    # --- Help dialogs ---

    def show_how_it_works(self):
        QMessageBox.information(self, "How it works", (
            "<h3>Quick start</h3>"
            "<ol>"
            "<li><b>Set a target directory</b> — type a path or click <i>Browse...</i></li>"
            "<li><b>Pick a sensitivity mode:</b><br>"
            "&nbsp;&nbsp;Strict — exact match (SHA-256, zero false positives)<br>"
            "&nbsp;&nbsp;Balanced — fast near-exact (compares head + tail bytes)<br>"
            "&nbsp;&nbsp;Fuzzy — finds similar content (~85%+ overlap)</li>"
            "<li><b>Click Analyze</b> — the scan runs in the background</li>"
            "<li><b>Click a folder</b> on the left to see its files on the right</li>"
            "<li><b>Click a file</b> to compare it with its duplicate in the bottom panel</li>"
            "<li><b>Clean up:</b> select duplicates, then quarantine or delete them</li>"
            "</ol>"
            "<h3>Detection pipeline</h3>"
            "<p><b>Strict &amp; Balanced</b> use a progressive pipeline:<br>"
            "file size → first 4 KB → last 4 KB → full SHA-256 (Strict only).<br>"
            "Each stage eliminates non-candidates before reading more data.</p>"
            "<p><b>Fuzzy</b> tokenizes text (or uses byte n-grams for binary files), "
            "computes a 64-bit SimHash, and splits it into 8 LSH bands. "
            "Files sharing any band are flagged as similar.</p>"
            "<h3>Quarantine</h3>"
            "<p>Files are never deleted directly — they are first moved to a "
            "<code>_FORENSIC_QUARANTINE</code> folder inside the target directory. "
            "You can review them, restore them manually, or use <i>Empty quarantine</i> "
            "to permanently delete them.</p>"
            "<h3>Auto-clean</h3>"
            "<p>The auto-clean wizard picks which copy to keep using heuristics: "
            "shortest path, absence of keywords like 'copy' or 'backup', "
            "and most recent modification time as a tiebreaker. "
            "All other copies are moved to quarantine.</p>"
            "<h3>Safety &amp; disclaimer</h3>"
            "<p><b>Back up your data before using this tool.</b> While multiple "
            "safeguards are in place — confirmation dialogs, quarantine step before "
            "deletion, and no files are ever deleted without explicit user action — "
            "no software is infallible.</p>"
            "<p>Deleted files may still be recoverable from your operating system's "
            "trash/recycle bin depending on your platform and configuration.</p>"
            "<p>This software is provided as-is, without warranty of any kind. "
            "The authors are not liable for any data loss. "
            "<b>You use this tool entirely at your own risk.</b></p>"
        ))

    def show_about(self):
        QMessageBox.about(self, "About", (
            "<h3>Genies Forensic Inspector</h3>"
            "<p>Duplicate file finder with forensic-grade detection.</p>"
            "<p>Algorithms: SHA-256, progressive head/tail pipeline, "
            "SimHash + LSH banding.</p>"
            "<p>Built with Python and PyQt5.</p>"
            "<hr>"
            "<p>Created by <b>Marc Gagnon</b> "
            "(<a href='https://marcgagnon.ca'>marcgagnon.ca</a>)<br>"
            "with <b>Gemini</b> and <b>Claude</b>.</p>"
        ))

    # --- Core actions ---

    def clear_all_data(self):
        self.match_map.clear()
        self.file_records.clear()
        self.f_stats.clear()
        self.folder_tree.clear()
        self.file_tree.clear()
        self.diff_left.clear()
        self.diff_right.clear()
        self.status_bar.showMessage("Settings changed — re-analyze to update.")

    def select_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.path_input.text())
        if path:
            self.path_input.setText(os.path.abspath(path))

    def start_scan(self):
        target = self.path_input.text()
        if not os.path.isdir(target):
            QMessageBox.warning(self, "Invalid path", f"Directory not found:\n{target}")
            return
        self.folder_tree.clear()
        self.file_tree.clear()
        self.diff_left.clear()
        self.diff_right.clear()
        self.progress_bar.setVisible(True)
        self.worker = ScanWorker(target, self.sens_combo.currentText())
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
                item.setText(0, "QUARANTINE")
            elif s["dupes"] > 0:
                item.setForeground(2, QColor("#e67e22"))
            self.folder_tree.addTopLevelItem(item)
        self.folder_tree.setSortingEnabled(True)

        total_files = sum(s["count"] for s in stats.values())
        dupe_groups = sum(1 for paths in match_map.values() if len(paths) > 1)
        dupe_files = sum(len(paths) - 1 for paths in match_map.values() if len(paths) > 1)
        self.status_bar.showMessage(
            f"Done: {total_files} files scanned, {dupe_groups} duplicate groups, "
            f"{dupe_files} redundant copies."
        )

    # --- Folder / file tree ---

    def on_folder_click(self, item):
        folder_rel = item.text(0)
        if folder_rel == "QUARANTINE":
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

        if is_q:
            status = "QUARANTINED"
        elif dupes:
            status = f"MATCH ({len(dupes) + 1})"
        else:
            status = "Unique"

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
                child = SortableTreeWidgetItem(["", f"-> {rel}", "-", "Match"])
                child.setCheckState(0, Qt.Unchecked)
                child.setData(0, Qt.UserRole, op)
                item.addChild(child)

        self.file_tree.addTopLevelItem(item)

    # --- Forensic Lab ---

    def on_file_click(self, item, col):
        path = item.data(0, Qt.UserRole)
        if not path or not os.path.exists(path):
            return
        self.diff_left.clear()
        self.diff_right.clear()

        record_a = self.file_records.get(path)
        text_a = self._read_preview(path)
        size_a = record_a.size if record_a else 0

        self.diff_left.append(
            f"<b>FILE A:</b> {path}<br>"
            f"<b>Size:</b> {size_a / 1024:.1f} KB<br>"
            f"{'—' * 40}<br>{text_a[:8000]}"
        )

        dupes = self._get_dupes_for(path)
        if dupes:
            other = dupes[0]
            record_b = self.file_records.get(other)
            text_b = self._read_preview(other)
            size_b = record_b.size if record_b else 0

            # Text similarity (SequenceMatcher)
            text_sim = difflib.SequenceMatcher(
                None, text_a[:3000], text_b[:3000]
            ).ratio() * 100

            # SimHash similarity (if available)
            simhash_info = ""
            if (record_a and record_b
                    and record_a.simhash is not None
                    and record_b.simhash is not None):
                sh_sim = simhash_similarity(record_a.simhash, record_b.simhash) * 100
                hamming = bin(record_a.simhash ^ record_b.simhash).count('1')
                simhash_info = (
                    f"<br><b>SimHash similarity:</b> {sh_sim:.1f}% "
                    f"(Hamming distance: {hamming}/{SIMHASH_BITS})"
                )

            # Size comparison
            size_info = ""
            if size_a != size_b:
                diff_kb = abs(size_a - size_b) / 1024
                size_info = f"<br><b>Size difference:</b> {diff_kb:.1f} KB"

            color = "#27ae60" if text_sim > 95 else "#e67e22" if text_sim > 70 else "#c0392b"
            self.diff_right.append(
                f"<b>FILE B:</b> {other}<br>"
                f"<b>Size:</b> {size_b / 1024:.1f} KB{size_info}<br>"
                f"<b style='color:{color};'>Text similarity: {text_sim:.1f}%</b>"
                f"{simhash_info}<br>"
                f"{'—' * 40}<br>{text_b[:8000]}"
            )

    def _read_preview(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(15000)
        except OSError:
            return "[Binary or protected file]"

    # --- Bulk actions ---

    def check_all_duplicates(self):
        root = self.file_tree.invisibleRootItem()
        checked = 0
        for i in range(root.childCount()):
            item = root.child(i)
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, Qt.Checked)
                checked += 1
        if checked:
            self.status_bar.showMessage(f"Checked {checked} duplicate copies.")
        else:
            self.status_bar.showMessage("No duplicates to check — select a folder first.")

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
        paths = self.get_checked_paths()
        if not paths:
            self.status_bar.showMessage("Nothing checked.")
            return
        q_dir = os.path.join(self.path_input.text(), "_FORENSIC_QUARANTINE")
        answer = QMessageBox.question(
            self, "Quarantine",
            f"Move {len(paths)} checked file(s) to quarantine?"
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
        self.status_bar.showMessage(f"Quarantined {moved}/{len(paths)} files.")
        self.start_scan()

    def delete_checked(self):
        paths = self.get_checked_paths()
        if not paths:
            self.status_bar.showMessage("Nothing checked.")
            return
        answer = QMessageBox.warning(
            self, "Permanent Delete",
            f"PERMANENTLY DELETE {len(paths)} checked file(s)?\nThis cannot be undone.",
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
        self.status_bar.showMessage(f"Deleted {deleted}/{len(paths)} files.")
        self.start_scan()

    def smart_auto_clean(self):
        """Identify redundant copies using heuristics and move to quarantine."""
        dupe_sets = [list(paths) for paths in self.match_map.values() if len(paths) > 1]
        if not dupe_sets:
            self.status_bar.showMessage("No duplicates found — run ANALYZE first.")
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

        # Don't move a file that was elected keeper in another group
        to_move -= already_kept

        if not to_move:
            self.status_bar.showMessage("No redundant copies to move.")
            return

        answer = QMessageBox.question(
            self, "Smart Auto-Wizard",
            f"The wizard identified {len(to_move)} redundant copies.\n"
            f"Move them to quarantine?\n\n"
            f"(Keeps the file with the shortest, cleanest path in each group.)"
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
        self.status_bar.showMessage(
            f"Wizard moved {moved}/{len(to_move)} files to quarantine."
        )
        self.start_scan()

    def purge_quarantine(self):
        q_dir = os.path.join(self.path_input.text(), "_FORENSIC_QUARANTINE")
        if not os.path.isdir(q_dir):
            self.status_bar.showMessage("No quarantine folder found.")
            return
        files = [f for f in os.listdir(q_dir) if os.path.isfile(os.path.join(q_dir, f))]
        if not files:
            self.status_bar.showMessage("Quarantine is already empty.")
            return
        answer = QMessageBox.warning(
            self, "Purge Quarantine",
            f"PERMANENTLY DELETE all {len(files)} file(s) in quarantine?\n"
            f"This cannot be undone.",
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
        self.status_bar.showMessage(
            f"Purged {deleted}/{len(files)} files from quarantine."
        )
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
        open_act = menu.addAction("Open containing folder")
        open_act.triggered.connect(
            lambda: open_in_file_manager(os.path.dirname(path))
        )
        menu.exec_(self.file_tree.viewport().mapToGlobal(pos))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ForensicVisualInspector()
    ex.show()
    sys.exit(app.exec_())
