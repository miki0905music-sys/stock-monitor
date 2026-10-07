# -*- coding: utf-8 -*-
"""
在庫監視のエントリポイント。

通知する状態遷移:
  in_stock -> sold_out        （在庫切れになった）
  sold_out -> in_stock        （在庫が復活した）
  in_stock -> unknown/error   （判定できなくなった）
  unknown/error -> in_stock   （判定不能中に在庫ありに復帰。見逃し防止のため追加）
初回（last_statusが空）は記録のみで通知しない。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from . import config, notifier, sheets_client
from .sites import SITE_CHECKERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

NOTIFY_TRANSITIONS = {
    ("in_stock", "sold_out"),
    ("sold_out", "in_stock"),
    ("in_stock", "unknown"),
    ("in_stock", "error"),
    ("unknown", "in_stock"),
    ("error", "in_stock"),
}


def should_notify(prev: str, curr: str) -> bool:
    return (prev, curr) in NOTIFY_TRANSITIONS


def run() -> None:
    ws = sheets_client.get_worksheet()
    targets, header = sheets_client.load_targets(ws)
    logger.info("監視対象 %d件を読み込みました。", len(targets))

    for i, target in enumerate(targets):
        site_key = str(target.get(config.COL_SITE, "")).strip()
        url = str(target.get(config.COL_URL, "")).strip()
        row_number = target["_row"]

        checker_cls = SITE_CHECKERS.get(site_key)
        if checker_cls is None:
            logger.warning("未対応のsite '%s' です（行%s）。スキップします。", site_key, row_number)
            continue

        result = checker_cls().check(url)

        prev = str(target.get(config.COL_LAST_STATUS, "")).strip()
        curr = result.status.value
        now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

        values = {
            config.COL_LAST_STATUS: curr,
            config.COL_LAST_CHECKED_AT: now_str,
            config.COL_MEMO: result.detail,
        }
        if result.product_name:
            values[config.COL_PRODUCT_NAME] = result.product_name

        if should_notify(prev, curr):
            sent = notifier.send_status_change_alert(
                site_key=site_key,
                product_name=result.product_name or str(target.get(config.COL_PRODUCT_NAME, "")),
                url=url, price=result.price, prev=prev, curr=curr, detail=result.detail,
            )
            if sent:
                values[config.COL_NOTIFIED_AT] = now_str

        sheets_client.update_row(ws, header, row_number, values)
        logger.info("[%s] %s: %s -> %s (%s)", site_key, url, prev or "(初回)", curr, result.detail)

        if i < len(targets) - 1:
            time.sleep(config.REQUEST_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
