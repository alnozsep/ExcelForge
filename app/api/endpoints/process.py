"""
app/api/endpoints/process.py

メインのファイル処理エンドポイント。
このファイルが全体の処理フローを制御する。
"""

import gc
import time
import hashlib
import json
import os
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from app.api.middleware.token_auth import verify_token
from app.core.file_reader import read_file, detect_file_type
from app.core.extractor import extract_data
from app.core.excel_writer import write_to_template
from app.core.masking import mask_sensitive_data, unmask_data
from app.utils.receipt_generator import generate_receipt
from app.utils.cleanup import cleanup_variables
from app.api.endpoints.receipt import store_receipt
from app.config import settings
from app.models.enums import ErrorCode, AppException

router = APIRouter()


def _validate_file(upload_file: UploadFile, allowed_extensions: list[str]):
    """ファイルの拡張子とサイズを検証する"""
    ext = os.path.splitext(upload_file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise AppException(
            error_code=ErrorCode.INVALID_FILE_TYPE,
            message=f"無効なファイル形式です。許可されている形式: {', '.join(allowed_extensions)}",
            status_code=400,
        )

    if getattr(upload_file, "size", 0) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise AppException(
            error_code=ErrorCode.FILE_TOO_LARGE,
            message=f"ファイルサイズが上限({settings.MAX_UPLOAD_SIZE_MB}MB)を超えています",
            status_code=413,
        )


def _unmask_extracted_data(extracted_data: dict, mask_map: dict) -> dict:
    """抽出データの各値に対してunmaskを適用する"""
    unmasked = {}
    for k, v in extracted_data.items():
        if isinstance(v, str):
            unmasked[k] = unmask_data(v, mask_map)
        else:
            unmasked[k] = v
    return unmasked


@router.post("/process")
async def process_files(
    source_file: UploadFile = File(...),
    template_file: UploadFile = File(...),
    token: str = Form(...),
    mapping_config: str = Form(None),
):
    """
    処理手順（設計書 5.1節 Step6〜Step15 に完全準拠）:

    この関数内で宣言されるすべての変数は、
    finally ブロックで明示的に削除される。
    """
    # 変数を事前宣言（finallyでの削除を確実にするため）
    source_bytes = None
    template_bytes = None
    source_text = None
    masking_result = None
    extracted_data = None
    unmasked_data = None
    output_buffer = None
    receipt = None

    try:
        start_time = time.monotonic()

        # Step 6: トークン検証
        _ = verify_token(token)

        # Step 7: バリデーション
        _validate_file(source_file, settings.ALLOWED_SOURCE_EXTENSIONS)
        _validate_file(template_file, settings.ALLOWED_TEMPLATE_EXTENSIONS)

        # Step 8: ファイル読み込み
        source_bytes = await source_file.read()
        template_bytes = await template_file.read()

        # 読み込み後のサイズ再検証（フォールバック）
        if len(source_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise AppException(
                error_code=ErrorCode.FILE_TOO_LARGE,
                message=f"ファイルサイズが上限({settings.MAX_UPLOAD_SIZE_MB}MB)を超えています",
                status_code=413,
            )
        if len(template_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise AppException(
                error_code=ErrorCode.FILE_TOO_LARGE,
                message=f"テンプレートファイルサイズが上限({settings.MAX_UPLOAD_SIZE_MB}MB)を超えています",
                status_code=413,
            )

        file_type = detect_file_type(source_file.filename)
        source_text = read_file(source_bytes, file_type)

        # Step 9: マスキング（個人情報保護: Gemini APIに送る前に必ず通す）
        masking_result = mask_sensitive_data(source_text)

        # Step 10: AI抽出（マスキング済みテキストを送信）
        parsed_mapping = json.loads(mapping_config) if mapping_config else None
        extraction_result = await extract_data(
            masking_result.masked_text, parsed_mapping
        )
        extracted_data = extraction_result.data

        # Step 11: マスキング復元（抽出データの各値を復元）
        unmasked_data = _unmask_extracted_data(extracted_data, masking_result.mask_map)

        # Step 12: Excel書き込み（メモリ上で完結、ファイルシステムに書き込まない）
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

        # レシートをメモリキャッシュに保存（GET /api/v1/receipt/{id} で取得可能に）
        store_receipt(receipt)

        # Step 14: レスポンス返却
        output_buffer.seek(0)

        def iter_and_close(buf):
            try:
                yield from buf
            finally:
                buf.close()

        return StreamingResponse(
            iter_and_close(output_buffer),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="excelforge_output.xlsx"',
                "X-ExcelForge-Receipt": receipt.model_dump_json(),
            },
        )

    finally:
        # Step 15: 明示的クリーンアップ（メモリ解放）
        # output_buffer はジェネレータ内でcloseするためここから除外
        cleanup_variables(
            source_bytes,
            template_bytes,
            source_text,
            masking_result,
            extracted_data,
            unmasked_data,
            receipt,
        )
        gc.collect()
