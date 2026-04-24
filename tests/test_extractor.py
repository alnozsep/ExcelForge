import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.core.extractor import extract_data
from app.models.enums import AppException, ErrorCode


# モック用のVertex AIレスポンス
class MockResponse:
    def __init__(self, text):
        self.text = text


@pytest.fixture
def mock_vertex_model():
    with patch("app.core.extractor.GenerativeModel") as MockModel:
        model_instance = MockModel.return_value
        yield model_instance


@pytest.mark.asyncio
async def test_successful_extraction(mock_vertex_model):
    """正常なテキストからJSONが抽出されること"""
    mock_vertex_model.generate_content_async = AsyncMock(
        return_value=MockResponse('{"会社名": "株式会社テスト"}')
    )

    result = await extract_data("株式会社テスト")
    assert result.data == {"会社名": "株式会社テスト"}
    assert result.is_fallback is False
    assert result.retry_count == 0


@pytest.mark.asyncio
async def test_extraction_with_mapping_config(mock_vertex_model):
    """mapping_config指定時に指定項目のみ抽出されること"""
    mock_vertex_model.generate_content_async = AsyncMock(
        return_value=MockResponse('{"代表者名": "山田太郎"}')
    )

    mapping_config = {"代表者名": "A1"}
    result = await extract_data("山田太郎", mapping_config)
    assert result.data == {"代表者名": "山田太郎"}

    # 呼び出された引数にmapping_configのキーが含まれているか確認
    call_args = mock_vertex_model.generate_content_async.call_args[0][0]
    assert "代表者名" in call_args


@pytest.mark.asyncio
async def test_retry_on_json_parse_failure(mock_vertex_model):
    """JSON parse失敗時にリトライされること"""
    # 1回目: 不正なJSON, 2回目: 正常なJSON
    mock_vertex_model.generate_content_async = AsyncMock(
        side_effect=[
            MockResponse("これはJSONではありません"),
            MockResponse('{"会社名": "株式会社テスト"}'),
        ]
    )

    result = await extract_data("テキスト")
    assert result.data == {"会社名": "株式会社テスト"}
    assert result.retry_count == 1


@pytest.mark.asyncio
async def test_max_retry_exceeded_raises_error(mock_vertex_model):
    """リトライ上限超過でExtractionError(AppException)が送出されること"""
    mock_vertex_model.generate_content_async = AsyncMock(
        return_value=MockResponse("不正なJSON文字列")
    )

    with pytest.raises(AppException) as excinfo:
        await extract_data("テキスト")

    assert excinfo.value.error_code == ErrorCode.EXTRACTION_FAILED
    assert (
        mock_vertex_model.generate_content_async.call_count == 3
    )  # 初回 + リトライ2回


@pytest.mark.asyncio
async def test_timeout_raises_error(mock_vertex_model):
    """タイムアウト時にTimeoutErrorが送出されること"""
    mock_vertex_model.generate_content_async = AsyncMock(
        side_effect=asyncio.TimeoutError()
    )

    with pytest.raises(AppException) as excinfo:
        await extract_data("テキスト")

    assert excinfo.value.error_code == ErrorCode.TIMEOUT


@pytest.mark.asyncio
async def test_json_wrapped_in_code_block(mock_vertex_model):
    """```json...```で囲まれたレスポンスが正しくparseされること"""
    mock_vertex_model.generate_content_async = AsyncMock(
        return_value=MockResponse('```json\n{"会社名": "テスト"}\n```')
    )

    result = await extract_data("テキスト")
    assert result.data == {"会社名": "テスト"}
