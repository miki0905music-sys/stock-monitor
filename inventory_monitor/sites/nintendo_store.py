# -*- coding: utf-8 -*-
"""
マイニンテンドーストア（store-jp.nintendo.com/item/goods/...）の在庫チェッカー。

判定根拠（在庫あり商品・品切れ商品の「ページのソースを表示」2件を比較して確認）:

 1. 主判定: <script id="mobify-data" type="application/json"> 内の商品データ。
      __PRELOADED_STATE__.__reactQuery.queries[*] のうち、
      queryKey に "/products/" を含むクエリの state.data.inventory
        在庫あり: orderable=true,  stockLevel=135 (ats=135)
        品切れ  : orderable=false, stockLevel=0   (ats=0)
    ※ queries の並び順（添字）は固定とみなさず、queryKey で探す。

 2. 副判定: 描画済みHTML内のカート操作ボタンの文言
        在庫あり: <button>カートに入れる</button>
        品切れ  : <button disabled aria-disabled="true">品切れ</button>
    ※ クラス名はTailwindの見た目用で不安定なため使わず、文言のみを見る。

判定方針:
   1と2が両方取得でき、一致した場合のみ確定。
   不一致・取得不能・未確認の状態（予約/取り寄せ可、複数バリエーション）は
   UNKNOWN。ページ取得そのものの失敗（403/429/通信エラー等）は ERROR。

アクセス方針:
   robots.txt は /item/ を禁止していない（確認済み）。
   User-Agent は偽装せず、ブロックされた場合（403/429）も回避せず ERROR として記録する。
"""
from __future__ import annotations

import json
import logging

import requests
from bs4 import BeautifulSoup

from .base import StockChecker, StockResult, StockStatus

logger = logging.getLogger(__name__)

USER_AGENT = "InventoryMonitorBot/1.0 (personal use; low-frequency)"
REQUEST_TIMEOUT = 15

BUTTON_TEXT_IN_STOCK = "カートに入れる"
BUTTON_TEXT_SOLD_OUT = "品切れ"


class NintendoStoreChecker(StockChecker):
    site_key = "nintendo_store"

    def check(self, url: str) -> StockResult:
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("NintendoStore: HTTP取得失敗 url=%s error=%s", url, e)
            return StockResult(status=StockStatus.ERROR, detail=f"HTTP取得失敗: {e}")

        return self.judge(resp.text)

    # ------------------------------------------------------------------
    def judge(self, html: str) -> StockResult:
        """HTML文字列から在庫を判定する（通信を伴わないのでテストしやすい）。"""
        soup = BeautifulSoup(html, "html.parser")

        product = self._find_product(soup)
        button_status = self._parse_button(soup)

        name = price = None
        data_status = None
        data_note = ""
        if product is not None:
            name = product.get("name")
            try:
                price = int(product["price"]) if product.get("price") is not None else None
            except (TypeError, ValueError):
                price = None
            data_status, data_note = self._status_from_product(product)

        if data_status is None and button_status is None:
            return StockResult(
                status=StockStatus.UNKNOWN, product_name=name, price=price,
                detail=f"商品データ・ボタンのどちらからも判定できません（構造変更の可能性）{data_note}",
            )

        if data_status is not None and button_status is not None:
            if data_status != button_status:
                return StockResult(
                    status=StockStatus.UNKNOWN, product_name=name, price=price,
                    detail=f"判定シグナル不一致（商品データ={data_status.value}, ボタン={button_status.value}）",
                )
            return StockResult(status=data_status, product_name=name, price=price,
                               detail="商品データ(inventory)とボタン文言が一致")

        # 片方しか取れない場合は確定させない（誤通知を避ける）
        got = data_status or button_status
        src = "商品データのみ" if data_status else "ボタンのみ"
        return StockResult(
            status=StockStatus.UNKNOWN, product_name=name, price=price,
            detail=f"片方のシグナルのみ取得（{src}={got.value}）。確定できません。{data_note}",
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _find_product(soup: BeautifulSoup):
        tag = soup.find("script", id="mobify-data")
        if tag is None:
            return None
        raw = tag.string or tag.get_text()
        try:
            data = json.loads(raw)
            queries = data["__PRELOADED_STATE__"]["__reactQuery"]["queries"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
        for q in queries:
            key = q.get("queryKey") or []
            if "/products/" not in key:
                continue
            d = (q.get("state") or {}).get("data")
            if isinstance(d, dict) and isinstance(d.get("inventory"), dict):
                return d
        return None

    @staticmethod
    def _status_from_product(product: dict):
        """(StockStatus | None, 補足メモ) を返す。確認済みのパターン以外は None。"""
        inv = product["inventory"]
        orderable = inv.get("orderable")
        level = inv.get("stockLevel")
        if not isinstance(orderable, bool) or not isinstance(level, int):
            return None, "（inventoryの形式が想定外）"

        # 2商品でしか確認していない状態は、推測で判定せず UNKNOWN に回す
        if inv.get("preorderable") or inv.get("backorderable"):
            return None, "（予約/取り寄せ可の商品は未確認）"
        variants = product.get("variants")
        if isinstance(variants, list) and len(variants) > 1:
            return None, "（複数バリエーション商品は未確認）"

        if orderable and level > 0:
            return StockStatus.IN_STOCK, ""
        if not orderable and level == 0:
            return StockStatus.OUT_OF_STOCK, ""
        return None, f"（orderable={orderable} と stockLevel={level} が矛盾）"

    @staticmethod
    def _parse_button(soup: BeautifulSoup):
        found = set()
        for b in soup.find_all("button"):
            text = b.get_text(strip=True)
            if text == BUTTON_TEXT_IN_STOCK:
                if b.has_attr("disabled") or b.get("aria-disabled") == "true":
                    return None  # 文言と状態が食い違う → 確定しない
                found.add(StockStatus.IN_STOCK)
            elif text == BUTTON_TEXT_SOLD_OUT:
                found.add(StockStatus.OUT_OF_STOCK)
        return found.pop() if len(found) == 1 else None
