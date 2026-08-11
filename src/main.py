"""
Japan Property Market — 中古マンション売買の2サイト横断比較（SUUMO + at home）.

東京23区の中古マンション売買物件を2サイトから収集し、同じ駅・同じ間取りの
販売価格を横断比較できるデータセットを出力します。
"""

from __future__ import annotations

import asyncio
import datetime
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from apify import Actor
except ImportError:
    Actor = None

from sources.suumo_sale import search_suumo_sale
from sources.athome_sale import search_athome_sale

SOURCES = {
    "suumo": search_suumo_sale,
    "athome": search_athome_sale,
}


def _norm_key(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


async def run(actor_input: dict) -> list[dict]:
    stats_mode = actor_input.get("statsMode", False)
    ward = str(actor_input.get("ward", "渋谷区")).strip()
    max_items = int(actor_input.get("maxItems", 100))
    max_pages = int(actor_input.get("maxPages", 2))
    sources_str = str(actor_input.get("sources", "suumo,athome"))
    enabled = [s.strip() for s in sources_str.split(",") if s.strip() in SOURCES]

    import httpx

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        results: list[dict] = []
        for name in enabled:
            fn = SOURCES[name]
            try:
                items = await fn(
                    client,
                    ward=ward,
                    max_pages=max_pages,
                    max_items=max_items,
                )
                results.extend(items)
            except Exception as e:
                print(f"Source {name} error: {e}")

    if stats_mode:
        keyword = str(actor_input.get("statsKeyword") or "").strip()
        filtered = []
        for item in results:
            if keyword and _norm_key(keyword) not in _norm_key(item.get("title", "")):
                continue
            try:
                price = int(item.get("price"))
            except (TypeError, ValueError):
                continue
            filtered.append((item, price))
        count = len(filtered)
        if count:
            prices = [price for _, price in filtered]
            price_min = min(prices)
            price_max = max(prices)
            price_avg = int(sum(prices) / count)
            s = sorted(prices)
            if count % 2:
                price_median = s[count // 2]
            else:
                price_median = int((s[count // 2 - 1] + s[count // 2]) / 2)
            sample_items = [
                {
                    "title": item.get("title"),
                    "price": price,
                    "detailUrl": item.get("detailUrl"),
                    "shop": item.get("shop"),
                }
                for item, price in filtered[:3]
            ]
        else:
            price_min = None
            price_max = None
            price_avg = None
            price_median = None
            sample_items = []
        collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        stats_result = {
            "statsType": "japan-property-price",
            "keyword": keyword,
            "count": count,
            "priceMin": price_min,
            "priceMax": price_max,
            "priceAvg": price_avg,
            "priceMedian": price_median,
            "sampleItems": sample_items,
            "collectedAt": collected_at,
        }
        if Actor is not None:
            await Actor.push_data(stats_result)
        else:
            print(json.dumps(stats_result, ensure_ascii=False))
        return results

    if Actor is not None:
        for item in results:
            await Actor.push_data(item)
        print(f"Collected {len(results)} items from {len(enabled)} sources")
    return results


async def main() -> None:
    if Actor is not None:
        async with Actor:
            actor_input = await Actor.get_input() or {}
            await run(actor_input)
    else:
        raw = sys.stdin.read().strip()
        actor_input = json.loads(raw) if raw else {}
        results = await run(actor_input)
        for item in results:
            print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
