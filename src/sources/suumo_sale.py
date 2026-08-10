"""
SUUMO 中古マンション売買 (suumo.jp/ms/chuko) スクレイパー.

検索ページ: /ms/chuko/tokyo/sc_shibuya/ （区単位URL）
ページネーション: ?page={n}
物件カード構造（property_unit内のdottableテーブル）:
  物件名: メゾンジャルダン
  販売価格: 2980万円
  所在地: 東京都渋谷区千駄ヶ谷３-8-4
  沿線・駅: 東京メトロ副都心線「北参道」徒歩5分
  専有面積: 28.78m2
  間取り: ワンルーム
  築年数: 2000年3月
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://suumo.jp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 東京23区の区URL（sc_XXXX形式）
TOKYO_WARDS = {
    "千代田区": "sc_chiyoda",
    "中央区": "sc_chuo",
    "港区": "sc_minato",
    "新宿区": "sc_shinjuku",
    "文京区": "sc_bunkyo",
    "台東区": "sc_taito",
    "墨田区": "sc_sumida",
    "江東区": "sc_koto",
    "品川区": "sc_shinagawa",
    "目黒区": "sc_meguro",
    "大田区": "sc_ota",
    "世田谷区": "sc_setagaya",
    "渋谷区": "sc_shibuya",
    "中野区": "sc_nakano",
    "杉並区": "sc_suginami",
    "豊島区": "sc_toshima",
    "北区": "sc_kita",
    "荒川区": "sc_arakawa",
    "板橋区": "sc_itabashi",
    "練馬区": "sc_nerima",
    "足立区": "sc_adachi",
    "葛飾区": "sc_katsushika",
    "江戸川区": "sc_edogawa",
}


async def fetch_page(client: httpx.AsyncClient, url: str, max_retries: int = 3) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            resp = await client.get(url, headers=HEADERS, follow_redirects=True)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                return resp.text
            if resp.status_code in (403, 429):
                await asyncio.sleep(3 * (attempt + 1))
                continue
            return None
        except httpx.HTTPError:
            await asyncio.sleep(2 * (attempt + 1))
    return None


def _clean_price(raw: str) -> Optional[int]:
    """'2980万円' → 29800000 / '9,800万円' → 98000000"""
    raw = raw.strip().replace(",", "")
    m = re.search(r"([\d.]+)億円", raw)
    if m:
        return int(float(m.group(1)) * 100000000)
    m = re.search(r"([\d.]+)万円", raw)
    if m:
        return int(float(m.group(1)) * 10000)
    return None


def _extract_dl(container) -> dict:
    """dl/dt/ddペアを抽出（dottable-line内・dottable-fix内とも）"""
    result: dict[str, str] = {}
    for dl in container.select("dl"):
        dt = dl.find("dt")
        dd = dl.find("dd")
        if dt and dd:
            label = dt.get_text(" ", strip=True)
            value = dd.get_text(" ", strip=True)
            if label and value and label not in result:
                result[label] = value
    return result


def parse_items(html: str, ward: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for unit in soup.select(".property_unit"):
        # 物件リンク
        link = ""
        link_el = unit.select_one("a[href*='/ms/chuko/']")
        if link_el:
            href = str(link_el.get("href", "") or "")
            if href.startswith("/"):
                link = BASE_URL + href
        # dottable全体（dottable--cassette + dottable-fix）から dl/dt/dd 抽出
        info: dict[str, str] = {}
        for dtable in unit.select("div.dottable, table.dottable-fix"):
            info.update(_extract_dl(dtable))
        title = info.get("物件名", "")
        price = _clean_price(info.get("販売価格", ""))
        if not title and price is None:
            continue
        items.append({
            "productId": f"suumo-sale-{ward}-{title}-{info.get('間取り','')}-{len(items)}",
            "title": title,
            "price": price,
            "address": info.get("所在地", ""),
            "station": info.get("沿線・駅", "") or info.get("交通", ""),
            "layout": info.get("間取り", ""),
            "areaSqm": info.get("専有面積", ""),
            "buildingAge": info.get("築年月", "") or info.get("築年数", ""),
            "totalFloors": info.get("所在階", "") or info.get("建物階数", "") or info.get("建物構造", ""),
            "productUrl": link or BASE_URL,
            "source": "suumo_sale",
            "shop": "SUUMO 中古マンション",
            "ward": ward,
        })
    return items


async def search_suumo_sale(
    client: httpx.AsyncClient,
    ward: str = "渋谷区",
    max_pages: int = 2,
    max_items: int = 100,
) -> list[dict]:
    if ward not in TOKYO_WARDS:
        ward = "渋谷区"
    sc = TOKYO_WARDS[ward]
    base = f"{BASE_URL}/ms/chuko/tokyo/{sc}/"
    results: list[dict] = []
    page = 1
    while page <= max_pages and len(results) < max_items:
        url = f"{base}?page={page}"
        html = await fetch_page(client, url)
        if not html:
            break
        items = parse_items(html, ward)
        if not items:
            break
        for it in items:
            if len(results) >= max_items:
                break
            it["scrapedAt"] = __import__("datetime").datetime.now().isoformat() + "Z"
            results.append(it)
        if f"page={page+1}" not in html:
            break
        page += 1
        await asyncio.sleep(0.5)
    return results
