"""
app/core/excel_writer.py

責務: Excelテンプレートをメモリ上で開き、抽出データを指定セルに書き込み、BytesIOとして返す。
"""

import io
from typing import Optional
import openpyxl
import re

from app.models.enums import AppException, ErrorCode


def _is_merged_cell(worksheet, cell) -> bool:
    """セルが結合セルの一部かどうかを判定する"""
    for merged_range in worksheet.merged_cells.ranges:
        if cell.coordinate in merged_range:
            return True
    return False


def _get_merged_cell_master(worksheet, cell):
    """結合セルの左上（マスター）セルを返す"""
    for merged_range in worksheet.merged_cells.ranges:
        if cell.coordinate in merged_range:
            # 結合範囲の左上のセルを返す
            return worksheet.cell(row=merged_range.min_row, column=merged_range.min_col)
    return cell


def _has_formula(cell) -> bool:
    """セルに数式が含まれているかを判定する"""
    return cell.data_type == "f" or (
        isinstance(cell.value, str) and cell.value.startswith("=")
    )


def write_to_template(
    template_bytes: bytes, extracted_data: dict, mapping_config: Optional[dict] = None
) -> io.BytesIO:
    """
    Excelテンプレートにデータを書き込む。
    """
    try:
        # メモリ上でExcelファイルを開く
        wb = openpyxl.load_workbook(io.BytesIO(template_bytes))

        if mapping_config and "mappings" in mapping_config:
            # マッピング設定に基づく書き込み
            mappings = mapping_config.get("mappings", [])
            for mapping in mappings:
                key = mapping.get("key")
                sheet_name = mapping.get("sheet")
                cell_ref = mapping.get("cell")

                if not key or key not in extracted_data:
                    continue

                val = extracted_data[key]
                if val is None:
                    continue

                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                else:
                    # シートが存在しない場合は最初のアクティブシートを使用
                    ws = wb.active

                target_cell = ws[cell_ref]

                # 結合セルの場合はマスターセルを取得
                if _is_merged_cell(ws, target_cell):
                    target_cell = _get_merged_cell_master(ws, target_cell)

                # 数式セルはスキップ
                if _has_formula(target_cell):
                    continue

                # 値を書き込み（元の書式は維持される）
                target_cell.value = val

        # 直接セル指定（Sheet:Cell形式）の書き込み
        for key, val in extracted_data.items():
            if val is None or not isinstance(key, str) or ":" not in key:
                continue
            
            parts = key.split(":")
            if len(parts) == 2:
                sheet_name, cell_ref = parts
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    try:
                        # セル番地が有効かチェック
                        target_cell = ws[cell_ref]
                        if _is_merged_cell(ws, target_cell):
                            target_cell = _get_merged_cell_master(ws, target_cell)
                        if not _has_formula(target_cell):
                            target_cell.value = val
                    except Exception:
                        continue

        else:
            # mapping_configがない場合はプレースホルダー {{key}} を探して置換
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                for row in ws.iter_rows():
                    for cell in row:
                        if (
                            isinstance(cell.value, str)
                            and "{{" in cell.value
                            and "}}" in cell.value
                        ):
                            # セル内のすべてのプレースホルダーを置換
                            new_value = cell.value
                            matches = re.findall(r"\{\{([^}]+)\}\}", cell.value)

                            has_replacement = False
                            for key in matches:
                                if (
                                    key in extracted_data
                                    and extracted_data[key] is not None
                                ):
                                    # 置換
                                    val_str = str(extracted_data[key])
                                    new_value = new_value.replace(
                                        f"{{{{{key}}}}}", val_str
                                    )
                                    has_replacement = True
                                elif mapping_config and key in mapping_config:
                                    # mapping_config（辞書形式）でキーの指定がある場合
                                    # ただし、プレースホルダー方式でmapping_config(dict)を使うケースへの対応
                                    pass

                            if has_replacement:
                                # 元が完全に "{{key}}" のみで、置換結果が数値の場合は数値に変換
                                if (
                                    len(matches) == 1
                                    and cell.value.strip() == f"{{{{{matches[0]}}}}}"
                                ):
                                    val = extracted_data[matches[0]]
                                    if isinstance(val, (int, float)):
                                        new_value = val

                                # 結合セルの場合はマスターセルに書き込む
                                if _is_merged_cell(ws, cell):
                                    master_cell = _get_merged_cell_master(ws, cell)
                                    if not _has_formula(master_cell):
                                        master_cell.value = new_value
                                else:
                                    if not _has_formula(cell):
                                        cell.value = new_value

        # BytesIOに保存して返す
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    except Exception as e:
        raise AppException(
            ErrorCode.TEMPLATE_ERROR, f"テンプレート書き込みエラー: {str(e)}"
        )
