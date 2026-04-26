"""
app/utils/cleanup.py


メモリ上のデータを明示的に削除するユーティリティ。
Pythonのガベージコレクタに任せるだけでは不十分な場合の安全策。

注意:
  - bytes型は不変オブジェクトのため、ゼロ埋めはできない。
    また、引数は値渡しのため呼び出し元の変数には影響しない。
    この関数はあくまでベストエフォートの補助的クリーンアップである。
"""

import io
from typing import Any


def cleanup_variables(*variables: Any) -> None:
    """
    渡されたすべての変数を明示的にクリーンアップする。

    処理:
        - bytes/bytearray: 参照解放のためdel（Pythonではbytes不変のため上書き不可）
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
                # bytesは不変オブジェクトのため上書き不可。
                # 参照解放は呼び出し側のローカル変数には影響しないが、
                # 大きなバイナリの早期解放を促す意図がある。
                pass
            elif isinstance(var, io.BytesIO):
                if not var.closed:
                    var.close()
            elif isinstance(var, dict):
                var.clear()
            elif isinstance(var, list):
                var.clear()
        except Exception:
            pass  # クリーンアップ自体のエラーは無視する
