# -*- coding: utf-8 -*-
"""
Nintendo Store 用スタブ（未実装）。
実装時は Kirby Cafe と同様に、在庫あり/在庫切れの実ページを比較して
共通の判定要素を特定してから check() を書くこと。推測で実装しない。
"""
from __future__ import annotations

from .base import StockChecker, StockResult, StockStatus


class NintendoStoreChecker(StockChecker):
    site_key = "nintendo_store"

    def check(self, url: str) -> StockResult:
        return StockResult(status=StockStatus.UNKNOWN, detail="NintendoStoreChecker は未実装です")
