# -*- coding: utf-8 -*-
"""site列の値 → チェッカークラスの対応表。新サイトはここに1行足す。"""
from .base import StockChecker, StockResult, StockStatus  # noqa: F401
from .kirby_cafe import KirbyCafeChecker
from .nintendo_store import NintendoStoreChecker

SITE_CHECKERS: dict[str, type[StockChecker]] = {
    KirbyCafeChecker.site_key: KirbyCafeChecker,
    NintendoStoreChecker.site_key: NintendoStoreChecker,
}
