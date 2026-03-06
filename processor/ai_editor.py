"""
processor/ai_editor.py
======================
Gemini API を使用した字幕テキストの AI 編集ロジック。
"""

import os
import json
import google.generativeai as genai
from typing import List, Dict, Optional, Any

class AIEditor:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
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
                     segments: List[Dict[str, Any]], 
                     global_instruction: str) -> List[Dict[str, Any]]:
        """
        全セグメントを一括で修正する。
        """
        if not self.api_key:
            return segments

        # セグメントをテキストのリストとして抽出
        texts = [s.get("speech 2 txt", s.get("text", "")) for s in segments]
        json_input = json.dumps(texts, ensure_ascii=False)

        prompt = f"""
あなたはプロの動画字幕エディターです。
以下の字幕リスト全体を、ユーザーの一括指示に従って修正してください。

【ユーザーの一括指示】: {global_instruction}

【入力データ (JSON)】:
{json_input}

【制約事項】:
- 全体のトーン（敬語、口調など）を統一してください。
- JSON配列の形式（["テキスト1", "テキスト2", ...]）で、入力と同じ順序・同じ要素数で返してください。
- 修正後のJSONデータのみを出力してください。
"""
        try:
            response = self.model.generate_content(prompt)
            # JSON 抽出ロジック（マークダウンの除去など）
            res_text = response.text.strip()
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                res_text = res_text.split("```")[1].split("```")[0].strip()
            
            refined_texts = json.loads(res_text)
            
            if len(refined_texts) == len(segments):
                for i, new_text in enumerate(refined_texts):
                    if "speech 2 txt" in segments[i]:
                        segments[i]["speech 2 txt"] = new_text
                    else:
                        segments[i]["text"] = new_text
            
            return segments
        except Exception as e:
            print(f"[AIEditor] Error in batch refine: {e}")
            return segments
