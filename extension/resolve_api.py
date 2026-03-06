"""
extension/resolve_api.py
========================
DaVinci Resolve API への接続ブリッジ (PySide6 / スタンドアロン実行対応)

このモジュールは、DaVinci Resolve の外部プロセス（standalone Python）から
API に接続するためのユーティリティを提供します。
"""

import os
import sys
from typing import Any, Optional

# 内部で保持する Resolve インスタンス
_resolve_instance: Optional[Any] = None

def set_resolve_instance(resolve_obj: Any):
    """
    DaVinci Resolve の API オブジェクトを明示的にセットする。
    """
    global _resolve_instance
    _resolve_instance = resolve_obj

def get_resolve(resolve_obj: Optional[Any] = None) -> Optional[Any]:
    """
    DaVinci Resolve の API オブジェクトを取得する (内部/外部 ハイブリッド版)
    """
    global _resolve_instance

    # 1. 直接渡された場合はそれを使用 (最速・確実)
    if resolve_obj is not None:
        _resolve_instance = resolve_obj
        return resolve_obj

    # 2. すでにセットされているインスタンスを確認
    if _resolve_instance is not None:
        return _resolve_instance

    # 3. 内部実行時のグローバル変数を確認 (Scripts メニュー等からの起動)
    try:
        import __main__
        # Resolve 内部では __main__.resolve が定義されている
        if hasattr(__main__, 'resolve') and getattr(__main__, 'resolve') is not None:
            return getattr(__main__, 'resolve')
        # Fusion 内部の場合
        if hasattr(__main__, 'fusion') and getattr(__main__, 'fusion') is not None:
            return getattr(__main__, 'fusion').GetResolve()
    except Exception:
        pass

    # 3. 外部実行時 (standalone) のための接続ロジック
    if sys.platform == "win32":
        # Windows: 通常のインストールパス
        default_api_path = os.path.expandvars(r"%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
        default_lib_path = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
        script_api_path = os.environ.get("RESOLVE_SCRIPT_API", default_api_path)
        script_lib_path = os.environ.get("RESOLVE_SCRIPT_LIB", default_lib_path)
        
    elif sys.platform == "darwin":
        # macOS: 通常のインストールパス
        default_api_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
        default_lib_path = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
        script_api_path = os.environ.get("RESOLVE_SCRIPT_API", default_api_path)
        script_lib_path = os.environ.get("RESOLVE_SCRIPT_LIB", default_lib_path)
    
    elif sys.platform == "linux":
        # Linux: 通常のインストールパス
        default_api_path = "/opt/resolve/Developer/Scripting"
        default_lib_path = "/opt/resolve/libs/Fusion/fusionscript.so"
        script_api_path = os.environ.get("RESOLVE_SCRIPT_API", default_api_path)
        script_lib_path = os.environ.get("RESOLVE_SCRIPT_LIB", default_lib_path)
    else:
        script_api_path = os.environ.get("RESOLVE_SCRIPT_API", "")
        script_lib_path = os.environ.get("RESOLVE_SCRIPT_LIB", "")

    modules_path = os.path.join(script_api_path, "Modules")

    # 環境変数のセット (外部プロセスからの認識を助ける)
    if script_api_path:
        os.environ["RESOLVE_SCRIPT_API"] = script_api_path
    if script_lib_path:
        os.environ["RESOLVE_SCRIPT_LIB"] = script_lib_path

    if modules_path not in sys.path and os.path.exists(modules_path):
        sys.path.append(modules_path)

    # DLL ディレクトリの追加 (Windows + Python 3.8+)
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        try:
            os_bin_path = os.path.dirname(script_lib_path)
            if os.path.exists(os_bin_path):
                os.add_dll_directory(os_bin_path)
        except Exception:
            pass

    # 直結ロード試行
    if os.path.exists(script_lib_path):
        try:
            import importlib.util
            import importlib.machinery
            loader = importlib.machinery.ExtensionFileLoader("fusionscript", script_lib_path)
            spec = importlib.machinery.ModuleSpec("fusionscript", loader)
            fusionscript = importlib.util.module_from_spec(spec)
            loader.exec_module(fusionscript)
            
            resolve = fusionscript.GetResolve()
            if resolve:
                return resolve
        except Exception:
            pass

    # 標準的なインポート試行
    try:
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")
        if resolve:
            return resolve
    except Exception:
        pass

    return None

def seek_to_segment(timeline: Any, start_frame: int) -> bool:
    """
    指定された開始フレームにタイムラインの再生ヘッドを移動する。
    """
    if not timeline:
        return False
    try:
        return timeline.SetCurrentTimecode(str(start_frame))
    except Exception:
        # GetStartFrame オフセットなどを考慮した計算が必要な場合がある
        return False
