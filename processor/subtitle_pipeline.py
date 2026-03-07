"""
processor/subtitle_pipeline.py
==============================
外部リファレンス (elosove.com p=923/963) に準拠した字幕生成パイプライン。
"""

import os
import csv
import subprocess
import threading
from typing import List, Optional, Callable, Any
from processor.base_transcriber import TranscriptSegment
from processor.adapters.whisper_transcriber import WhisperTranscriber
from processor.ai_editor import AIEditor

import ffmpeg
from utils.path_manager import get_project_root, resolve_path

class SubtitlePipeline:
    ai_editor: Optional[AIEditor]
    
    def __init__(self, settings: dict):
        self.settings = settings
        self.transcriber = WhisperTranscriber(settings)
        
        # プロジェクトルートの動的取得
        self.project_root = get_project_root()
        
        # AI Editor の初期化
        api_key = settings.get("ai", {}).get("api_key") or os.getenv("GEMINI_API_KEY")
        self.ai_editor = AIEditor(api_key=api_key) if api_key else None
        
        # FFmpeg パスの検証 (ffmpeg-python はシステムパスの ffmpeg を優先するが、
        # 必要に応じて static-ffmpeg 等で補完する)
        self.ffmpeg_path = self.validate_ffmpeg_path(settings.get("ffmpeg_path", "ffmpeg"))
        
        # 停止イベント
        self.stop_event: Optional[threading.Event] = None

    def set_stop_event(self, event: Optional[threading.Event]):
        self.stop_event = event

    def _is_stopped(self) -> bool:
        event = self.stop_event
        return event is not None and event.is_set()

    def validate_ffmpeg_path(self, path: str) -> str:
        """
        FFmpeg が利用可能か検証する。
        """
        try:
            # ffmpeg.probe を使って簡単な検証 (自分のソース自身をプローブするのは難しいため version 確認)
            subprocess.run([path, "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return path
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"[pipeline] FFmpeg not found at: {path}. Trying static-ffmpeg fallback...")
            try:
                import static_ffmpeg
                static_ffmpeg.add_paths()
                subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "ffmpeg"
            except (ImportError, subprocess.CalledProcessError):
                print("[Warning] No valid FFmpeg found.")
                return path

    def extract_audio_ffmpeg(self, video_path: str, output_wav_path: str) -> bool:
        """ 
        ffmpeg-python を使用して動画から音声を抽出する。
        仕様: 16000Hz, Mono, 16bit PCM (Whisper最適設定)
        """
        try:
            video_path = os.path.normpath(video_path)
            output_wav_path = os.path.normpath(output_wav_path)
            os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
            
            # 入力ストリーム定式化
            stream = ffmpeg.input(video_path)
            
            # 音声フィルタと出力設定
            # vn: 映像なし, ac: 1 (モノラル), ar: 16000 (16kHz), acodec: pcm_s16le
            stream = ffmpeg.output(
                stream, 
                output_wav_path, 
                vn=None, 
                ac=1, 
                ar='16000', 
                acodec='pcm_s16le'
            )
            
            # 停止イベントの監視をしつつ実行するために、別スレッドで run するか
            # あるいは ffmpeg.run はプロセスをブロッキングするため、Popen 的な挙動が必要な場合は 
            # compile -> run_async を使用する。
            
            process = ffmpeg.run_async(stream, cmd=self.ffmpeg_path, overwrite_output=True, pipe_stdout=True, pipe_stderr=True)

            while process.poll() is None:
                if self._is_stopped():
                    process.terminate()
                    process.wait()
                    print("[pipeline] FFmpeg process terminated by user.")
                    return False
                import time
                time.sleep(0.1)

            if process.returncode != 0:
                _, stderr = process.communicate()
                print(f"[pipeline] FFmpeg failed (code: {process.returncode})")
                print(f"[pipeline] Error: {stderr.decode('utf-8', 'replace')}")
                return False

            if not os.path.exists(output_wav_path) or os.path.getsize(output_wav_path) < 1024:
                return False

            return True
            
        except Exception as e:
            print(f"[pipeline] ffmpeg-python error: {e}")
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

    def run_full_pipeline(self, 
                          audio_path: str, 
                          output_base_name: str, 
                          fps: float, 
                          log_callback: Optional[Callable[[str], None]] = None,
                          progress_callback: Optional[Callable[[int], None]] = None
                          ) -> Optional[str]:
        """ 
        音声 -> CSV -> SRT の一連の流れ。
        """
        try:
            def log(msg):
                if log_callback: log_callback(msg)
                else: print(msg)
            
            def report_progress(p):
                if progress_callback: progress_callback(p)

            # パスの正規化 (Windows/Unix 共通)
            audio_path = os.path.normpath(audio_path)
            output_base_name = os.path.normpath(output_base_name)

            log(">>> [Step 1] Whisper による音声認識開始...")
            report_progress(45)
            
            if self._is_stopped(): return None
            
            # transber.transcribe にも stop_event を渡す
            segments = self.transcriber.transcribe(audio_path, stop_event=self.stop_event)
            
            if self._is_stopped() or segments is None:
                log("[pipeline] Transcription cancelled or failed.")
                return None
            
            log(f"   ✓ {len(segments)} セグメントを検出。")
            report_progress(70)

            # AI による自動修正
            editor = self.ai_editor
            if editor and self.settings.get("ai", {}).get("auto_refine", False):
                if self._is_stopped(): return None
                log(">>> [Phase 1.5] AI によるテキスト自動修正中...")
                seg_dicts = [{"text": s.text} for s in segments]
                instruction = self.settings.get("ai", {}).get("refine_instruction", "自然な日本語の字幕に修正してください。")
                refined = editor.batch_refine(seg_dicts, instruction)
                
                if self._is_stopped(): return None
                
                for i, r in enumerate(refined):
                    segments[i].text = r.get("text", segments[i].text)
                log("   ✓ AI 修正完了。")
            
            report_progress(85)
            if self._is_stopped(): return None

            csv_path = output_base_name + ".csv"
            log(f">>> [Step 2] CSV 出力 (p=923準拠): {os.path.basename(csv_path)}")
            if not self.segments_to_csv(segments, csv_path, fps):
                return None

            if self._is_stopped(): return None
            
            srt_path = output_base_name + ".srt"
            log(f">>> [Step 3] SRT 変換 (p=963準拠): {os.path.basename(srt_path)}")
            if not self.csv_to_srt(csv_path, srt_path, fps):
                return None

            report_progress(100)
            return srt_path
        except Exception as e:
            print(f"[pipeline] run_full_pipeline error: {e}")
            return None
