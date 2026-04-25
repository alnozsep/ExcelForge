import openpyxl
import os

template_path = "/Users/nozakizai/Desktop/excelforge/test_data/invoice_template.xlsx"
wb = openpyxl.load_workbook(template_path)
ws = wb.active

print(f"Sheet Name: {ws.title}")
for row in ws.iter_rows(values_only=True):
    print(row)
