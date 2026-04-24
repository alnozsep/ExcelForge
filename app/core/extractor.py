"""
app/core/extractor.py

責務: Gemini APIにテキストを送信し、構造化されたJSONデータを受け取る。
"""

import json
import re
import asyncio
from typing import Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from app.config import settings
from app.models.enums import AppException, ErrorCode

# モジュール初期化時にVertex AIを初期化
if settings.GCP_PROJECT_ID:
    vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)

SYSTEM_PROMPT = """
あなたはデータ抽出の専門家です。
与えられたテキストから、指定された項目を正確に抽出してください。

## ルール
1. 出力は必ずJSON形式とすること
2. 値が見つからない場合はnullとすること
3. 日付は "YYYY-MM-DD" 形式に統一すること
4. 金額は数値型（整数）とし、カンマや円記号を含めないこと
5. JSONのキーは日本語とすること
6. JSON以外のテキスト（説明文等）を出力に含めないこと
"""

class ExtractionResult:
    def __init__(self, data: dict, is_fallback: bool = False, retry_count: int = 0):
        self.data = data
        self.is_fallback = is_fallback
        self.retry_count = retry_count

def build_extraction_prompt(source_text: str, mapping_config: Optional[dict] = None) -> str:
    """
    Geminiに送信するプロンプトを組み立てる。
    """
    prompt = f"{SYSTEM_PROMPT}\n\n対象テキスト:\n{source_text}\n\n"
    
    if mapping_config:
        prompt += "以下の項目を抽出し、指定された形式で出力してください:\n"
        prompt += "{\n"
        
        # mapping_configの構造に応じて対応
        # dict形式 (プレースホルダー自動判定) または mappingsリスト形式 (マッピング設定)
        keys_to_extract = []
        if "mappings" in mapping_config:
            keys_to_extract = [m.get("key") for m in mapping_config["mappings"] if m.get("key")]
        else:
            keys_to_extract = list(mapping_config.keys())
            
        for key in keys_to_extract:
            prompt += f'  "{key}": "適切な値",\n'
        prompt += "}\n"
    else:
        prompt += "このテキストに含まれるすべての項目をキー・バリュー形式のJSONで出力してください。\n"
        
    return prompt

def _parse_llm_response(response_text: str) -> dict:
    """
    LLMのレスポンスからJSONを抽出してパースする。
    """
    text = response_text.strip()
    
    # マークダウンのコードブロックで囲まれている場合を処理
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
        
    # JSON以外の文字が前後に付着しているケースに対応するため、最初と最後の波括弧を探す
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end >= start:
        text = text[start:end+1]
        
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSONパースエラー: {e}")

async def extract_data(source_text: str, mapping_config: Optional[dict] = None, max_retries: int = 2) -> ExtractionResult:
    """
    Gemini APIを呼び出してデータ抽出を実行する。
    """
    model = GenerativeModel("gemini-1.5-pro-preview-0409")
    config = GenerationConfig(temperature=0.0)
    
    base_prompt = build_extraction_prompt(source_text, mapping_config)
    current_prompt = base_prompt
    
    for attempt in range(max_retries + 1):
        try:
            # タイムアウトを設定して非同期呼び出し
            response = await asyncio.wait_for(
                model.generate_content_async(current_prompt, generation_config=config),
                timeout=settings.GEMINI_TIMEOUT_SECONDS
            )
            
            result_json = _parse_llm_response(response.text)
            return ExtractionResult(data=result_json, is_fallback=False, retry_count=attempt)
            
        except asyncio.TimeoutError:
            raise AppException(ErrorCode.TIMEOUT, "Gemini APIの呼び出しがタイムアウトしました")
        except ValueError as e:
            if attempt < max_retries:
                current_prompt = base_prompt + f"\n\n※前回の出力はJSONとしてパースできませんでした。正しいJSON形式のみを出力してください。\n前回のエラー: {e}"
                continue
            else:
                raise AppException(ErrorCode.EXTRACTION_FAILED, f"データ抽出に失敗しました: 最大リトライ回数超過 ({e})")
        except Exception as e:
            if isinstance(e, AppException):
                raise e
            raise AppException(ErrorCode.EXTRACTION_FAILED, f"Gemini API通信エラー: {str(e)}")
            
    raise AppException(ErrorCode.EXTRACTION_FAILED, "データ抽出に失敗しました: 不明なエラー")
