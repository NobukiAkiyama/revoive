"""
app_entry.py (Backend Driver for Subtitle Pivot)
===============================================
ロジックの動作検証および UI 連携用の最小限のエントリポイント。
UI に関してはユーザー側で実装することを想定し、バックエンドの呼び出しに専念します。
"""

import sys
import os
from typing import Any, Optional

from utils.path_manager import get_project_root, get_config_path, ensure_ffmpeg_env

# プロジェクトルートの動的解決 (path_manager に一任)
PROJECT_ROOT = get_project_root()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
import ffmpeg
from config.settings_manager import SettingsManager
from processor.workflow_engine import run_standard_workflow
from extension.resolve_api import get_resolve, get_timeline_mark_in_out, frame_to_timecode
from utils.version import get_version_string

# シングルトン設定マネージャーの取得
settings_mgr = SettingsManager()

def get_video_fps(video_path: str) -> float:
    """
    ffmpeg-python を使用してビデオの FPS を取得する。
    """
    try:
        # 手動でのタイムアウト設定 (ffmpeg-python の probe には timeout 引数がないため、
        # subprocess を直接呼ぶか、あるいは事前に環境を整える)
        # ここでは advice に従い、数秒のタイムアウトを意識した実装にする。
        # ffmpeg.probe は内部で subprocess.run を呼んでいるが、timeout 引数を直接は取らない。
        # 代わりに cmd を構築して実行する。
        
        import subprocess
        import json

        cmd = [
            'ffprobe', '-v', 'quiet', 
            '-print_format', 'json', 
            '-show_streams', '-show_format', 
            video_path
        ]
        
        # 5秒のタイムアウトを設定
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
        probe = json.loads(result.stdout)
        
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        avg_frame_rate = video_info['avg_frame_rate']
        if '/' in avg_frame_rate:
            num, den = map(int, avg_frame_rate.split('/'))
            if den == 0: return 24.0
            return num / den
        return float(avg_frame_rate)
    except subprocess.TimeoutExpired:
        print(f"[Warning] ffprobe timed out for {video_path}. Using default 24.0")
        return 24.0
    except Exception as e:
        print(f"[Warning] Failed to detect FPS: {e}. Using default 24.0")
        return 24.0

