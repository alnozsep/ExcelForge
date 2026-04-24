"""
app/config.py

すべての設定値はこのファイルで一元管理する。
ハードコードされた設定値をコード内に散在させない。
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # === アプリケーション ===
    APP_NAME: str = "ExcelForge"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # === サーバー ===
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # === Gemini API ===
    GCP_PROJECT_ID: str
    GCP_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    GEMINI_TEMPERATURE: float = 0.0  # 再現性を最大化するため0固定

    # === ファイル制限 ===
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_SOURCE_EXTENSIONS: list[str] = [".pdf", ".csv", ".xlsx", ".xls"]
    ALLOWED_TEMPLATE_EXTENSIONS: list[str] = [".xlsx"]
    MAX_PDF_PAGES: int = 20

    # === セキュリティ ===
    VALID_TOKENS: dict[str, str] = {}
    # 形式: {"token文字列": "顧客名"}
    # 例: {"abc123xyz": "株式会社A", "def456uvw": "B事務所"}

    # === ログ ===
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # === タイムアウト ===
    GEMINI_TIMEOUT_SECONDS: int = 120
    REQUEST_TIMEOUT_SECONDS: int = 180

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
