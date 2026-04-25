import io
from app.core.file_reader import read_file, FileType

template_path = "/Users/nozakizai/Desktop/excelforge/test_data/invoice_template.xlsx"
with open(template_path, "rb") as f:
    template_bytes = f.read()

template_text = read_file(template_bytes, FileType.XLSX)
print(template_text)
