"""
masking.py の単体テスト
"""

import pytest
from app.core.masking import mask_sensitive_data, unmask_data, MaskingResult


class TestMaskSensitiveData:
    """マスキング処理のテスト"""

    @pytest.mark.unit
    def test_phone_number_masked(self):
        """電話番号がマスキングされること"""
        text = "電話番号は03-1234-5678です"
        result = mask_sensitive_data(text)
        assert "03-1234-5678" not in result.masked_text
        assert "[MASK_PHONE_" in result.masked_text
        assert len(result.mask_map) == 1

    @pytest.mark.unit
    def test_mobile_phone_masked(self):
        """携帯電話番号がマスキングされること"""
        text = "携帯は090-1234-5678です"
        result = mask_sensitive_data(text)
        assert "090-1234-5678" not in result.masked_text

    @pytest.mark.unit
    def test_mynumber_masked(self):
        """マイナンバーがマスキングされること"""
        text = "マイナンバー: 1234 5678 9012"
        result = mask_sensitive_data(text)
        assert "1234 5678 9012" not in result.masked_text
        assert "[MASK_MYNUMBER_" in result.masked_text

    @pytest.mark.unit
    def test_mynumber_with_hyphens(self):
        """ハイフン区切りマイナンバーがマスキングされること"""
        text = "番号: 1234-5678-9012"
        result = mask_sensitive_data(text)
        assert "1234-5678-9012" not in result.masked_text

    @pytest.mark.unit
    def test_email_masked(self):
        """メールアドレスがマスキングされること"""
        text = "連絡先: taro@test-corp.co.jp"
        result = mask_sensitive_data(text)
        assert "taro@test-corp.co.jp" not in result.masked_text
        assert "[MASK_EMAIL_" in result.masked_text

    @pytest.mark.unit
    def test_account_number_masked(self):
        """銀行口座番号がマスキングされること"""
        text = "口座番号: 1234567"
        result = mask_sensitive_data(text)
        assert "1234567" not in result.masked_text
        assert "[MASK_ACCOUNT_" in result.masked_text

    @pytest.mark.unit
    def test_multiple_items_masked(self):
        """複数の個人情報が同時にマスキングされること"""
        text = "電話03-1111-2222、メールtest@a.com、番号1234567"
        result = mask_sensitive_data(text)
        assert "03-1111-2222" not in result.masked_text
        assert "test@a.com" not in result.masked_text
        assert len(result.mask_map) >= 2

    @pytest.mark.unit
    def test_no_sensitive_data(self):
        """個人情報がないテキストは変更されないこと"""
        text = "これは普通のテキストです。特に個人情報は含みません。"
        result = mask_sensitive_data(text)
        assert result.masked_text == text
        assert len(result.mask_map) == 0

    @pytest.mark.unit
    def test_return_type(self):
        """戻り値がMaskingResult型であること"""
        result = mask_sensitive_data("テスト")
        assert isinstance(result, MaskingResult)
        assert isinstance(result.masked_text, str)
        assert isinstance(result.mask_map, dict)


class TestUnmaskData:
    """マスキング復元のテスト"""

    @pytest.mark.unit
    def test_unmask_restores_original(self):
        """マスク解除で元のテキストに復元されること"""
        original = "電話番号は03-1234-5678です"
        masked_result = mask_sensitive_data(original)
        restored = unmask_data(masked_result.masked_text, masked_result.mask_map)
        assert restored == original

    @pytest.mark.unit
    def test_unmask_multiple_items(self):
        """複数のマスク項目が正しく復元されること"""
        original = "TEL: 03-1111-2222, MAIL: a@b.com"
        masked_result = mask_sensitive_data(original)
        restored = unmask_data(masked_result.masked_text, masked_result.mask_map)
        assert restored == original

    @pytest.mark.unit
    def test_unmask_empty_map(self):
        """空のmask_mapでテキストが変更されないこと"""
        text = "変更なし"
        result = unmask_data(text, {})
        assert result == text

    @pytest.mark.unit
    def test_roundtrip_consistency(self):
        """マスキング→復元の往復で情報が失われないこと"""
        texts = [
            "TEL:03-1234-5678 FAX:03-8765-4321",
            "マイナンバー1234 5678 9012を入力",
            "account@example.com に送信、口座1234567",
        ]
        for original in texts:
            masked = mask_sensitive_data(original)
            restored = unmask_data(masked.masked_text, masked.mask_map)
            assert restored == original, f"Failed for: {original}"


class TestMaskMapConsistency:
    """マスキングマップの整合性テスト"""

    @pytest.mark.unit
    def test_mask_map_keys_in_text(self):
        """mask_mapのキーがすべてmasked_textに存在すること"""
        text = "TEL: 03-1234-5678, MAIL: test@example.com"
        result = mask_sensitive_data(text)
        for key in result.mask_map:
            assert key in result.masked_text

    @pytest.mark.unit
    def test_mask_map_values_not_in_text(self):
        """mask_mapの値（元データ）がmasked_textに存在しないこと"""
        text = "TEL: 03-1234-5678"
        result = mask_sensitive_data(text)
        for value in result.mask_map.values():
            assert value not in result.masked_text

    @pytest.mark.unit
    def test_unique_mask_keys(self):
        """同じカテゴリの複数マスクに異なる連番が付くこと"""
        text = "TEL1: 03-1111-1111 TEL2: 03-2222-2222 TEL3: 03-3333-3333"
        result = mask_sensitive_data(text)
        keys = list(result.mask_map.keys())
        assert len(keys) == len(set(keys))  # 重複なし
