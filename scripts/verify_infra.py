import os
import sys
import threading
import time
import json

# プロジェクトルートをパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings_manager import SettingsManager
from processor.workflow_engine import run_standard_workflow

def test_settings_manager() -> None:
    print(">>> [Test] SettingsManager Verification...")
    mgr = SettingsManager()
    config_path = os.path.join(PROJECT_ROOT, "config", "test_settings.json")
    
    # 1. 初期化とデフォルト値
    mgr.initialize(config_path)
    assert mgr.get("whisper.model") == "base"
    
    # 2. 値の更新と保存
    mgr.set("whisper.model", "large-v3")
    mgr.save()
    
    # 3. 再ロードして確認
    mgr.load()
    assert mgr.get("whisper.model") == "large-v3"
    print("   ✓ Persistence OK")

    # 4. スレッドセーフティ (簡易)
    def worker() -> None:
        for _ in range(100):
            mgr.set("gui.theme", "light")
            mgr.get("gui.theme")
            mgr.save()
    
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    print("   ✓ Thread-safety (no crash) OK")
    
    if os.path.exists(config_path):
        os.remove(config_path)

def test_engine_generator() -> None:
    print(">>> [Test] Engine Generator & Cancellation Verification...")
    stop_event = threading.Event()
    
    # ダミー設定
    settings = {
        "ffmpeg_path": "ffmpeg",
        "whisper": {"model": "tiny", "device": "cpu"},
        "ai": {"auto_refine": False}
    }
    
    # 存在しない動画パスでテスト (早めにエラーが出るはず)
    video_path = "non_existent.mp4"
    
    engine_gen = run_standard_workflow(
        video_path=video_path,
        settings=settings,
        fps=24.0,
        project_root=PROJECT_ROOT,
        stop_event=stop_event
    )
    
    # 1. 最初のステップで中断
    status, prog = next(engine_gen)
    print(f"   Step 1: {status} ({prog}%)")
    
    stop_event.set()
    print("   Sent Stop Signal")
    
    try:
        next_step = next(engine_gen)
        print(f"   Next step (should not happen): {next_step}")
    except StopIteration as e:
        print(f"   ✓ Interrupted successfully (Return: {e.value})")

if __name__ == "__main__":
    try:
        test_settings_manager()
        test_engine_generator()
        print("\n[ALL INFRA TESTS PASSED]")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
