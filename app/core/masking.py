"""
app/core/masking.py


責務: テキストから個人情報をマスキングし、
      処理後に復元する。


制約:
  - マスキングは「可能な範囲で」行うものであり、
    100%の検出を保証しない
  - マスキング/復元のペアは同一リクエスト内で完結する
  - マスキングマップはメモリ上にのみ存在する
"""

import re
from dataclasses import dataclass, field


@dataclass
class MaskingResult:
    masked_text: str
    mask_map: dict[str, str] = field(default_factory=dict)
    # mask_map例: {"[MASK_001]": "090-1234-5678", "[MASK_002]": "1234-5678-9012"}


def mask_sensitive_data(text: str) -> MaskingResult:
    """
    以下のパターンをマスキングする:

    1. マイナンバー（12桁の数字、ハイフン・スペース区切り含む）
       パターン: r'\d{4}[\s-]?\d{4}[\s-]?\d{4}'
       置換先: [MASK_MYNUMBER_001]

    2. 電話番号（固定・携帯）
       パターン: r'0\d{1,4}[\s-]?\d{1,4}[\s-]?\d{3,4}'
       置換先: [MASK_PHONE_001]

    3. メールアドレス
       パターン: r'[\w\.\-]+@[\w\.\-]+'
       置換先: [MASK_EMAIL_001]

    4. 銀行口座番号（7桁の連続数字）
       パターン: r'(?<!\d)\d{7}(?!\d)'
       置換先: [MASK_ACCOUNT_001]
       注: このパターンは郵便番号下4桁など、
           すべての7桁連続数字にマッチする可能性がある。
           100%の精度を保証するものではなく、過剰検出の可能性に留意すること。

    連番はカテゴリごとに001からインクリメントする。
    """
    if not text:
        return MaskingResult(masked_text=text)

    mask_map = {}
    counters = {
        "MYNUMBER": 1,
        "PHONE": 1,
        "EMAIL": 1,
        "ACCOUNT": 1,
    }

    # 各パターンの定義
    patterns = {
        "MYNUMBER": r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)",
        "PHONE": r"(?<!\d)0\d{1,4}[\s-]?\d{1,4}[\s-]?\d{3,4}(?!\d)",
        "EMAIL": r"[\w\.\-]+@[\w\.\-]+",
        "ACCOUNT": r"(?<!\d)\d{7}(?!\d)",
    }

    masked_text = text

    # 置換処理の共通関数
    def replacer(match, category):
        original_value = match.group(0)
        # 既にマップされている場合は同じプレースホルダを再利用するか、新規発行する
        # （ここではシンプルに毎回新規発行、または既に同じ値があれば再利用でも良いが、
        #   連番をつける仕様なので新規発行とする）
        placeholder = f"[MASK_{category}_{counters[category]:03d}]"
        mask_map[placeholder] = original_value
        counters[category] += 1
        return placeholder

    # MYNUMBER
    masked_text = re.sub(
        patterns["MYNUMBER"], lambda m: replacer(m, "MYNUMBER"), masked_text
    )

    # PHONE
    masked_text = re.sub(patterns["PHONE"], lambda m: replacer(m, "PHONE"), masked_text)

    # EMAIL
    masked_text = re.sub(patterns["EMAIL"], lambda m: replacer(m, "EMAIL"), masked_text)

    # ACCOUNT
    masked_text = re.sub(
        patterns["ACCOUNT"], lambda m: replacer(m, "ACCOUNT"), masked_text
    )

    return MaskingResult(masked_text=masked_text, mask_map=mask_map)


def unmask_data(masked_text: str, mask_map: dict[str, str]) -> str:
    """
    マスキングされたテキストを元に戻す。
    mask_mapのキーをバリューで置換する。
    """
    if not masked_text or not mask_map:
        return masked_text

    unmasked_text = masked_text
    for placeholder, original_value in mask_map.items():
        unmasked_text = unmasked_text.replace(placeholder, original_value)

    return unmasked_text
