"""twikit 2.3.3 の ClientTransaction.get_indices を、Xの現行仕様に合わせて差し替えるパッチ。

背景:
  2026-03 頃、Xが ondemand.s.js の参照方法をwebpackのチャンク番号経由に変えたため、
  公式のtwikit 2.3.3 は "Couldn't get KEY_BYTE indices" で全リクエストが失敗する。
  修正PR(https://github.com/d60/twikit/pull/410, #411)は未マージのまま、
  PR #410 のフォークはその後削除されて pip install できなくなった(2026-11)。

  そこで第三者のフォークに依存せず、PyPI の twikit==2.3.3 に対して
  同等の修正をこのリポジトリ内で適用する。内容は PR #410 の transaction.py の
  変更(正規表現3つと get_indices)と同じで、通信先も元コードと同じ abs.twimg.com のみ。

  公式が修正版をリリースしたら、このファイルとimportを削除してよい。
"""
import re

from twikit.x_client_transaction import transaction as _transaction

# 例: ...,12345:"ondemand.s",... のチャンク番号を取得
ON_DEMAND_FILE_REGEX = re.compile(r""",(\d+):["']ondemand\.s["']""")
# チャンク番号 -> ファイル名ハッシュ (例: ,12345:"abcdef0123")
ON_DEMAND_HASH_PATTERN = r',{}:"([0-9a-f]+)"'
# ondemand.s.*.js 内の KEY_BYTE インデックス
INDICES_REGEX = re.compile(r"\[(\d+)\],\s*16")


async def _get_indices(self, home_page_response, session, headers):
    key_byte_indices = []
    response = self.validate_response(home_page_response) or self.home_page_response
    response_str = str(response)

    on_demand_file = ON_DEMAND_FILE_REGEX.search(response_str)
    if on_demand_file:
        chunk_index = on_demand_file.group(1)
        hash_match = re.search(ON_DEMAND_HASH_PATTERN.format(chunk_index), response_str)
        if hash_match:
            filename = hash_match.group(1)
            on_demand_file_url = (
                f"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{filename}a.js"
            )
            on_demand_file_response = await session.request(
                method="GET", url=on_demand_file_url, headers=headers
            )
            for item in INDICES_REGEX.finditer(str(on_demand_file_response.text)):
                key_byte_indices.append(item.group(1))

    if not key_byte_indices:
        raise Exception("Couldn't get KEY_BYTE indices")

    key_byte_indices = list(map(int, key_byte_indices))
    return key_byte_indices[0], key_byte_indices[1:]


_transaction.ClientTransaction.get_indices = _get_indices
