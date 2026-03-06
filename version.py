"""
ReVoice Pro - Version Information
"""

VERSION_MAJOR = 2
VERSION_MINOR = 11
VERSION_PATCH = 0
VERSION_SUFFIX = "stable"  # "alpha", "beta", "rc" など

# 文字列形式 (v2.11.0)
__version__ = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
if VERSION_SUFFIX and VERSION_SUFFIX != "stable":
    __version__ += f"-{VERSION_SUFFIX}"

# 比較用タプル形式
VERSION_INFO = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

def get_version_string() -> str:
    """アプリケーション名を含めたフルバージョン文字列を返す"""
    return f"ReVoice Pro v{__version__}"

def is_release_build() -> bool:
    """開発用ビルドかリリース用ビルドかを判定"""
    return VERSION_SUFFIX == "stable"
