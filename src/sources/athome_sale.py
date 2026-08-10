"""
at home 中古マンション売買 (athome.co.jp/mansion/chuko) スクレイパー.

検索ページ: /mansion/chuko/tokyo/shibuya-city/list/
ページネーション: /mansion/chuko/tokyo/shibuya-city/list/page{n}/
物件カード構造（bukken-item内）:
  価格: <div class="property-price">880 万円</div>
  タイトル: <div class="title-wrap__title-text">...</div>
  詳細テーブル: <table class="property-detail-table">
    間取り: ワンルーム
    築年月: 1983年7月（築43年2ヶ月）
    階建: 5階建 / 3階
    構造: ＲＣ
    専有面積: 13.21m²
    所在地: 渋谷区本町６丁目
    交通: 京王線 「幡ヶ谷」駅 徒歩10分
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.athome.co.jp"
# at home は Accept-Language/Accept 付きだとブロックされる（405）ためUAのみ
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}

# 東京23区のURL
TOKYO_WARDS = {
    "千代田区": "chiyoda-city",
    "中央区": "chuo-city",
    "港区": "minato-city",
    "新宿区": "shinjuku-city",
    "文京区": "bunkyo-city",
    "台東区": "taito-city",
    "墨田区": "sumida-city",
    "江東区": "koto-city",
    "品川区": "shinagawa-city",
    "目黒区": "meguro-city",
    "大田区": "ota-city",
    "世田谷区": "setagaya-city",
    "渋谷区": "shibuya-city",
    "中野区": "nakano-city",
    "杉並区": "suginami-city",
    "豊島区": "toshima-city",
    "北区": "kita-city",
    "荒川区": "arakawa-city",
    "板橋区": "itabashi-city",
    "練馬区": "nerima-city",
    "足立区": "adachi-city",
    "葛飾区": "katsushika-city",
    "江戸川区": "edogawa-city",
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
    """'880 万円' → 8800000 / '1億2,000万円' → 120000000"""
    raw = raw.strip().replace(",", "").replace(" ", "")
    m = re.search(r"([\d.]+)億円", raw)
    if m:
        return int(float(m.group(1)) * 100000000)
    m = re.search(r"([\d.]+)万円", raw)
    if m:
        return int(float(m.group(1)) * 10000)
    return None


def parse_items(html: str, ward: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".card-box"):
        # タイトル（住所ベース: 渋谷区 本町６丁目（幡ヶ谷駅） 3階 ワンルーム）
        title_el = card.select_one(".title-wrap__title-text")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if not title:
            continue
        # 価格（<p>880万円</p>）
        price = None
        p_el = title_el.select_one("p") if title_el else None
        if p_el:
            price = _clean_price(p_el.get_text(" ", strip=True))
        # リンク
        link = ""
        link_el = card.select_one("a[href*='/mansion/'], a[href*='/kodate/']")
        if link_el:
            href = str(link_el.get("href", "") or "")
            if href.startswith("/"):
                link = BASE_URL + href.split("?")[0]
        # 詳細テーブル（property-detail-table）
        layout = ""
        build_year = ""
        total_floors = ""
        structure = ""
        area = ""
        address = ""
        station = ""
        table = card.select_one(".property-detail-table")
        if table:
            for dl in table.select("dl"):
                dt = dl.find("dt")
                dd = dl.find("dd")
                if not dt or not dd:
                    continue
                label = dt.get_text(" ", strip=True)
                value = dd.get_text(" ", strip=True)
                if label == "間取り":
                    layout = value
                elif label == "築年月":
                    build_year = value
                elif label == "階建":
                    total_floors = value
                elif label == "構造":
                    structure = value
                elif label == "専有面積":
                    area = value
                elif label == "所在地":
                    address = value
                elif label == "交通":
                    station = value
        if not title and price is None:
            continue
        items.append({
            "productId": f"athome-sale-{ward}-{title}-{layout}-{len(items)}",
            "title": title,
            "price": price,
            "address": address,
            "station": station,
            "layout": layout,
            "areaSqm": area,
            "buildingAge": build_year,
            "totalFloors": total_floors,
            "structure": structure,
            "productUrl": link or BASE_URL,
            "source": "athome_sale",
            "shop": "at home 中古マンション",
            "ward": ward,
        })
    return items


async def search_athome_sale(
    client: httpx.AsyncClient,
    ward: str = "渋谷区",
    max_pages: int = 2,
    max_items: int = 100,
) -> list[dict]:
    if ward not in TOKYO_WARDS:
        ward = "渋谷区"
    wurl = TOKYO_WARDS[ward]
    base = f"{BASE_URL}/mansion/chuko/tokyo/{wurl}/list/"
    results: list[dict] = []
    page = 1
    while page <= max_pages and len(results) < max_items:
        url = base if page == 1 else f"{base}page{page}/"
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
        if f"page{page+1}/" not in html:
            break
        page += 1
        await asyncio.sleep(0.5)
    return results
