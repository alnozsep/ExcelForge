"""
file_reader.py の単体テスト
"""

import pytest
from app.core.file_reader import read_file, detect_file_type, FileType
from app.models.enums import FileReadError


class TestDetectFileType:
    """ファイルタイプ判定のテスト"""

    @pytest.mark.unit
    @pytest.mark.parametrize("filename,expected", [
        ("document.pdf", FileType.PDF),
        ("data.csv", FileType.CSV),
        ("sheet.xlsx", FileType.XLSX),
        ("old_sheet.xls", FileType.XLS),
        ("DOCUMENT.PDF", FileType.PDF),  # 大文字
        ("my.data.file.csv", FileType.CSV),  # 複数ドット
    ])
    def test_valid_extensions(self, filename: str, expected: FileType):
        """対応拡張子が正しくFileTypeに変換されること"""
        assert detect_file_type(filename) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize("filename", [
        "document.docx",
        "image.png",
        "archive.zip",
        "noextension",
        "",
    ])
    def test_invalid_extensions(self, filename: str):
        """非対応拡張子でValueErrorが発生すること"""
        with pytest.raises(ValueError):
            detect_file_type(filename)


class TestReadPDF:
    """PDF読み込みのテスト"""

    @pytest.mark.unit
    def test_text_extraction(self, sample_pdf_bytes):
        """PDFからテキストが抽出されること"""
        result = read_file(sample_pdf_bytes, FileType.PDF)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Test Corporation" in result

    @pytest.mark.unit
    def test_multipage_extraction(self, sample_pdf_bytes):
        """複数ページのPDFから全ページのテキストが抽出されること"""
        result = read_file(sample_pdf_bytes, FileType.PDF)
        assert "Page" in result or "Test Corporation" in result
        assert "DX Promotion Project" in result  # Page 2の内容

    @pytest.mark.unit
    def test_empty_pdf_raises_error(self, empty_pdf_bytes):
        """テキストなしPDFでFileReadErrorが発生すること"""
        with pytest.raises(FileReadError):
            read_file(empty_pdf_bytes, FileType.PDF)

    @pytest.mark.unit
    def test_corrupted_pdf_raises_error(self, corrupted_pdf_bytes):
        """破損PDFでFileReadErrorが発生すること"""
        with pytest.raises(FileReadError):
            read_file(corrupted_pdf_bytes, FileType.PDF)


class TestReadCSV:
    """CSV読み込みのテスト"""

    @pytest.mark.unit
    def test_utf8_reading(self, sample_csv_bytes):
        """UTF-8 CSVが正しく読み込まれること"""
        result = read_file(sample_csv_bytes, FileType.CSV)
        assert isinstance(result, str)
        assert "株式会社テスト" in result
        assert "山田太郎" in result

    @pytest.mark.unit
    def test_shiftjis_fallback(self, sample_csv_sjis_bytes):
        """Shift_JIS CSVがフォールバックで読み込まれること"""
        result = read_file(sample_csv_sjis_bytes, FileType.CSV)
        assert isinstance(result, str)
        assert "株式会社テスト" in result

    @pytest.mark.unit
    def test_empty_csv_raises_error(self):
        """空CSVでFileReadErrorが発生すること"""
        with pytest.raises(FileReadError):
            read_file(b"", FileType.CSV)


class TestReadExcel:
    """Excel読み込みのテスト"""

    @pytest.mark.unit
    def test_xlsx_reading(self, sample_xlsx_bytes):
        """Excelファイルのセル値が読み取られること"""
        result = read_file(sample_xlsx_bytes, FileType.XLSX)
        assert isinstance(result, str)
        assert "株式会社テスト" in result
        assert "1500000" in result

    @pytest.mark.unit
    def test_merged_cells_handling(self, sample_xlsx_bytes):
        """セル結合されたExcelで値が読み取られること"""
        result = read_file(sample_xlsx_bytes, FileType.XLSX)
        assert "補助金申請データ" in result  # 結合セルA1の値

    @pytest.mark.unit
    def test_corrupted_xlsx_raises_error(self):
        """破損Excelファイルでエラーが発生すること"""
        with pytest.raises(FileReadError):
            read_file(b"not an excel file", FileType.XLSX)
