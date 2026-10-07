# -*- coding: utf-8 -*-
"""設定値。秘匿情報は環境変数（GitHub Secrets）から読み込む。"""
from __future__ import annotations

import os

GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
# サービスアカウントJSONの中身（文字列）またはファイルパス
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
WORKSHEET_NAME = os.environ.get("WORKSHEET_NAME", "監視対象")

COL_SITE = "site"
COL_PRODUCT_ID = "product_id"
COL_URL = "url"
COL_PRODUCT_NAME = "product_name"
COL_LAST_STATUS = "last_status"
COL_LAST_CHECKED_AT = "last_checked_at"
COL_NOTIFIED_AT = "notified_at"
COL_MEMO = "memo"

REQUIRED_COLUMNS = [
    COL_SITE, COL_PRODUCT_ID, COL_URL, COL_PRODUCT_NAME,
    COL_LAST_STATUS, COL_LAST_CHECKED_AT, COL_NOTIFIED_AT, COL_MEMO,
]

# 商品ごとのリクエスト間隔（秒）。サイトへの負荷配慮のため短くしすぎない。
REQUEST_INTERVAL_SECONDS = float(os.environ.get("REQUEST_INTERVAL_SECONDS", "3"))

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
