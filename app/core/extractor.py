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

# Vertex AIは初回呼び出し時に遅延初期化する（テスト容易性のため）
_vertexai_initialized = False


def _ensure_vertexai_initialized():
    """初回のextract_data呼び出し時にVertex AIを初期化する"""
    global _vertexai_initialized
    if not _vertexai_initialized and settings.GCP_PROJECT_ID:
        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        _vertexai_initialized = True


SYSTEM_PROMPT = """
あなたはデータ抽出の専門家です。
与えられたテキストから、指定された項目を正確に抽出してください。

## ルール
1. 出力は必ずJSON形式とすること
2. 値が見つからない場合はnullとすること
3. 日付は "YYYY-MM-DD" 形式に統一すること
4. 金額は数値型（整数）とし、カンマや円記号を含めないこと
5. JSON以外のテキスト（説明文等）を出力に含めないこと
6. JSONのキー名は、後続の指示に従うこと（後続の指示がキー名を指定している場合は、それを優先すること）
"""


class ExtractionResult:
    def __init__(self, data: dict, is_fallback: bool = False, retry_count: int = 0):
        self.data = data
        self.is_fallback = is_fallback
        self.retry_count = retry_count


def build_extraction_prompt(
    source_text: str,
    mapping_config: Optional[dict] = None,
    template_text: Optional[str] = None,
) -> str:
    """
    Geminiに送信するプロンプトを組み立てる。
    """
    prompt = f"{SYSTEM_PROMPT}\n\n対象テキスト:\n{source_text}\n\n"

    if template_text:
        prompt += f"## エクセルテンプレートの構造\n{template_text}\n\n"
        prompt += "指示: 上記のテンプレート構造を確認し、ソーステキストから抽出したデータを「どのセルに書き込むべきか」を論理的に判断してください。\n"
        prompt += "判定ルール（重要）:\n"
        prompt += (
            "1. 既に文字が入っているセル（ラベル）は絶対に上書きしないでください。\n"
        )
        prompt += "2. 必ずラベルの右側や下側にある '(empty)' となっているセルを選択してください。\n"
        prompt += "3. 結合セル（Merged Cells）の場合、その範囲内のいずれかの番地を指定してください。ただし、その結合範囲のマスターセルに既にラベルが入っている場合は、その隣の空いている範囲を探してください。\n"
        prompt += "4. 明細行（テーブル）の場合、ヘッダ行（No, 品名など）のすぐ下の行の '(empty)' セルから順に埋めてください。ソーステキストに複数の明細がある場合は、すべて抽出して連続する行に配置してください。\n"
        prompt += "5. 金額や合計（金額、小計、合計など）の項目がソーステキストに欠けているが、テンプレートにそれらを書く場所がある場合、抽出した数量と単価から計算して求めてください。\n"
        prompt += "6. 単位（個、本、式など）が不明な場合は、文脈から推測するか、空欄にしてください。\n"
        prompt += "\n出力は以下のJSON形式とします。このモードでは、ルール5（キーは日本語）を無視し、キーを 'シート名:セル番地' としてください:\n"
        prompt += '{\n  "SheetName:C7": 1045000,\n  "SheetName:F4": "2026-04-30"\n}\n'
    elif mapping_config:
        prompt += "以下の項目を抽出し、指定された形式で出力してください:\n"
        prompt += "{\n"

        # mapping_configの構造に応じて対応
        # dict形式 (プレースホルダー自動判定) または mappingsリスト形式 (マッピング設定)
        keys_to_extract = []
        if "mappings" in mapping_config:
            keys_to_extract = [
                m.get("key") for m in mapping_config["mappings"] if m.get("key")
            ]
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
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSONパースエラー: {e}")


async def extract_data(
    source_text: str,
    mapping_config: Optional[dict] = None,
    template_text: Optional[str] = None,
    max_retries: int = 2,
) -> ExtractionResult:
    """
    Gemini APIを呼び出してデータ抽出を実行する。
    """
    # 初回呼び出し時にVertex AIを初期化
    _ensure_vertexai_initialized()

    model = GenerativeModel(settings.GEMINI_MODEL)
    config = GenerationConfig(temperature=0.0)

    base_prompt = build_extraction_prompt(source_text, mapping_config, template_text)
    current_prompt = base_prompt

    for attempt in range(max_retries + 1):
        try:
            # タイムアウトを設定して非同期呼び出し
            response = await asyncio.wait_for(
                model.generate_content_async(current_prompt, generation_config=config),
                timeout=settings.GEMINI_TIMEOUT_SECONDS,
            )

            result_json = _parse_llm_response(response.text)
            return ExtractionResult(
                data=result_json, is_fallback=False, retry_count=attempt
            )

        except asyncio.TimeoutError:
            raise AppException(
                ErrorCode.TIMEOUT, "Gemini APIの呼び出しがタイムアウトしました"
            )
        except ValueError as e:
            if attempt < max_retries:
                current_prompt = (
                    base_prompt
                    + f"\n\n※前回の出力はJSONとしてパースできませんでした。正しいJSON形式のみを出力してください。\n前回のエラー: {e}"
                )
                continue
            else:
                raise AppException(
                    ErrorCode.EXTRACTION_FAILED,
                    f"データ抽出に失敗しました: 最大リトライ回数超過 ({e})",
                )
        except Exception as e:
            if isinstance(e, AppException):
                raise e
            raise AppException(
                ErrorCode.EXTRACTION_FAILED, f"Gemini API通信エラー: {str(e)}"
            )

    raise AppException(
        ErrorCode.EXTRACTION_FAILED, "データ抽出に失敗しました: 不明なエラー"
    )
