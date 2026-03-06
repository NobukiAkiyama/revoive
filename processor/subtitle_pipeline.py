"""
processor/subtitle_pipeline.py
==============================
外部リファレンス (elosove.com p=923/963) に準拠した字幕生成パイプライン。
"""

import os
import csv
import subprocess
from typing import List, Optional, Callable
from processor.base_transcriber import TranscriptSegment
from processor.adapters.whisper_transcriber import WhisperTranscriber
from processor.ai_editor import AIEditor

class SubtitlePipeline:
    ai_editor: Optional[AIEditor]
    
    def __init__(self, settings: dict):
        self.settings = settings
        self.transcriber = WhisperTranscriber(settings)
        
        # プロジェクトルートの動的取得 (processor/ 階層の親)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # AI Editor の初期化
        api_key = settings.get("ai", {}).get("api_key") or os.getenv("GEMINI_API_KEY")
        self.ai_editor = AIEditor(api_key=api_key) if api_key else None
        
        # FFmpeg パスの検証
        self.ffmpeg_path = self.validate_ffmpeg_path(settings.get("ffmpeg_path", "ffmpeg"))

    def validate_ffmpeg_path(self, path: str) -> str:
        """
        指定された FFmpeg パスが有効か検証する。
        無効な場合は static-ffmpeg の使用を試みる。
        """
        try:
            # 指定パスでバージョン確認を試行
            subprocess.run([path, "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[pipeline] Valid FFmpeg found at: {path}")
            return path
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"[pipeline] FFmpeg not found or invalid at: {path}. Trying static-ffmpeg fallback...")
            try:
                import static_ffmpeg
                # パスを通す
                static_ffmpeg.add_paths()
                # static_ffmpeg が追加したパスで再確認 (通常は 'ffmpeg' で通るようになる)
                subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("[pipeline] static-ffmpeg successfully initialized.")
                return "ffmpeg"
            except (ImportError, subprocess.CalledProcessError):
                print("[Warning] No valid FFmpeg found. Extraction may fail.")
                return path # 失敗しても元のパスを返しておく

    def extract_audio_ffmpeg(self, video_path: str, output_wav_path: str) -> bool:
        """ 
        ffmpeg を使用して動画から音声を抽出する。
        仕様: 16000Hz, Mono, 16bit PCM (Whisper最適設定)
        """
        try:
            os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
            
            cmd = [
                self.ffmpeg_path, '-y',
                '-i', video_path,
                '-vn', # 映像なし
                '-ac', '1', # モノラル
                '-ar', '16000', # 16kHz
                '-acodec', 'pcm_s16le', # 16-bit
                output_wav_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return os.path.exists(output_wav_path)
        except Exception as e:
            print(f"[pipeline] ffmpeg error: {e}")
            return False

    def segments_to_csv(self, segments: List[TranscriptSegment], output_path: str, fps: float) -> bool:
        """ 
        リファレンス p=923 に準拠した CSV 出力。 
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['speech start time', 'speech duration', 'speech 2 txt'])
                for seg in segments:
                    start_frame = int(seg.start * fps)
                    duration = seg.end - seg.start
                    writer.writerow([start_frame, f"{duration:.3f}", seg.text])
            return True
        except Exception as e:
            print(f"[pipeline] segments_to_csv error: {e}")
            return False

    def csv_to_srt(self, csv_path: str, output_path: str, fps: float) -> bool:
        """ 
        リファレンス p=963 に準拠した SRT 変換。
        """
        try:
            def convert_seconds_to_srt_format(frame: int, fps_val: float) -> str:
                seconds = frame / fps_val
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                seconds_left = seconds % 60
                seconds_int = int(seconds_left)
                milliseconds = int((seconds_left - seconds_int) * 1000)
                return f"{hours:02}:{minutes:02}:{seconds_int:02},{milliseconds:03}"

            rows = []
            if not os.path.exists(csv_path):
                print(f"[pipeline] CSV file not found: {csv_path}")
                return False

            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, row in enumerate(rows):
                    try:
                        start_frame = int(row['speech start time'])
                        duration_sec = float(row['speech duration'])
                        text = row['speech 2 txt']

                        start_time_str = convert_seconds_to_srt_format(start_frame, fps)
                        end_frame = start_frame + int(duration_sec * fps)
                        end_time_str = convert_seconds_to_srt_format(end_frame, fps)

                        f.write(f"{i+1}\n")
                        f.write(f"{start_time_str} --> {end_time_str}\n")
                        f.write(f"{text}\n\n")
                    except Exception as e_row:
                        print(f"[pipeline] Skipping row {i} due to error: {e_row}")
            return True
        except Exception as e:
            print(f"[pipeline] csv_to_srt error: {e}")
            return False

    def run_full_pipeline(self, audio_path: str, output_base_name: str, fps: float, log_callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """ 
        音声 -> CSV -> SRT の一連の流れ。
        audio_path: ユーザーから受け取った絶対パス or 内部解決済みパス
        output_base_name: 出力ファイルのベース名（拡張子なし、絶対パス推奨）
        """
        try:
            def log(msg):
                if log_callback: log_callback(msg)
                else: print(msg)

            # パスの正規化 (Windows/Unix 共通)
            audio_path = os.path.normpath(audio_path)
            output_base_name = os.path.normpath(output_base_name)

            log(">>> [Step 1] Whisper による音声認識開始...")
            segments = self.transcriber.transcribe(audio_path)
            log(f"   ✓ {len(segments)} セグメントを検出。")

            # AI による自動修正 (オプション)
            editor = self.ai_editor
            if editor and self.settings.get("ai", {}).get("auto_refine", False):
                log(">>> [Phase 1.5] AI によるテキスト自動修正中...")
                seg_dicts = [{"text": s.text} for s in segments]
                instruction = self.settings.get("ai", {}).get("refine_instruction", "自然な日本語の字幕に修正してください。")
                refined = editor.batch_refine(seg_dicts, instruction)
                for i, r in enumerate(refined):
                    segments[i].text = r.get("text", segments[i].text)
                log("   ✓ AI 修正完了。")

            csv_path = output_base_name + ".csv"
            log(f">>> [Step 2] CSV 出力 (p=923準拠): {os.path.basename(csv_path)}")
            if not self.segments_to_csv(segments, csv_path, fps):
                return None

            srt_path = output_base_name + ".srt"
            log(f">>> [Step 3] SRT 変換 (p=963準拠): {os.path.basename(srt_path)}")
            if not self.csv_to_srt(csv_path, srt_path, fps):
                return None

            return srt_path
        except Exception as e:
            print(f"[pipeline] run_full_pipeline error: {e}")
            return None
