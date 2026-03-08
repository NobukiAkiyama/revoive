"""
scripts/resolve_launcher.py
==========================
DaVinci Resolve の Scripts メニューから GUI 版を起動するエントリーポイント。
"""

import os
import sys


def find_project_root() -> str:
    """ハードコードなしでプロジェクトルートを動的に解決する。"""
    try:
        base_path = os.path.realpath(__file__)
        return os.path.dirname(os.path.dirname(base_path))
    except NameError:
        pass

    if sys.argv and sys.argv[0]:
        base_path = os.path.realpath(sys.argv[0])
        if os.path.isfile(base_path):
            return os.path.dirname(os.path.dirname(base_path))

    return os.getcwd()


PROJECT_ROOT = find_project_root()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main() -> None:
    print(f"[ReVoice] GUI launcher started. (Root: {PROJECT_ROOT})")

    try:
        from extension.resolve_api import get_resolve
        from app_entry import main as app_main
    except ImportError as exc:
        print(f"[Fatal Error] Failed to load modules: {exc}")
        return

    resolve = get_resolve()
    if not resolve:
        print("[Error] DaVinci Resolve API connection failed.")
        return

    app_main(resolve)


if __name__ == "__main__":
    main()
