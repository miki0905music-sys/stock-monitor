# -*- coding: utf-8 -*-
"""
Kirby Cafe ポップアップストア（kirbycafe-popup.com）の在庫チェッカー。

判定根拠（在庫あり/在庫切れの実ページHTMLを比較して確認済み）:
 1. 主判定: <script type="application/ld+json"> の Product.offers.availability
      .../InStock    → 在庫あり
      .../OutOfStock → 在庫切れ
 2. 副判定: input.sysCartButton.sysCartInButton の disabled 属性の有無
 両者が取得でき一致した場合のみ確定。矛盾・取得不能は UNKNOWN。
 ページ取得自体の失敗は ERROR。
"""
from __future__ import annotations

import json
import logging

import requests
from bs4 import BeautifulSoup

from .base import StockChecker, StockResult, StockStatus

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    "InventoryMonitorBot/1.0 (personal use; low-frequency)"
)
REQUEST_TIMEOUT = 15


class KirbyCafeChecker(StockChecker):
    site_key = "kirby_cafe"

    def check(self, url: str) -> StockResult:
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("KirbyCafe: HTTP取得失敗 url=%s error=%s", url, e)
            return StockResult(status=StockStatus.ERROR, detail=f"HTTP取得失敗: {e}")

        soup = BeautifulSoup(resp.text, "html.parser")
        ld_status, name, price = self._parse_json_ld(soup)
        button_status = self._parse_cart_button(soup)

        if ld_status is None and button_status is None:
            return StockResult(
                status=StockStatus.UNKNOWN, product_name=name, price=price,
                detail="JSON-LDとカートボタンのどちらからも在庫シグナルを取得できません（サイト構造変更の可能性）",
            )

        if ld_status is not None and button_status is not None:
            if ld_status != button_status:
                return StockResult(
                    status=StockStatus.UNKNOWN, product_name=name, price=price,
                    detail=f"判定シグナル不一致（JSON-LD={ld_status.value}, ボタン={button_status.value}）",
                )
            return StockResult(
                status=ld_status, product_name=name, price=price,
                detail="JSON-LDとカートボタンが一致",
            )

        only = ld_status or button_status
        src = "JSON-LDのみ" if ld_status else "カートボタンのみ"
        return StockResult(status=only, product_name=name, price=price,
                           detail=f"片方のシグナルのみ取得（{src}）")

    @staticmethod
    def _parse_json_ld(soup: BeautifulSoup):
        for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = tag.string or tag.get_text()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for obj in (data if isinstance(data, list) else [data]):
                if not isinstance(obj, dict) or obj.get("@type") != "Product":
                    continue
                offers = obj.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                availability = str(offers.get("availability", ""))
                name = obj.get("name")
                try:
                    price = int(offers["price"]) if offers.get("price") is not None else None
                except (TypeError, ValueError):
                    price = None
                if availability.endswith("/InStock"):
                    return StockStatus.IN_STOCK, name, price
                if availability.endswith("/OutOfStock"):
                    return StockStatus.OUT_OF_STOCK, name, price
                return None, name, price
        return None, None, None

    @staticmethod
    def _parse_cart_button(soup: BeautifulSoup):
        button = soup.select_one("input.sysCartButton.sysCartInButton")
        if button is None:
            return None
        return StockStatus.OUT_OF_STOCK if button.has_attr("disabled") else StockStatus.IN_STOCK
