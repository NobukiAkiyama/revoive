import os
import sys

# プロジェクトルートの決定
# utils/path_manager.py にあるため、2回上の階層がルート
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

def get_project_root() -> str:
    return PROJECT_ROOT
