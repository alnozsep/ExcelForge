import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import io
import json

from app.main import app
from app.config import settings
from app.core.extractor import ExtractionResult

client = TestClient(app)


@pytest.fixture
def auth_token():
    # テスト用のトークンをセットアップ
    token = "test_token_123"
    settings.VALID_TOKENS[token] = "テスト顧客"
    yield token
    # クリーンアップ
    if token in settings.VALID_TOKENS:
        del settings.VALID_TOKENS[token]


@pytest.fixture
def mock_dependencies():
    with (
        patch(
            "app.api.endpoints.process.extract_data", new_callable=AsyncMock
        ) as mock_extract,
        patch("app.api.endpoints.process.write_to_template") as mock_write,
    ):
        mock_extract.return_value = ExtractionResult(
            data={"テスト": "データ"}, is_fallback=False, retry_count=0
        )

        buf = io.BytesIO(b"dummy excel data")
        buf.seek(0)
        mock_write.return_value = buf

        yield mock_extract, mock_write


def test_successful_processing(
    auth_token, mock_dependencies, sample_pdf_bytes, sample_xlsx_bytes
):
    """正常な入力でExcelが返却されること"""
    mock_extract, mock_write = mock_dependencies

    files = {
        "source_file": ("test.pdf", sample_pdf_bytes, "application/pdf"),
        "template_file": (
            "template.xlsx",
            sample_xlsx_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }
    data = {"token": auth_token}

    response = client.post("/api/v1/process", files=files, data=data)

    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.content == b"dummy excel data"
    assert mock_extract.called
    assert mock_write.called


def test_invalid_token_returns_403(sample_pdf_bytes, sample_xlsx_bytes):
    """無効なトークンで403が返却されること"""
    files = {
        "source_file": ("test.pdf", sample_pdf_bytes, "application/pdf"),
        "template_file": (
            "template.xlsx",
            sample_xlsx_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }
    data = {"token": "invalid_token_999"}

    response = client.post("/api/v1/process", files=files, data=data)
    assert response.status_code == 403
    assert response.json()["detail"] == "無効なアクセストークンです"


def test_invalid_file_type_returns_400(auth_token, sample_xlsx_bytes):
    """非対応ファイルで400が返却されること"""
    files = {
        "source_file": (
            "test.txt",
            b"dummy text file content just to be sure it is not pdf",
            "text/plain",
        ),
        "template_file": (
            "template.xlsx",
            sample_xlsx_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }
    data = {"token": auth_token}

    response = client.post("/api/v1/process", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_FILE_TYPE"


def test_oversized_file_returns_413(auth_token, sample_pdf_bytes, sample_xlsx_bytes):
    """サイズ超過で413が返却されること"""
    # 実際にはUploadFileのsizeプロパティに依存するため、
    # 10MB以上のダミーデータを作成するか、設定を一時的に小さくする
    original_max_size = settings.MAX_UPLOAD_SIZE_MB
    settings.MAX_UPLOAD_SIZE_MB = 0  # 0MBに制限

    try:
        files = {
            "source_file": ("test.pdf", sample_pdf_bytes, "application/pdf"),
            "template_file": (
                "template.xlsx",
                sample_xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        }
        data = {"token": auth_token}

        response = client.post("/api/v1/process", files=files, data=data)
        assert response.status_code == 413
        assert response.json()["error_code"] == "FILE_TOO_LARGE"
    finally:
        settings.MAX_UPLOAD_SIZE_MB = original_max_size


def test_receipt_header_present(
    auth_token, mock_dependencies, sample_pdf_bytes, sample_xlsx_bytes
):
    """レスポンスにX-ExcelForge-Receiptヘッダが含まれること"""
    files = {
        "source_file": ("test.pdf", sample_pdf_bytes, "application/pdf"),
        "template_file": (
            "template.xlsx",
            sample_xlsx_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }
    data = {"token": auth_token}

    response = client.post("/api/v1/process", files=files, data=data)

    assert response.status_code == 200
    assert "X-ExcelForge-Receipt" in response.headers

    receipt_json = response.headers["X-ExcelForge-Receipt"]
    receipt_data = json.loads(receipt_json)

    assert "receipt_id" in receipt_data
    assert receipt_data["data_retention"] == "none"
