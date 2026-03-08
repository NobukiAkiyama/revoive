import os
import json
import threading
from typing import Any, Dict, Optional, cast

class SettingsManager:
    """
    アプリケーション設定を一括管理するシングルトン・マネージャー。
    定数・デフォルト値・環境変数・JSONファイルを統合する。
    """
    _instance: Optional['SettingsManager'] = None
    _lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> 'SettingsManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SettingsManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._settings: Dict[str, Any] = {}
        self._config_path: Optional[str] = None
        self._save_lock = threading.Lock()
        
        # デフォルト設定
        self._default_settings = {
            "ffmpeg_path": "ffmpeg",
            "whisper": {
                "model": "base",
                "device": "auto",
                "language": "ja",
                "vad_filter": True,
                "min_speech_duration_ms": 250
            },
            "ai": {
                "api_key": "",
                "auto_refine": True,
                "refine_instruction": "自然な日本語の字幕に修正してください。"
            },
            "gui": {
                "theme": "dark",
                "auto_start": False
            }
        }
        self._initialized = True

    def initialize(self, config_path: str) -> None:
        """設定ファイルを読み込み、初期化する。"""
        self._config_path = os.path.normpath(config_path)
        self.load()
        self._merge_env_vars()

    def _merge_env_vars(self) -> None:
        """環境変数からの上書き (GEMINI_API_KEY等)"""
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            if "ai" not in self._settings:
                self._settings["ai"] = {}
            self._settings["ai"]["api_key"] = gemini_key

    def load(self) -> None:
        """JSONファイルから設定をロードする。"""
        with self._save_lock:
            # 1. デフォルト値をベースにする
            self._settings = json.loads(json.dumps(self._default_settings))
            
            config_path = self._config_path
            if config_path and os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        disk_settings = json.load(f)
                        self._deep_update(self._settings, disk_settings)
                except Exception as e:
                    print(f"[Settings] Failed to load {self._config_path}: {e}")

    def save(self) -> None:
        """現在の設定をJSONファイルに保存する。"""
        config_path = self._config_path
        if not config_path:
            return

        with self._save_lock:
            try:
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(self._settings, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[Settings] Failed to save {config_path}: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        ドット区切りのパスで設定を取得する (例: 'whisper.model')。
        スレッドセーフな読み取りを保証するため、コピーを返すかロックを検討。
        """
        with self._save_lock: # 読み取り時も一応ロック
            keys = key_path.split('.')
            value = self._settings
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    def set(self, key_path: str, value: Any) -> None:
        """ドット区切りのパスで設定を更新する。"""
        with self._save_lock:
            keys = key_path.split('.')
            target = self._settings
            for k in keys[:-1]:
                if not isinstance(target, dict):
                    break
                if k not in target or not isinstance(target[k], dict):
                    target[k] = {}
                target = target[k]
            
            if isinstance(target, dict) and len(keys) > 0:
                key = keys[-1]
                # バリデーション
                if key_path == "whisper.model":
                    valid_models = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]
                    if value not in valid_models:
                        print(f"[Settings] Warning: Invalid whisper model '{value}'. Keeping default.")
                        return
                elif key_path == "whisper.min_speech_duration_ms":
                    if not isinstance(value, (int, float)) or value < 0:
                        print(f"[Settings] Warning: Invalid duration '{value}'. Must be >= 0.")
                        return
                
                target[key] = value

    def _deep_update(self, base: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """辞書を再帰的に更新する。"""
        for k, v in updates.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

    @property
    def all_settings(self) -> Dict[str, Any]:
        """全設定のコピーを返す。"""
        with self._save_lock:
            return cast(Dict[str, Any], json.loads(json.dumps(self._settings)))
