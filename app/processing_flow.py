"""
app/processing_flow.py

責務: ファイルアップロード処理のコアロジックを1つの関数に集約する。
      これによりFastAPIエンドポイントとStreamlitの両方から同じロジックを
      直接呼び出せるようになり、FastAPIプロセスを分離する必要がなくなる。
"""

import gc
import time
import hashlib
import json
import io
from typing import Optional

from app.core.file_reader import read_file, detect_file_type, FileType
from app.core.extractor import extract_data
from app.core.excel_writer import write_to_template
from app.core.masking import mask_sensitive_data, unmask_data
from app.utils.receipt_generator import generate_receipt
from app.utils.cleanup import cleanup_variables


async def run_processing(
    source_bytes: bytes,
    template_bytes: bytes,
    source_filename: str,
    mapping_config: Optional[str] = None,
    processing_mode: str = "auto",
) -> tuple[io.BytesIO, dict]:
    """
    ファイル処理の全フローを実行する。

    Args:
        source_bytes: ソースファイルのバイナリ
        template_bytes: テンプレートファイルのバイナリ
        source_filename: ソースファイル名（拡張子判定に使用）
        mapping_config: マッピング設定JSON文字列（任意）
        processing_mode: 処理モード（"auto" / "placeholder" / "manual"）

    Returns:
        (output_buffer: BytesIO, receipt_data: dict) のタプル
    """
    source_text = None
    masking_result = None
    extracted_data = None
    unmasked_data = None
    output_buffer = None
    template_text = None

    try:
        start_time = time.monotonic()

        # Step 8: ファイル読み込み
        file_type = detect_file_type(source_filename)
        source_text = read_file(source_bytes, file_type)

        # Step 9: マスキング
        masking_result = mask_sensitive_data(source_text)

        # Step 10: AI抽出
        parsed_mapping = json.loads(mapping_config) if mapping_config else None

        if processing_mode == "auto" and not parsed_mapping:
            template_text = read_file(template_bytes, FileType.XLSX)

        extraction_result = await extract_data(
            masking_result.masked_text, parsed_mapping, template_text
        )
        extracted_data = extraction_result.data

        # Step 11: マスキング復元
        unmasked_data = _unmask_extracted_data(extracted_data, masking_result.mask_map)

        # Step 12: Excel書き込み
        output_buffer = write_to_template(template_bytes, unmasked_data, parsed_mapping)

        # Step 13: レシート生成
        processing_time = time.monotonic() - start_time
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        template_hash = hashlib.sha256(template_bytes).hexdigest()
        receipt = generate_receipt(
            source_hash=source_hash,
            template_hash=template_hash,
            source_type=file_type.value,
            source_size=len(source_bytes),
            processing_time=processing_time,
        )

        output_buffer.seek(0)
        return output_buffer, receipt.model_dump()

    finally:
        cleanup_variables(
            source_bytes,
            template_bytes,
            source_text,
            masking_result,
            extracted_data,
            unmasked_data,
            template_text,
        )
        gc.collect()


def _unmask_extracted_data(extracted_data: dict, mask_map: dict) -> dict:
    """抽出データの各値に対してunmaskを適用する"""
    unmasked = {}
    for k, v in extracted_data.items():
        if isinstance(v, str):
            unmasked[k] = unmask_data(v, mask_map)
        else:
            unmasked[k] = v
    return unmasked
