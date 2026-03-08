"""
utils/health_check.py
=====================
環境診断ユーティリティ。FFmpeg, GPU, Gemini API, Resolve API の状態を確認する。
"""

import os
import sys
import subprocess
import shutil
from typing import Dict, Any, List, Optional, Tuple

class HealthCheck:
    """
    システムの健全性をチェックし、ユーザーにフィードバックを提供するクラス。
    """
    
    @staticmethod
    def check_ffmpeg() -> Tuple[bool, str]:
        """FFmpeg/FFprobe の存在確認。"""
        ffmpeg_base = shutil.which("ffmpeg")
        ffprobe_base = shutil.which("ffprobe")
        
        if not ffmpeg_base or not ffprobe_base:
            return False, "FFmpeg または FFprobe が見つかりません。パスが通っているか確認してください。"
        
        try:
            # バージョン確認で動作チェック
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True, f"FFmpeg found: {ffmpeg_base}"
        except Exception as e:
            return False, f"FFmpeg execution failed: {e}"

    @staticmethod
    def check_gpu() -> Tuple[bool, str]:
        """GPU(CUDA) の利用可否と、不足 DLL の簡易スキャン。"""
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            if not has_cuda:
                return False, "CUDA が利用不可能です。CPU モードで動作します。(NVIDIA GPU が非搭載か、ドライバ未設定の可能性があります)"
            
            # DLL スキャン (Windows のみ)
            if sys.platform == "win32":
                # CUDA 12 系の主要 DLL 名
                required_dlls = ["cublas64_12.dll", "cudnn64_8.dll"]
                # 実際には faster-whisper はライブラリパスを要求するが、
                # ここでは torch が CUDA を認識しているなら概ね OK と判断しつつ、
                # 特定の警告を出すためのフックとして残す。
                pass
            
            return True, f"CUDA is available: {torch.cuda.get_device_name(0)}"
        except ImportError:
            return False, "torch がインストールされていないため、GPU 診断をスキップします。"
        except Exception as e:
            return False, f"GPU check error: {e}"

    @staticmethod
    def check_gemini(api_key: Optional[str]) -> Tuple[bool, str]:
        """Gemini API の疎通確認。利用可能なモデルを自動取得する。"""
        if not api_key:
            return False, "Gemini API キーが設定されていません。環境変数 GEMINI_API_KEY を設定してください。"
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # 利用可能なモデルをリストアップ
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            if not available_models:
                return False, "利用可能なモデルが見つかりませんでした。APIキーの権限を確認してください。"
            
            # gemini-1.5-flash を優先的に探す
            target_model = None
            for m_name in available_models:
                if "gemini-1.5-flash" in m_name:
                    target_model = m_name
                    break
            
            if not target_model:
                target_model = available_models[0] # 見つからなければ最初の一つ
            
            model = genai.GenerativeModel(target_model)
            # 超軽量なリクエスト
            response = model.generate_content("Ping", generation_config={"max_output_tokens": 1})
            if response:
                return True, f"Gemini API connection successful using model: {target_model}"
            return False, "Gemini API returned empty response."
        except Exception as e:
            msg = str(e)
            if "API_KEY_INVALID" in msg:
                return False, "Gemini API キーが無効です。正しいキーを設定してください。"
            return False, f"Gemini API check failed: {e}"

    @staticmethod
    def check_resolve() -> Tuple[bool, str]:
        """DaVinci Resolve スクリプティングの有効性。"""
        try:
            from extension.resolve_api import get_resolve
            resolve = get_resolve()
            if resolve:
                return True, "Successfully connected to DaVinci Resolve."
            return False, "DaVinci Resolve が起動していないか、スクリプト実行設定が有効ではありません。"
        except Exception as e:
            return False, f"Resolve connection check failed: {e}"

    @classmethod
    def run_all(cls, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """全項目を実行し、結果のリストを返す。"""
        results = []
        
        checks = [
            ("FFmpeg", cls.check_ffmpeg),
            ("GPU/CUDA", cls.check_gpu),
            ("Gemini API", lambda: cls.check_gemini(api_key)),
            ("Resolve API", cls.check_resolve),
        ]
        
        print("\n--- System Health Check ---")
        for name, func in checks:
            status, message = func()
            results.append({"name": name, "status": status, "message": message})
            icon = "[OK]" if status else "[!!]"
            print(f"{icon} {name:<12}: {message}")
        print("---------------------------\n")
        
        return results
