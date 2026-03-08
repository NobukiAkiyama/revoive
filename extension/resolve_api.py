"""
extension/resolve_api.py
========================
DaVinci Resolve API への接続ブリッジ (堅牢版)
"""

import os
import sys
from typing import Any, Optional, cast

import math
from typing import Any, Optional, cast, Dict

_resolve_instance: Optional[Any] = None

def frame_to_timecode(frame: int, fps: float) -> str:
    """
    Drop Frame (DF) 対応のタイムコード変換。
    """
    drop_frame_rates = [29.97, 59.94]
    is_df = any(abs(fps - df) < 0.01 for df in drop_frame_rates)

    if is_df:
        fps_round        = round(fps)
        drop_frames      = round(fps * 0.066666) # 2 or 4
        frames_per_10min = round(fps * 60 * 10)
        frames_per_min   = fps_round * 60 - drop_frames

        frame = frame % round(fps * 3600 * 24)
        d = math.floor(frame / frames_per_10min)
        m = frame % frames_per_10min

        if m > drop_frames:
            frame += drop_frames * 9 * d + drop_frames * math.floor((m - drop_frames) / frames_per_min)
        else:
            frame += drop_frames * 9 * d

        f  = frame % fps_round
        s  = math.floor(frame / fps_round) % 60
        mn = math.floor(math.floor(frame / fps_round) / 60) % 60
        h  = math.floor(math.floor(math.floor(frame / fps_round) / 60) / 60)
        sep = ";"
    else:
        fps_r = round(fps)
        f  = frame % fps_r
        s  = math.floor(frame / fps_r) % 60
        mn = math.floor(math.floor(frame / fps_r) / 60) % 60
        h  = math.floor(math.floor(math.floor(frame / fps_r) / 60) / 60)
        sep = ":"

    return f"{int(h):02}{sep}{int(mn):02}{sep}{int(s):02}{sep}{int(f):02}"

def get_timeline_mark_in_out(resolve: Any) -> Dict[str, Optional[int]]:
    """
    タイムラインの Mark In / Out フレームを取得する。
    """
    try:
        project = resolve.GetProjectManager().GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        mark_info = timeline.GetMarkInOut()
        video = mark_info.get("video", {})
        
        return {
            "in": video.get("in"),
            "out": video.get("out")
        }
    except Exception as e:
        print(f"[resolve] Error getting Mark In/Out: {e}")
        return {"in": None, "out": None}

def get_current_context() -> Dict[str, Any]:
    """
    現在の Resolve のプロジェクトとタイムラインの情報を取得する。
    """
    resolve = get_resolve()
    if not resolve:
        return {"error": "Resolve API not available"}

    try:
        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        if not project:
            return {"error": "No project open"}

        timeline = project.GetCurrentTimeline()
        if not timeline:
            return {
                "project_name": project.GetName(),
                "error": "No timeline open"
            }

        # 基本情報の取得
        mark_info = get_timeline_mark_in_out(resolve)
        
        return {
            "project_name": project.GetName(),
            "timeline_name": timeline.GetName(),
            "fps": float(timeline.GetSetting("timelineFrameRate")),
            "resolution": f"{timeline.GetSetting('timelineResolutionWidth')}x{timeline.GetSetting('timelineResolutionHeight')}",
            "mark_in": mark_info.get("in"),
            "mark_out": mark_info.get("out")
        }
    except Exception as e:
        return {"error": str(e)}

def get_resolve_lib_path() -> Optional[str]:
    """
    DaVinci Resolve のスクリプト用ライブラリ (fusionscript) のパスを特定する。
    優先順位:
    1. 環境変数 RESOLVE_SCRIPT_LIB
    2. Windows レジストリ (Winのみ)
    3. 標準のインストールパス
    """
    # 1. 環境変数
    env_path = os.environ.get("RESOLVE_SCRIPT_LIB")
    if env_path and os.path.exists(env_path):
        return env_path

    if sys.platform == "win32":
        # 2. Windows レジストリ検索
        # 通常の 64bit レジストリと 32bit 互換 (WOW6432Node) の両方を試行
        registry_paths = [
            r"SOFTWARE\Blackmagic Design\DaVinci Resolve",
            r"SOFTWARE\WOW6432Node\Blackmagic Design\DaVinci Resolve"
        ]
        
        for key_path in registry_paths:
            try:
                import winreg
                # HKLM を優先、失敗したら HKCU も一応確認
                for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                    try:
                        with winreg.OpenKey(root, key_path) as key:
                            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                            if install_path:
                                dll_path = os.path.join(install_path, "fusionscript.dll")
                                if os.path.exists(dll_path):
                                    print(f"[resolve] Found via Registry ({'HKLM' if root==winreg.HKEY_LOCAL_MACHINE else 'HKCU'} - {key_path}): {dll_path}")
                                    return dll_path
                    except FileNotFoundError:
                        continue
            except Exception as e:
                print(f"[resolve] Registry search error for {key_path}: {e}")
                pass

        # 3. Windows 標準パス
        standard_path = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
        if os.path.exists(standard_path):
            return standard_path

    elif sys.platform == "darwin":
        # macOS 標準パス
        standard_path = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
        if os.path.exists(standard_path):
            return standard_path
    
    else:
        # Linux 標準パス
        standard_path = "/opt/resolve/libs/Fusion/fusionscript.so"
        if os.path.exists(standard_path):
            return standard_path

    return None

