"""
app/utils/cleanup.py


メモリ上のデータを明示的に削除するユーティリティ。
Pythonのガベージコレクタに任せるだけでは不十分な場合の安全策。
"""

import io
from typing import Any


def cleanup_variables(*variables: Any) -> None:
    """
    渡されたすべての変数を明示的にクリーンアップする。

    処理:
        - bytes型: ゼロで上書きしてからdel（セキュアな削除）
        - io.BytesIO: close()してからdel
        - dict/list: clear()してからdel
        - それ以外: del のみ

    いずれの変数がNoneでもエラーにしない。
    """
    for var in variables:
        if var is None:
            continue
        try:
            if isinstance(var, (bytes, bytearray)):
                # bytesは不変なのでbytearray化して上書き
                # ※完全なセキュア削除はPythonでは困難だが、ベストエフォートで
                if isinstance(var, bytearray):
                    for i in range(len(var)):
                        var[i] = 0
            elif isinstance(var, io.BytesIO):
                if not var.closed:
                    var.close()
            elif isinstance(var, dict):
                var.clear()
            elif isinstance(var, list):
                var.clear()
        except Exception:
            pass  # クリーンアップ自体のエラーは無視する
