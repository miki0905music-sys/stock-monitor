# -*- coding: utf-8 -*-
"""サイトごとの在庫チェッカーが実装する共通インターフェース。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StockStatus(str, Enum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "sold_out"
    UNKNOWN = "unknown"  # シグナルが取れない/矛盾する場合
    ERROR = "error"      # ページ自体を取得できなかった場合（HTTPエラー等）


@dataclass
class StockResult:
    status: StockStatus
    product_name: str | None = None
    price: int | None = None
    checked_at: datetime = field(default_factory=datetime.now)
    detail: str = ""


class StockChecker(ABC):
    site_key: str = "base"

    @abstractmethod
    def check(self, url: str) -> StockResult:
        """在庫状況を判定する。判定不能時は例外ではなく UNKNOWN / ERROR を返す。"""
        raise NotImplementedError
