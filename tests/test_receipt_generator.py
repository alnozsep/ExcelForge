"""
tests/test_receipt_generator.py
"""

from app.utils.receipt_generator import generate_receipt


def test_generate_receipt_returns_valid_receipt():
    receipt = generate_receipt(
        source_hash="abc123",
        template_hash="def456",
        source_type="pdf",
        source_size=1024,
        processing_time=1.5,
    )

    assert receipt.receipt_id is not None
    assert len(receipt.receipt_id) == 36  # UUID4 length
    assert receipt.source_file_hash == "abc123"
    assert receipt.template_file_hash == "def456"
    assert receipt.source_file_type == "pdf"
    assert receipt.source_file_size_bytes == 1024
    assert receipt.processing_time_seconds == 1.5
    assert receipt.gemini_model_used is not None
    assert receipt.data_retention == "none"
    assert receipt.storage_used == "none"
    assert receipt.database_used == "none"


def test_generate_receipt_unique_ids():
    receipt1 = generate_receipt(
        source_hash="h1",
        template_hash="h2",
        source_type="csv",
        source_size=0,
        processing_time=0.0,
    )
    receipt2 = generate_receipt(
        source_hash="h1",
        template_hash="h2",
        source_type="csv",
        source_size=0,
        processing_time=0.0,
    )

    assert receipt1.receipt_id != receipt2.receipt_id
