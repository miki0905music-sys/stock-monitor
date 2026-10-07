# -*- coding: utf-8 -*-
"""在庫状態の変化をDiscord Webhookで通知する。"""
from __future__ import annotations

import logging

import requests

from . import config

logger = logging.getLogger(__name__)

_LABELS = {
    "in_stock": "✅ 在庫あり",
    "sold_out": "❌ 在庫切れ",
    "unknown": "⚠️ 判定不能(UNKNOWN)",
    "error": "⚠️ 取得エラー(ERROR)",
}


def send_status_change_alert(*, site_key: str, product_name: str, url: str,
                             price: int | None, prev: str, curr: str,
                             detail: str = "") -> bool:
    if not config.DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL が未設定のため通知をスキップしました。")
        return False

    price_text = f"￥{price:,}" if price is not None else "価格不明"
    lines = [
        f"🔔 **在庫状態が変化しました** [{site_key}]",
        f"{product_name or '(商品名不明)'} / {price_text}",
        f"{_LABELS.get(prev, prev)} → {_LABELS.get(curr, curr)}",
    ]
    if detail and curr in ("unknown", "error"):
        lines.append(f"詳細: {detail}")
    lines.append(url)

    try:
        resp = requests.post(config.DISCORD_WEBHOOK_URL,
                             json={"content": "\n".join(lines)}, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("Discord通知送信に失敗しました: %s", e)
        return False