def run_headless_workflow(args: argparse.Namespace) -> None:
    """
    GUIなしでワークフローを完結させる。
    """
    print(f"\n=== {get_version_string()} (Headless Mode) ===")
    
    try:
        # SettingsManager の初期化
        config_path = get_config_path()
        settings_mgr.initialize(config_path)

        # 0. 先に FFmpeg 環境を確保する (Health Check で検知できるように)
        ffmpeg_dir = ensure_ffmpeg_env()
        if ffmpeg_dir:
            ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
            if os.path.exists(ffmpeg_exe):
                settings_mgr.set("ffmpeg_path", ffmpeg_exe)
                # print(f"[Info] FFmpeg path set to: {ffmpeg_exe}")
            else:
                settings_mgr.set("ffmpeg_path", "ffmpeg")

        # 1. システム健全性チェック
        from utils.health_check import HealthCheck
        api_key = settings_mgr.get("ai.api_key")
        health_results = HealthCheck.run_all(api_key=api_key)
        
        # 2. Resolve コンテキストの表示
        from extension.resolve_api import get_current_context
        ctx = get_current_context()
        if ctx and "error" not in ctx:
            print(f"--- Resolve Context ---")
            print(f"Project  : {ctx.get('project_name')}")
            print(f"Timeline : {ctx.get('timeline_name')}")
            print(f"Range    : {ctx.get('mark_in')} - {ctx.get('mark_out')}")
            print(f"FPS      : {ctx.get('fps')}")
            print(f"-----------------------\n")
        
        # 3. 致命的なエラーの判定 (FFmpeg は必須)
        critical_failures = [r for r in health_results if not r["status"] and r["name"] in ["FFmpeg"]]
        if critical_failures:
            print("\n[Error] Critical issues: FFmpeg is required to run.")
            sys.exit(1)
        
        # Gemini がダメな場合は設定で自動修正をオフにする
        gemini_status = next((r for r in health_results if r["name"] == "Gemini API"), None)
        if gemini_status and not gemini_status["status"]:
            print("[Info] Gemini API is unavailable. AI Refinement will be skipped.")
            settings_mgr.set("ai.auto_refine", False)
        elif args.refine:
            settings_mgr.set("ai.auto_refine", True)
        
        # FPS の決定
        fps = args.fps
        if fps <= 0:
            if ctx and "error" not in ctx and ctx.get("fps"):
                fps = ctx["fps"]
                print(f"[Info] Using Resolve timeline FPS: {fps}")
            else:
                fps = get_video_fps(args.video)
        
        print(f"[Info] Input Video: {args.video}")
        print(f"[Info] Target FPS: {fps:.3f}")

        # Resolve から Mark In/Out を取得
        offset_frame = 0
        if "error" not in ctx:
            mark_in = ctx.get("mark_in")
            mark_out = ctx.get("mark_out")
            if mark_in is not None or mark_out is not None:
                offset_frame = mark_in if mark_in is not None else 0
                in_str = frame_to_timecode(mark_in, fps) if mark_in is not None else "Start"
                out_str = frame_to_timecode(mark_out, fps) if mark_out is not None else "End"
                print(f"[Info] Timeline Range: {in_str} - {out_str} (Offset: {offset_frame}f)")

        # エンジンの実行 (ジェネレーター)
        engine_gen = run_standard_workflow(
            video_path=args.video,
            settings=settings_mgr.all_settings,
            fps=fps,
            project_root=PROJECT_ROOT,
            offset_frame=offset_frame,
            log_callback=lambda msg: print(msg)
        )

        srt_path: Optional[str] = None
        # ジェネレーターを回し、最後に StopIteration から戻り値を取得
        while True:
            try:
                status, prog = next(engine_gen)
                sys.stdout.write(f"\r[Progress] {prog:>3}% : {status:<20}")
                sys.stdout.flush()
            except StopIteration as e:
                srt_path = e.value
                print() # 完了後の改行
                break

        if srt_path is not None:
            # 型ヒントを確実に str にするためにキャスト (IDE linter 対策)
            from typing import cast
            final_srt = cast(str, srt_path)
            if os.path.exists(final_srt):
                print(f"\n[Success] SRT Generated: {final_srt}")
                if os.name == 'nt':
                    try: os.startfile(os.path.dirname(final_srt))
                    except: pass
                print("\nProcessing complete successfully. Returning to Resolve...")
                return # 成功時は input() をスキップして即終了
        
        print("\n[Error] Workflow finished but no SRT was produced.")

    except Exception:
        import traceback
        error_details: Optional[str] = traceback.format_exc()
        print("\n" + "="*50)
        print("!!! CRITICAL ERROR OCCURRED !!!")
        print("="*50)
        print(error_details)
    
    # 失敗時、または例外発生時のみ、ユーザーが確認できるまで閉じない
    print("\n" + "-"*30)
    input("Press Enter to close this window...")
    
    # error_details が定義されている（＝例外発生）か、srt_path が取得できていない場合は失敗とみなす
    if 'error_details' in locals() or srt_path is None:
        sys.exit(1)

def init_q_application() -> Optional[Any]:
    """
    QApplication の起動
    """
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        return app
    except ImportError:
        print("[Error] PySide6 がインストールされていません。GUIモードは利用できません。")
        return None

def run_gui_mode(resolve_obj: Optional[Any] = None) -> None:
    """
    GUIモードでの起動
    """
    app = init_q_application()
    if not app:
        return

    # 設定の初期化
    config_path = get_config_path()
    settings_mgr.initialize(config_path)

    # FFmpeg 環境の確保
    ffmpeg_dir = ensure_ffmpeg_env()
    if ffmpeg_dir:
        settings_mgr.set("ffmpeg_path", ffmpeg_dir)

    print(f"[Info] Starting ReVoice {get_version_string()} GUI...")
    # TODO: MainWindow の実装と表示
    # from ui.main_window import MainWindow
    # window = MainWindow(settings_mgr, resolve_obj)
    # window.show()
    
    # ダミーとしての待機 (実際は app.exec())
    print("[Pending] GUI implementation is required.")
    # sys.exit(app.exec())

def main() -> None:
    parser = argparse.ArgumentParser(description="ReVoice Subtitle Edition")
    parser.add_argument("video", nargs="?", help="Video file path (Headless only)")
    parser.add_argument("--headless", action="store_true", help="Run in headless CLI mode")
    parser.add_argument("--refine", action="store_true", help="Force enable AI refinement")
    parser.add_argument("--fps", type=float, default=0.0, help="Override FPS")
    parser.add_argument("--config", help="Custom settings.json path")
    parser.add_argument("--version", action="version", version=get_version_string())

    args = parser.parse_args()
    resolve = get_resolve()

    # モード判定
    if args.headless or args.video:
        if not args.video:
            print("[Error] Video path is required for headless mode.")
            sys.exit(1)
        run_headless_workflow(args)
    else:
        run_gui_mode(resolve)

if __name__ == "__main__":
    main()

