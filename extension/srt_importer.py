"""
extension/srt_importer.py
=========================
外部リファレンス (elosove.com p=963) に準拠した SRT インポート処理。
"""

import os
from typing import Any

def import_srt_to_resolve(resolve: Any, srt_path: str) -> bool:
    """
    SRT ファイルを現在のタイムラインの字幕トラックとしてインポートの準備を行う。
    リファレンス p=963 に基づき、ImportMedia を使用。
    """
    if not resolve or not srt_path or not os.path.exists(srt_path):
        return False

    try:
        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        media_pool = project.GetMediaPool()

        if not timeline:
            print("[srt_importer] タイムラインが見つかりません。")
            return False

        # 1. 字幕トラックの確認と追加 (p=963 準拠)
        # ※GetTrackCount('subtitle') を使用
        if timeline.GetTrackCount('subtitle') == 0:
            print("[srt_importer] 字幕トラックを追加します。")
            timeline.AddTrack('subtitle')

        # 2. メディアプールへインポート (p=963 では ImportMedia を使用)
        # 文字列としてパスを渡す
        import_result = media_pool.ImportMedia(srt_path.replace("\\", "/"))
        
        if import_result:
            print(f"[srt_importer] ファイル '{os.path.basename(srt_path)}' がメディアプールにインポートされました。")
            print(">>> 手動操作: メディアプールのSRTを右クリックし「タイムコードを使って字幕を挿入」を選択してください。")
            return True
        else:
            print("[srt_importer] インポートに失敗しました。")
            return False
            
    except Exception as e:
        print(f"[srt_importer] 例外が発生しました: {e}")
        return False
