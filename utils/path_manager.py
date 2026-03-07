import os
import sys
import logging
from typing import Optional, Any

# static-ffmpeg の型ヒントを Any で許容し、mypy の警告を回避
static_ffmpeg: Any
try:
    import static_ffmpeg
except ImportError:
    static_ffmpeg = None

# プロジェクトルートの決定
# os.path.realpath を使用してシンボリックリンク等を解決し、物理パスを特定する
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def get_project_root() -> str:
    """物理的なプロジェクトルートを返す。"""
    return PROJECT_ROOT

def resolve_path(path: str) -> str:
    """
    相対パスまたはプレースホルダーを絶対パスに変換する。
    """
    if not path:
        return ""
    
    # プレースホルダーの置換
    path = path.replace("{PROJECT_ROOT}", PROJECT_ROOT)
    
    # 相対パス（かつプレースホルダー置換後も相対パス）なら結合
    if not os.path.isabs(path):
        return os.path.normpath(os.path.join(PROJECT_ROOT, path))
    
    return os.path.normpath(path)

def to_relative_path(abs_path: str) -> str:
    """
    絶対パスをプロジェクトルートからの相対パスに変換する。
    可能であれば {PROJECT_ROOT} プレースホルダーを使用する。
    """
    if not abs_path:
        return ""
    
    abs_path = os.path.normpath(abs_path)
    root = os.path.normpath(PROJECT_ROOT)
    
    if abs_path.startswith(root):
        rel = os.path.relpath(abs_path, root)
        # Windows でもスラッシュに統一（ポータビリティのため）
        return rel.replace("\\", "/")
    
    return abs_path

# --- 各コンポーネント用パス生成メソッド ---

def get_output_dir() -> str:
    """データ出力先ディレクトリを返す。"""
    path = os.path.join(PROJECT_ROOT, "data", "output")
    os.makedirs(path, exist_ok=True)
    return os.path.normpath(path)

def get_config_path(filename: str = "settings.json") -> str:
    """設定ファイルのパスを返す。"""
    return os.path.normpath(os.path.join(PROJECT_ROOT, "config", filename))

def get_data_dir() -> str:
    """一般データ用ディレクトリを返す。"""
    path = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(path, exist_ok=True)
    return os.path.normpath(path)

def ensure_ffmpeg_env() -> Optional[str]:
    """
    FFmpeg/ffprobe の環境を整える。
    static-ffmpeg が利用可能な場合はそのパスを PATH に追加する。
    戻り値: FFmpeg 実行ファイルが含まれるディレクトリのパス
    """
    if static_ffmpeg:
        try:
            # static-ffmpeg のパスを PATH に追加
            static_ffmpeg.add_paths()
            
            # 追加されたパスを特定して返す (static-ffmpeg の内部を少し覗く必要があるが、
            # 一般的には sys.path や os.environ['PATH'] に追加される)
            # シンプルに or で PATH から抽出を試みるロジック
            import shutil
            ffmpeg_exe = shutil.which("ffmpeg")
            if ffmpeg_exe:
                dir_path = os.path.dirname(ffmpeg_exe)
                print(f"[Info] FFmpeg environment secured: {dir_path}")
                return dir_path
        except Exception as e:
            print(f"[Warning] Failed to setup static-ffmpeg: {e}")
    
    # システムの PATH にあるか確認
    import shutil
    ffmpeg_exe = shutil.which("ffmpeg")
    if ffmpeg_exe:
        return os.path.dirname(ffmpeg_exe)
        
    return None
