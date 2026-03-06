"""
processor/ai_editor.py
======================
Gemini API を使用した字幕テキストの AI 編集ロジック。
"""

import os
import json
import google.generativeai as genai
from typing import List, Dict, Optional, Any

# 字幕セグメントの型定義 (辞書形式)
SegmentList = List[Dict[str, Any]]

class AIEditor:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash") -> None:
        self.api_key: Optional[str] = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def refine_segment(self, 
                       text: str, 
                       instruction: str, 
                       context_before: str = "", 
                       context_after: str = "") -> str:
        """
        特定のセグメントをユーザーの指示に基づいて修正する。
        """
        if not self.api_key:
            return text

        prompt = f"""
あなたはプロの動画字幕エディターです。
以下の字幕セグメントを、ユーザーの指示に従って修正してください。

【文脈（前）】: {context_before}
【修正対象】: {text}
【文脈（後）】: {context_after}

【ユーザーの指示】: {instruction}

【制約事項】:
- 字幕としての自然な流れを重視してください。
- 意味を大きく変えず、表現をリファインしてください。
- 修正後のテキストのみを出力してください。余計な解説や引用符、接頭辞は不要です。
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[AIEditor] Error refining segment: {e}")
            return text

    def batch_refine(self, 
                     segments: SegmentList, 
                     global_instruction: str,
                     chunk_size: int = 50,
                     context_overlap: int = 3) -> SegmentList:
        """
        全セグメントをチャンク分割して修正する。
        チャンク間での文脈（口調等）を維持するため、前のチャンクの末尾をコンテキストに含める。
        """
        if not self.api_key or not segments:
            return segments

        all_refined_texts = []
        
        # チャンクごとにループ
        for i in range(0, len(segments), chunk_size):
            chunk = segments[i : i + chunk_size]
            
            # コンテキスト（前のチャンクの末尾数件）の取得
            context_segments = []
            if i > 0:
                context_start = max(0, i - context_overlap)
                context_segments = [s.get("speech 2 txt", s.get("text", "")) for s in segments[context_start:i]]
            
            context_text = "\n".join(context_segments)
            current_texts = [s.get("speech 2 txt", s.get("text", "")) for s in chunk]
            json_input = json.dumps(current_texts, ensure_ascii=False)

            prompt = f"""
あなたはプロの動画字幕エディターです。
以下の字幕リストを、ユーザーの一括指示に従って修正してください。

【前後の文脈（参照用）】:
{context_text}
（※この参照用セグメント自体は修正不要です。続くリストの口調や文脈を合わせるために使用してください）

【ユーザーの一括指示】: {global_instruction}

【入力データ (JSON)】:
{json_input}

【制約事項】:
- 全体のトーン（敬語、口調など）を、参照用テキストがある場合はそれに合わせ、一貫させてください。
- JSON配列の形式（["テキスト1", "テキスト2", ...]）で、入力と同じ順序・同じ要素数で返してください。
- 修正後のJSONデータのみを出力してください。
"""
            try:
                response = self.model.generate_content(prompt)
                res_text = response.text.strip()
                
                # JSON 抽出
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0].strip()
                
                refined_chunk = json.loads(res_text)
                
                if len(refined_chunk) == len(chunk):
                    all_refined_texts.extend(refined_chunk)
                else:
                    # 要素数が合わない場合はフォールバック
                    print(f"[AIEditor] Chunk {i//chunk_size} length mismatch. Using original.")
                    all_refined_texts.extend(current_texts)
            except Exception as e:
                # チャンク単位でのエラーハンドリング：このチャンクはスキップ（元のテキストを使用）
                print(f"[AIEditor] Error in chunk {i//chunk_size}: {e}")
                all_refined_texts.extend(current_texts)

        # 全体の結果をセグメントに適用
        if len(all_refined_texts) == len(segments):
            for i in range(len(all_refined_texts)):
                new_text = all_refined_texts[i]
                target = segments[i]
                if "speech 2 txt" in target:
                    target["speech 2 txt"] = new_text
                else:
                    target["text"] = new_text
        
        return segments
