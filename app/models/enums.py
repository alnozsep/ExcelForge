"""
app/models/enums.py

エラーコードと例外クラスの定義。
"""

from enum import Enum


class ErrorCode(str, Enum):
    INVALID_TOKEN = "INVALID_TOKEN"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    SCAN_PDF_NOT_SUPPORTED = "SCAN_PDF_NOT_SUPPORTED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EXTRACTION_JSON_PARSE_ERROR = "EXTRACTION_JSON_PARSE_ERROR"
    TEMPLATE_WRITE_ERROR = "TEMPLATE_WRITE_ERROR"
    TEMPLATE_INVALID = "TEMPLATE_INVALID"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    """アプリケーション共通の例外基底クラス"""
    def __init__(self, error_code: ErrorCode, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class FileReadError(AppException):
    def __init__(self, message: str):
        super().__init__(ErrorCode.FILE_READ_ERROR, message, 400)


class ExtractionError(AppException):
    def __init__(self, message: str):
        super().__init__(ErrorCode.EXTRACTION_FAILED, message, 422)


class TemplateWriteError(AppException):
    def __init__(self, message: str):
        super().__init__(ErrorCode.TEMPLATE_WRITE_ERROR, message, 500)
