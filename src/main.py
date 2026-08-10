"""
Japan Property Market — 中古マンション売買の2サイト横断比較（SUUMO + at home）.

東京23区の中古マンション売買物件を2サイトから収集し、同じ駅・同じ間取りの
販売価格を横断比較できるデータセットを出力します。
"""

from __future__ import annotations

import asyncio
import json
import sys
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


async def run(actor_input: dict) -> list[dict]:
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
