"""
scripts/resolve_launcher.py
==========================
DaVinci Resolve の Scripts メニューから実行されるエントリーポイント。
"""

import os
import sys

def find_project_root() -> str:
    """
    ハードコードされたパスを一切使わず、動的にプロジェクトルートを特定する。
    """
    # 1. __file__ が利用可能な場合 (realpath でシンボリックリンクを解決)
    try:
        base_path = os.path.realpath(__file__)
        # scripts/resolve_launcher.py の 2 階層上がルート
        return os.path.dirname(os.path.dirname(base_path))
    except NameError:
        pass

    # 2. sys.argv[0] (実行時の第一引数) を確認
    if sys.argv and sys.argv[0]:
        base_path = os.path.realpath(sys.argv[0])
        if os.path.isfile(base_path):
            return os.path.dirname(os.path.dirname(base_path))

    # 3. カレントディレクトリ (Resolve 内部実行時の標準的な挙動)
    return os.getcwd()

PROJECT_ROOT = find_project_root()

# sys.path に追加して utils 等をインポート可能にする
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 自作モジュールのインポート
try:
    from utils.path_manager import get_output_dir
except ImportError:
    # 万が一インポートできない場合のエラー表示
    print(f"[Fatal Error] Could not find project structure at: {PROJECT_ROOT}")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

import time
import subprocess
import importlib
import glob
from typing import Any

# モジュールの強制リロード
import extension.resolve_api
import extension.srt_importer
importlib.reload(extension.resolve_api)
importlib.reload(extension.srt_importer)

from extension.resolve_api import get_resolve, render_timeline, is_rendering_finished, cleanup_render_jobs
from extension.srt_importer import import_srt_to_resolve

def main() -> None:
    print(f"[ReVoice] Internal launcher started. (Root: {PROJECT_ROOT})")
    resolve = get_resolve()
    if not resolve:
        print("[Error] DaVinci Resolve API connection failed.")
        return

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    if not project:
        print("[Error] No active project found.")
        return

    data_dir = get_output_dir()
    temp_wav = os.path.join(data_dir, "resolve_render_temp.wav")

    # 1. レンダリング
    job_id = render_timeline(resolve, temp_wav)
    if not job_id: return

    # 2. 完了待ち
    render_success = False
    try:
        while not is_rendering_finished(resolve, job_id):
            time.sleep(2)
        else:
            render_success = True
    except KeyboardInterrupt: pass
    finally:
        cleanup_render_jobs(resolve, job_id)

    if render_success:
        # 3. 最新の出力ファイルを特定
        all_files = glob.glob(os.path.join(data_dir, "*"))
        files_only = [f for f in all_files if os.path.isfile(f) and not f.endswith(".srt")]
        if not files_only: return
        latest_input = max(files_only, key=os.path.getmtime)

        # 4. 外部プロセス起動 (システムの Python を使用)
        python_exe = "python"
        app_entry = os.path.normpath(os.path.join(PROJECT_ROOT, "app_entry.py"))
        cmd = [python_exe, app_entry, latest_input, "--headless", "--refine"]

        print(f"[ReVoice] Launching Headless Workflow...")
        try:
            creation_flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            process = subprocess.Popen(cmd, cwd=PROJECT_ROOT, creationflags=creation_flags)
            print("[ReVoice] Waiting for transcription process...")
            process.wait() 
            
            print("[ReVoice] Process finished. Importing results...")
            
            # 5. 生成された最新の SRT をインポート
            srt_files = glob.glob(os.path.join(data_dir, "*.srt"))
            if srt_files:
                latest_srt = max(srt_files, key=os.path.getmtime)
                if import_srt_to_resolve(resolve, latest_srt):
                    print("[ReVoice] SUCCESS: SRT imported.")
                    resolve.OpenPage("edit")
                else:
                    print("[Error] Import failed.")
            else:
                print("[Error] No SRT found.")

        except Exception as e:
            print(f"[Error] Bridge execution failed: {e}")

if __name__ == "__main__":
    main()
