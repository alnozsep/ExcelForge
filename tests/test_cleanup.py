"""
cleanup.py の単体テスト
"""

import io

import pytest
from app.utils.cleanup import cleanup_variables


class TestCleanupVariables:
    """メモリクリーンアップのテスト"""

    @pytest.mark.unit
    def test_dict_cleared(self):
        """dictがclear()されること"""
        d = {"key": "sensitive_value", "key2": "data"}
        cleanup_variables(d)
        assert len(d) == 0

    @pytest.mark.unit
    def test_list_cleared(self):
        """listがclear()されること"""
        lst = [1, 2, 3, "sensitive"]
        cleanup_variables(lst)
        assert len(lst) == 0

    @pytest.mark.unit
    def test_bytesio_closed(self):
        """BytesIOがclose()されること"""
        buf = io.BytesIO(b"sensitive data")
        cleanup_variables(buf)
        assert buf.closed

    @pytest.mark.unit
    def test_none_input_no_error(self):
        """None入力でエラーが発生しないこと"""
        cleanup_variables(None)
        cleanup_variables(None, None, None)

    @pytest.mark.unit
    def test_mixed_types(self):
        """異なる型の変数が混在しても正常にクリーンアップされること"""
        d = {"key": "value"}
        lst = [1, 2, 3]
        buf = io.BytesIO(b"data")

        cleanup_variables(d, lst, buf, None, "string_value", 12345)

        assert len(d) == 0
        assert len(lst) == 0
        assert buf.closed

    @pytest.mark.unit
    def test_already_closed_bytesio(self):
        """既にcloseされたBytesIOでエラーが発生しないこと"""
        buf = io.BytesIO(b"data")
        buf.close()
        cleanup_variables(buf)  # 二重closeでエラーにならない

    @pytest.mark.unit
    def test_empty_dict(self):
        """空dictでエラーが発生しないこと"""
        cleanup_variables({})

    @pytest.mark.unit
    def test_bytes_input(self):
        """bytes型入力でエラーが発生しないこと"""
        data = b"sensitive bytes data"
        cleanup_variables(data)
