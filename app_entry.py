"""
app_entry.py
============
GUI 版 ReVoice のエントリーポイント。
UI スケルトンを表示し、処理ロジック接続は別工程で実施する。
"""

import sys
from typing import Any, Optional

from utils.path_manager import get_project_root, get_config_path, ensure_ffmpeg_env
from config.settings_manager import SettingsManager
from extension.resolve_api import get_resolve
from ui.gui_bootstrap import GuiBootstrapper
from ui.main_window import ReVoiceMainWindow
from utils.version import get_version_string

# プロジェクトルートの動的解決
PROJECT_ROOT = get_project_root()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# シングルトン設定マネージャー
settings_mgr = SettingsManager()


def init_q_application() -> Optional[Any]:
    """QApplication を初期化して返す。"""
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        return app
    except ImportError:
        print("[Error] PySide6 がインストールされていません。GUI モードは利用できません。")
        return None


def run_gui_mode(resolve_obj: Optional[Any] = None) -> int:
    """
    GUI モードを起動する。
    起動準備・依存初期化を実施し、UI スケルトンを表示する。
    """
    app = init_q_application()
    if not app:
        return 1

    config_path = get_config_path()
    settings_mgr.initialize(config_path)

    ffmpeg_dir = ensure_ffmpeg_env()
    if ffmpeg_dir:
        settings_mgr.set("ffmpeg_path", ffmpeg_dir)

    resolve = resolve_obj or get_resolve()

    print(f"[Info] Starting ReVoice {get_version_string()} GUI bootstrap...")
    bootstrapper = GuiBootstrapper(
        app=app,
        resolve=resolve,
        settings_manager=settings_mgr,
        project_root=PROJECT_ROOT,
    )
    runtime = bootstrapper.prepare()

    window = ReVoiceMainWindow(resolve=runtime.resolve, settings=runtime.settings)
    window.show()
    return app.exec()


def main(resolve_obj: Optional[Any] = None) -> int:
    """アプリケーションのメインエントリー。"""
    return run_gui_mode(resolve_obj=resolve_obj)


if __name__ == "__main__":
    raise SystemExit(main())
