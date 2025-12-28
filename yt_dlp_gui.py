import sys
import subprocess
import json
import os
import urllib.request
import shutil
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QLabel, QFileDialog, QCheckBox, QComboBox, QDialog, QMessageBox
)
from PySide6.QtCore import QSize, QThread, Signal, QObject, QUrl
from PySide6.QtGui import QPalette, QDesktopServices

CONFIG_FILE = "app_config.json"
OPEN_FOLDER_DIALOG_TITLE = "Open folder"
OPEN_LAST_SAVE_LOCATION_TEXT = "Open last save location"

class DownloadWorker(QObject):
    output = Signal(str)
    finished = Signal()

    def __init__(self, url, video_dir, audio_dir, audio_only, cookies_browser=None, cookies_file=None):
        super().__init__()
        self.url = url
        self.video_dir = video_dir
        self.audio_dir = audio_dir
        self.audio_only = audio_only
        self.cookies_browser = cookies_browser
        self.cookies_file = cookies_file

    def run(self):
        if self.audio_only:
            download_dir = self.audio_dir
            cmd = [
                "yt-dlp", "-x", "--audio-format", "mp3",
                "-P", download_dir
            ]
            self.output.emit(f"Starting audio download: {self.url}\nDownload directory: {download_dir}")
        else:
            download_dir = self.video_dir
            cmd = [
                "yt-dlp", "-P", download_dir
            ]
            self.output.emit(f"Starting video download: {self.url}\nDownload directory: {download_dir}")
        if self.cookies_file:
            cmd.extend(["--cookies", self.cookies_file])
            self.output.emit(f"Using cookies file: {self.cookies_file}")
        elif self.cookies_browser:
            cmd.extend(["--cookies-from-browser", self.cookies_browser])
            self.output.emit(f"Using cookies from browser: {self.cookies_browser}")
        cmd.append(self.url)
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                self.output.emit(line.strip())
            process.wait()
            self.output.emit("Download finished.")
        except Exception as e:
            self.output.emit(f"Error: {e}")
        self.finished.emit()

class ReadmeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("README")
        self.resize(900, 600)
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(close_btn)
        layout.addLayout(buttons_layout)
        self._load_readme()

    def _load_readme(self):
        possible_paths = [
            os.path.join(os.getcwd(), "README.md"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        ]
        content = None
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        content = f.read()
                    break
                except Exception:
                    continue
        if content is None:
            content = "README.md not found."
        try:
            # Preferred: render markdown
            self.text.setMarkdown(content)
        except Exception:
            # Fallback to plain text
            self.text.setPlainText(content)

class YtDlpGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp GUI")
        self.setMinimumWidth(500)
        self.video_dir = os.path.expanduser("~")  # Default to home directory
        self.audio_dir = os.path.expanduser("~")
        self.last_save_dir = ""
        self.cookies_file_path = ""
        self.load_config()

        # Layouts
        main_layout = QVBoxLayout()
        url_layout = QHBoxLayout()
        video_dir_layout = QHBoxLayout()
        audio_dir_layout = QHBoxLayout()
        override_layout = QHBoxLayout()
        cookies_layout = QHBoxLayout()
        cookies_file_layout = QHBoxLayout()
        updates_layout = QHBoxLayout()

        # URL input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter video URL here...")

        # Paste button
        self.paste_btn = QPushButton("Paste from Clipboard")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)

        # Download button
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.start_download)

        # Audio only checkbox
        self.audio_only_checkbox = QCheckBox("Audio only (extract as .mp3)")

        # Override save location checkbox (with tooltip)
        self.override_save_location_checkbox = QCheckBox("Choose save location for each download (i)")
        override_layout.addWidget(self.override_save_location_checkbox)
        self.override_save_location_checkbox.setToolTip("Overrides default locations shown below and asks for save location every time")

        # Cookies from browser
        self.use_cookies_checkbox = QCheckBox("Use cookies from browser (i)")
        self.cookies_browser_combo = QComboBox()
        self.cookies_browser_combo.addItems(["brave", "chrome", "edge", "firefox", "vivaldi"])  # common browsers
        self.cookies_profile_input = QLineEdit()
        self.cookies_profile_input.setPlaceholderText("Profile (e.g., Default, Profile 1)")
        self.cookies_browser_combo.setEnabled(False)
        self.cookies_profile_input.setEnabled(False)
        self.use_cookies_checkbox.toggled.connect(self.cookies_browser_combo.setEnabled)
        self.use_cookies_checkbox.toggled.connect(self.cookies_profile_input.setEnabled)
        self.use_cookies_checkbox.setToolTip("Some sites require login. Extract cookies from a logged-in browser profile. If the browser's cookie database is locked, fully close the browser first. Then choose the browser and optional profile.")
        self.cookies_browser_combo.setToolTip("Browser to extract cookies from (must be logged in to the site).")
        self.cookies_profile_input.setToolTip("Optional profile name (e.g., Default, Profile 1). Leave empty for the default profile.")
        cookies_layout.addWidget(self.use_cookies_checkbox)
        browser_label = QLabel("Browser: (i)")
        browser_label.setToolTip("Browser to extract cookies from (must be logged in to the site).")
        cookies_layout.addWidget(browser_label)
        cookies_layout.addWidget(self.cookies_browser_combo)
        profile_label = QLabel("Profile: (i)")
        profile_label.setToolTip("Optional profile name (e.g., Default, Profile 1). Leave empty for the default profile.")
        cookies_layout.addWidget(profile_label)
        cookies_layout.addWidget(self.cookies_profile_input)

        # Cookies file
        self.use_cookies_file_checkbox = QCheckBox("Use cookies file (i)")
        self.use_cookies_file_checkbox.toggled.connect(lambda checked: self._set_cookies_file_enabled(checked))
        self.cookies_file_label = QLabel("(no file selected)")
        self.cookies_file_btn = QPushButton("Choose cookies.txt")
        self.cookies_file_btn.clicked.connect(self.choose_cookies_file)
        self.cookies_file_label.setEnabled(False)
        self.cookies_file_btn.setEnabled(False)
        self.use_cookies_file_checkbox.setToolTip("Use a Netscape-format cookies.txt exported from your browser (helpful when the browser cookie DB is locked). How: Install a cookies exporter extension; while logged in, open the site's page and export cookies as 'cookies.txt'.")
        self.cookies_file_btn.setToolTip("Pick a Netscape cookies.txt file exported from your browser.")
        cookies_file_layout.addWidget(self.use_cookies_file_checkbox)
        cookies_file_layout.addWidget(self.cookies_file_label)
        cookies_file_layout.addWidget(self.cookies_file_btn)

        # Status/output display
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setPlaceholderText("Status and output will appear here...")

        # Open last save location button (centered at bottom; enabled only after first save)
        self.open_last_save_btn = QPushButton(OPEN_LAST_SAVE_LOCATION_TEXT)
        self.open_last_save_btn.clicked.connect(lambda: self._open_directory_in_file_manager(self.last_save_dir))
        self.open_last_save_btn.setToolTip("Open the folder used for the most recent download (default or custom).")

        # Video download directory label and button
        self.video_dir_label = QLabel(self.video_dir)
        self.video_dir_btn = QPushButton("Choose Video Directory")
        self.video_dir_btn.clicked.connect(self.choose_video_dir)
        self.open_video_dir_btn = QPushButton("Open")
        self.open_video_dir_btn.clicked.connect(lambda: self._open_directory_in_file_manager(self.video_dir))
        self.open_video_dir_btn.setToolTip("Open the video download folder in your file manager (e.g., File Explorer).")
        video_dir_layout.addWidget(QLabel("Video to:"))
        video_dir_layout.addWidget(self.video_dir_label)
        video_dir_layout.addWidget(self.video_dir_btn)
        video_dir_layout.addWidget(self.open_video_dir_btn)

        # Audio download directory label and button
        self.audio_dir_label = QLabel(self.audio_dir)
        self.audio_dir_btn = QPushButton("Choose Audio Directory")
        self.audio_dir_btn.clicked.connect(self.choose_audio_dir)
        self.open_audio_dir_btn = QPushButton("Open")
        self.open_audio_dir_btn.clicked.connect(lambda: self._open_directory_in_file_manager(self.audio_dir))
        self.open_audio_dir_btn.setToolTip("Open the audio download folder in your file manager (e.g., File Explorer).")
        audio_dir_layout.addWidget(QLabel("Audio to:"))
        audio_dir_layout.addWidget(self.audio_dir_label)
        audio_dir_layout.addWidget(self.audio_dir_btn)
        audio_dir_layout.addWidget(self.open_audio_dir_btn)

        # Check for updates and View README buttons
        self.check_updates_btn = QPushButton("Check for yt-dlp updates")
        self.check_updates_btn.clicked.connect(self.check_for_updates)
        self.view_readme_btn = QPushButton("View README")
        self.view_readme_btn.clicked.connect(self.open_readme)
        updates_layout.addWidget(self.view_readme_btn)
        updates_layout.addStretch()
        updates_layout.addWidget(self.open_last_save_btn)
        updates_layout.addStretch()
        updates_layout.addWidget(self.check_updates_btn)

        # Small hint explaining tooltips
        hint_label = QLabel("Tip: Hover over items marked with '(i)' for more information.")
        hint_label.setStyleSheet("font-size: 11px; opacity: 0.8;")

        # Assemble layouts
        url_layout.addWidget(self.paste_btn)
        url_layout.addWidget(self.download_btn)
        url_layout.addWidget(self.url_input)
        main_layout.addLayout(url_layout)
        main_layout.addWidget(hint_label)
        main_layout.addWidget(self.audio_only_checkbox)
        main_layout.addLayout(override_layout)
        main_layout.addLayout(cookies_layout)
        main_layout.addLayout(cookies_file_layout)
        main_layout.addLayout(video_dir_layout)
        main_layout.addLayout(audio_dir_layout)
        main_layout.addWidget(self.status_display)
        main_layout.addLayout(updates_layout)
        self.setLayout(main_layout)

        # Apply initial enabled/disabled state for the last-save button
        self._update_last_save_button_state()

        # Restore window size if available
        if hasattr(self, 'window_size'):
            self.resize(QSize(*self.window_size))

        # Thread/worker placeholders
        self.thread = None
        self.worker = None

    def _set_cookies_file_enabled(self, enabled: bool):
        self.cookies_file_label.setEnabled(enabled)
        self.cookies_file_btn.setEnabled(enabled)

    def choose_cookies_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select cookies.txt file", os.getcwd(), "Text files (*.txt);;All files (*.*)")
        if file_path:
            self.cookies_file_path = file_path
            self.cookies_file_label.setText(file_path)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())

    def choose_video_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Video Download Directory", self.video_dir)
        if dir_path:
            self.video_dir = dir_path
            self.video_dir_label.setText(self.video_dir)

    def choose_audio_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Audio Download Directory", self.audio_dir)
        if dir_path:
            self.audio_dir = dir_path
            self.audio_dir_label.setText(self.audio_dir)

    def _open_directory_in_file_manager(self, dir_path: str):
        dir_path = (dir_path or "").strip()
        if not dir_path:
            QMessageBox.warning(self, OPEN_FOLDER_DIALOG_TITLE, "No folder is set.")
            return
        if not os.path.isdir(dir_path):
            QMessageBox.warning(self, OPEN_FOLDER_DIALOG_TITLE, f"Folder does not exist:\n{dir_path}")
            return
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))
        if not ok:
            QMessageBox.warning(self, OPEN_FOLDER_DIALOG_TITLE, f"Could not open folder:\n{dir_path}")

    def _update_last_save_button_state(self):
        enabled = bool((self.last_save_dir or "").strip()) and os.path.isdir(self.last_save_dir)
        self.open_last_save_btn.setEnabled(enabled)

    def _resolve_download_dirs(self, audio_only: bool, video_dir: str, audio_dir: str, override_save: bool):
        if not override_save:
            return video_dir, audio_dir
        if audio_only:
            dir_path = QFileDialog.getExistingDirectory(self, "Select Download Directory for Audio", audio_dir)
            if not dir_path:
                return None, None
            return video_dir, dir_path
        dir_path = QFileDialog.getExistingDirectory(self, "Select Download Directory for Video", video_dir)
        if not dir_path:
            return None, None
        return dir_path, audio_dir

    def _get_cookies_selection(self):
        use_cookies = self.use_cookies_checkbox.isChecked()
        use_cookies_file = self.use_cookies_file_checkbox.isChecked()
        if use_cookies_file and self.cookies_file_path:
            return None, self.cookies_file_path
        if use_cookies:
            browser = self.cookies_browser_combo.currentText()
            profile = self.cookies_profile_input.text().strip()
            cookies_browser = f"{browser}:{profile}" if profile else browser
            return cookies_browser, None
        return None, None

    def _start_worker(self, url: str, video_dir: str, audio_dir: str, audio_only: bool, cookies_browser, cookies_file):
        self.download_btn.setEnabled(False)
        self.status_display.append("")
        self.thread = QThread()
        self.worker = DownloadWorker(url, video_dir, audio_dir, audio_only, cookies_browser=cookies_browser, cookies_file=cookies_file)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.output.connect(self.status_display.append)
        self.worker.finished.connect(self.download_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def open_readme(self):
        dlg = ReadmeDialog(self)
        dlg.exec()

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_display.append("Please enter a URL.")
            return
        audio_only = self.audio_only_checkbox.isChecked()
        override_save = self.override_save_location_checkbox.isChecked()
        video_dir, audio_dir = self._resolve_download_dirs(audio_only, self.video_dir, self.audio_dir, override_save)
        if video_dir is None and audio_dir is None:
            self.status_display.append("Download cancelled.")
            return
        # Track the last save location (default or per-download override)
        self.last_save_dir = audio_dir if audio_only else video_dir
        self._update_last_save_button_state()
        cookies_browser, cookies_file = self._get_cookies_selection()
        self._start_worker(url, video_dir, audio_dir, audio_only, cookies_browser, cookies_file)

    def download_finished(self):
        self.download_btn.setEnabled(True)

    def check_for_updates(self):
        try:
            current = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
            current_version = current.stdout.strip() or current.stderr.strip()
            if current.returncode != 0:
                self.status_display.append(f"Could not determine current version. Output: {current_version}")
                return
            self.status_display.append(f"Current yt-dlp version: {current_version}")
        except Exception as e:
            self.status_display.append(f"Error checking current version: {e}")
            return
        try:
            with urllib.request.urlopen("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest") as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latest = data.get("tag_name") or data.get("name")
                if latest:
                    self.status_display.append(f"Latest yt-dlp release: {latest}")
                    if latest != current_version:
                        has_uv = shutil.which("uv") is not None
                        if has_uv:
                            self.status_display.append("Update available. To upgrade: 'uv pip install -U yt-dlp' (inside your venv)")
                        else:
                            self.status_display.append("Update available. To upgrade: 'python -m pip install -U yt-dlp'")
                    else:
                        self.status_display.append("You are up to date.")
                else:
                    self.status_display.append("Could not determine latest release from GitHub.")
        except Exception as e:
            self.status_display.append(f"Error checking latest release: {e}")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.video_dir = config.get("video_dir", self.video_dir)
                self.audio_dir = config.get("audio_dir", self.audio_dir)
                self.last_save_dir = config.get("last_save_dir", self.last_save_dir)
                self.window_size = config.get("window_size", None)
            except Exception:
                pass

    def save_config(self):
        config = {
            "video_dir": self.video_dir,
            "audio_dir": self.audio_dir,
            "last_save_dir": self.last_save_dir,
            "window_size": [self.width(), self.height()]
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f)
        except Exception:
            pass

    def closeEvent(self, event):
        self.save_config()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Style tooltips to stand out by swapping foreground/background with the app's palette
    pal = app.palette()
    bg = pal.color(QPalette.Window).name()
    fg = pal.color(QPalette.WindowText).name()
    app.setStyleSheet(f"QToolTip {{ color: {bg}; background-color: {fg}; border: 1px solid {bg}; padding: 4px; }}")
    window = YtDlpGui()
    window.show()
    sys.exit(app.exec())