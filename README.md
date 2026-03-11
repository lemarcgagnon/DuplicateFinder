# Duplicate Finder

A desktop application that finds and manages duplicate files using forensic-grade detection algorithms. Built with Python and PyQt5.

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Features

- **Three detection modes:**
  - **Strict** — SHA-256 full-content hash. Zero false positives. Uses a progressive pipeline (size → head → tail → full hash) to skip unnecessary I/O.
  - **Balanced** — Same progressive pipeline but stops at head+tail match. Near-zero false positives, much faster on large files.
  - **Fuzzy** — SimHash with LSH banding. Catches similar-but-not-identical files (~85%+ content overlap). Works on both text and binary files.

- **Side-by-side comparison lab** — Click any file to see a visual diff with its duplicate, including text similarity percentage and SimHash distance.

- **Smart auto-clean** — One-click wizard that identifies redundant copies using path heuristics (detects "copy", "backup", temp folders, etc.) and moves them to quarantine.

- **Safe quarantine workflow** — Files are moved to a `_FORENSIC_QUARANTINE` folder before permanent deletion. Review, restore, or purge at any time.

## Install

### Prerequisites

- Python 3.8 or later
- pip

### Steps

```bash
# Clone the repository
git clone https://github.com/lemarcgagnon/DuplicateFinder.git
cd DuplicateFinder

# Install dependencies
pip install -r requirements.txt

# Run
python3 app.py
```

> **Note:** On some Linux distributions, you may need system packages for Qt:
> ```bash
> # Ubuntu / Debian
> sudo apt install python3-pyqt5
>
> # Fedora
> sudo dnf install python3-qt5
> ```

### Windows / macOS

```bash
pip install PyQt5
python app.py
```

No additional system packages needed.

## Usage

1. **Set target directory** — Type a path or click **Browse...**
2. **Choose sensitivity** — Strict (exact), Balanced (fast), or Fuzzy (similar content)
3. **Click Analyze** — The scan runs in the background with a progress indicator
4. **Review results** — Click a folder on the left to see its files on the right. Duplicates are listed with their copies as child items.
5. **Compare** — Click any file to see a side-by-side comparison in the bottom panel
6. **Clean up** — Use **Select duplicates** → **Quarantine selected**, or let **Auto-clean duplicates** handle it automatically

## How detection works

```
Strict / Balanced:
  file size → first 4KB → last 4KB → full SHA-256 (Strict only)
  Each stage eliminates non-candidates before reading more data.

Fuzzy:
  tokenize text (or byte n-grams for binary)
  → 64-bit SimHash from shingle hashes
  → 8 LSH bands of 8 bits each
  Files sharing any band are candidate duplicates (~85%+ similarity threshold).
```

## Project structure

```
DuplicateFinder/
├── app.py              # Algorithms, UI, and logic (single-file app)
├── requirements.txt    # Python dependencies (PyQt5)
├── app.log             # Runtime warnings (created on first run)
└── README.md
```

## Safety & Disclaimer

**Back up your data before using this tool.** Always keep a copy of important files before running any cleanup operation.

Several safeguards are built in to prevent accidental data loss:

- Every destructive action requires an explicit confirmation dialog.
- Files are quarantined (moved to `_FORENSIC_QUARANTINE/`) before permanent deletion — you can review and restore them at any time.
- The auto-clean wizard never deletes files directly; it only moves copies to quarantine.
- No file is ever touched without user-initiated action.

That said, **no software is infallible**. Depending on your operating system and configuration, deleted files may still be recoverable from your trash or recycle bin. However, this is not guaranteed.

> **This software is provided "as is", without warranty of any kind, express or implied. The authors are not responsible for any data loss resulting from the use of this tool. You use it entirely at your own risk.**

## Security audit

This codebase has been scanned before publication using industry-standard security tools:

- **[Bandit](https://bandit.readthedocs.io/)** (static analysis for Python) — **0 issues.** Six informational findings related to `subprocess` usage were reviewed and confirmed safe: all calls use list arguments (no shell interpolation) and operate on user-selected paths within the app.
- **[pip-audit](https://pypi.org/project/pip-audit/)** (dependency vulnerability scanner) — **0 known vulnerabilities** in project dependencies (PyQt5).

You can re-run these audits yourself at any time:

```bash
pip install bandit pip-audit
bandit -r app.py
pip-audit -r requirements.txt
```

## Credits

Created by **Marc Gagnon** ([marcgagnon.ca](https://marcgagnon.ca)) with **Gemini** and **Claude**.

## License

MIT