def get_resolve(resolve_obj: Optional[Any] = None) -> Optional[Any]:
    global _resolve_instance
    if resolve_obj is not None:
        _resolve_instance = resolve_obj
        return resolve_obj
    if _resolve_instance is not None:
        return _resolve_instance

    # 既に Resolve 内で実行されている場合 (埋め込み Python)
    try:
        import __main__
        if hasattr(__main__, 'resolve') and getattr(__main__, 'resolve') is not None:
            return getattr(__main__, 'resolve')
        if hasattr(__main__, 'fusion') and getattr(__main__, 'fusion') is not None:
            return getattr(__main__, 'fusion').GetResolve()
    except Exception:
        pass

    # 外部プロセスからの接続試行
    script_lib_path = get_resolve_lib_path()
    if not script_lib_path:
        print("[resolve] Could find fusionscript library. Please ensure DaVinci Resolve is installed.")
        return None

    # Modules パスの追加 (Scripting/Modules)
    # 通常 lib パスの数階層上にある
    # Win: C:\Program Files\...\fusionscript.dll
    # API: %PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules
    if sys.platform == "win32":
        default_api_path = os.path.expandvars(r"%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
    elif sys.platform == "darwin":
        default_api_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
    else:
        default_api_path = "/opt/resolve/Developer/Scripting"

    script_api_path = os.environ.get("RESOLVE_SCRIPT_API", default_api_path)
    modules_path = os.path.join(script_api_path, "Modules")

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

    # 動的ロード
    try:
        import importlib.util
        import importlib.machinery
        loader = importlib.machinery.ExtensionFileLoader("fusionscript", script_lib_path)
        spec = importlib.machinery.ModuleSpec("fusionscript", loader)
        fusionscript = importlib.util.module_from_spec(spec)
        loader.exec_module(fusionscript)
        resolve = fusionscript.GetResolve()
        if resolve: 
            _resolve_instance = resolve
            return resolve
    except Exception as e:
        print(f"[resolve] External connection failed: {e}")

    return None

def render_timeline(resolve: Any, output_path: str) -> Optional[str]:
    """
    戻り値: JobId (string)
    """
    try:
        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        if not project:
            return None

        # 0. 既存ジョブの掃除 (JobId, jobId 両方のキーに対応)
        jobs = project.GetRenderJobList()
        for j in jobs:
            jid = j.get("JobId") or j.get("jobId")
            name = j.get("OutputFilename", "") or j.get("CustomName", "")
            if jid and "ReVoice_Temp" in name:
                project.DeleteRenderJob(jid)

        resolve.OpenPage("deliver")

        output_path = os.path.normpath(output_path)
        dir_name = os.path.dirname(output_path)
        base_name = os.path.basename(output_path)
        file_no_ext = os.path.splitext(base_name)[0]

        # 形式設定
        project.SetCurrentRenderFormatAndCodec("wav", "pcm")

        # Mark In/Out の取得と設定
        mark_info = get_timeline_mark_in_out(resolve)
        mark_in = mark_info.get("in")
        mark_out = mark_info.get("out")

        render_settings = {
            "SelectAllFrames": True if (mark_in is None and mark_out is None) else False,
            "TargetDir": dir_name,
            "CustomName": f"ReVoice_Temp_{file_no_ext}",
            "ExportVideo": False,
            "ExportAudio": True,
            "AudioBitDepth": 16,
            "AudioSampleRate": 48000
        }

        if mark_in is not None:
            render_settings["MarkIn"] = mark_in
        if mark_out is not None:
            render_settings["MarkOut"] = mark_out
        
        if not project.SetRenderSettings(render_settings):
            return None

        job_id = project.AddRenderJob()
        if job_id:
            print(f"[resolve] Added render job: {job_id}")
            project.StartRendering(job_id) # 単一IDまたはリスト
            return cast(str, job_id)
        return None
    except Exception as e:
        print(f"[resolve] Render error: {e}")
        return None

def is_rendering_finished(resolve: Any, job_id: str) -> bool:
    try:
        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        status = project.GetRenderJobStatus(job_id)
        
        if not status:
            return False
            
        # キー名の揺れに対応 (JobStatus, jobStatus)
        job_status = (status.get("JobStatus") or status.get("jobStatus", "")).lower()
        completion = status.get("CompletionPercentage", 0)
        
        print(f"[resolve] Job Status: {job_status} ({completion}%)")

        # 完了判定の拡張
        if job_status in ["complete", "completed"]:
            return True
        if job_status == "failed":
            print(f"[resolve] Render job {job_id} failed.")
            return True
        
        # 100% でレンダリング中でない場合は完了とみなす (バグ回避)
        if completion == 100 and not project.IsRenderingInProgress():
            print("[resolve] Rendering finished (detected via idle status).")
            return True
            
        return False
    except Exception:
        return False

def cleanup_render_jobs(resolve: Any, job_id: Optional[str] = None) -> None:
    try:
        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        if job_id:
            project.DeleteRenderJob(job_id)
            print(f"[resolve] Deleted temporary job: {job_id}")
    except Exception:
        pass

def seek_to_segment(timeline: Any, start_frame: int) -> bool:
    if not timeline: return False
    try: return cast(bool, timeline.SetCurrentTimecode(str(start_frame)))
    except Exception: return False
