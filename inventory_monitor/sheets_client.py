# -*- coding: utf-8 -*-
"""Google Sheets（監視対象マスタ）の読み書き。"""
from __future__ import annotations

import json
import logging

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

from . import config

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_worksheet() -> gspread.Worksheet:
    if not config.GOOGLE_SHEET_ID:
        raise RuntimeError("GOOGLE_SHEET_ID が設定されていません。")
    raw = config.GOOGLE_SERVICE_ACCOUNT_JSON
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON が設定されていません。")
    try:
        creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    except json.JSONDecodeError:
        creds = Credentials.from_service_account_file(raw, scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_key(config.GOOGLE_SHEET_ID)
    return sh.worksheet(config.WORKSHEET_NAME)


def load_targets(ws: gspread.Worksheet) -> tuple[list[dict], list[str]]:
    """(監視対象のリスト, ヘッダー行) を返す。各要素に行番号 _row を付与。"""
    header = ws.row_values(1)
    missing = [c for c in config.REQUIRED_COLUMNS if c not in header]
    if missing:
        raise RuntimeError(f"シートの1行目に必須列がありません: {missing}")
    records = ws.get_all_records()
    targets = []
    for i, row in enumerate(records, start=2):
        if not str(row.get(config.COL_URL, "")).strip():
            continue  # 空行はスキップ
        row["_row"] = i
        targets.append(row)
    return targets, header


def update_row(ws: gspread.Worksheet, header: list[str], row_number: int, values: dict) -> None:
    """指定行の一部セルだけを1回のAPI呼び出しでまとめて更新する。"""
    data = []
    for col_name, value in values.items():
        if col_name not in header:
            continue
        a1 = rowcol_to_a1(row_number, header.index(col_name) + 1)
        data.append({"range": a1, "values": [[value]]})
    if data:
        ws.batch_update(data)
