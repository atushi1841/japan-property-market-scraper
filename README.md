# Japan Property Market — 2-Site Cross-Shop Comparison (Used Condo Sale)

**Compare Tokyo 23-ward used condominium sale prices across Japan's top 2 property portals in a single dataset.**

Scrapes used condo sale listings from **SUUMO (スーモ) 中古マンション** — Japan's #1 property portal — and **at home (アットホーム) 中古マンション** — the #2 portal. Each item is tagged with its `source` so you can compare sale prices for the same station/layout across portals.

> 🇨🇳 中文版: [日本二手房市场](https://apify.com/fruitful_quintessence) / 🇰🇷 한국어판: [일본 부동산 마켓](https://apify.com/fruitful_quintessence)

## Why this is useful

- **Cross-portal price comparison** — the same condo near Shibuya station often differs by 5-15% between portals
- **Market research** — track Tokyo condo price trends by ward over time
- **Investment analysis** — identify underpriced/overpriced properties before buying
- **Relocation planning** — find the best-priced property before moving to Japan

## Input

| Field | Type | Default | Description |
|---|---|---|---|
| `ward` | select | `渋谷区` | Tokyo 23 wards (千代田区, 港区, 新宿区, 渋谷区, 世田谷区, etc.) |
| `maxItems` | integer | 100 | Max items to collect |
| `maxPages` | integer | 2 | Max pages per source |
| `sources` | string | `suumo,athome` | Comma-separated source list |
| `proxyConfiguration` | object | — | Apify proxy |

## Output Sample

```json
{
  "productId": "suumo-sale-渋谷区-メゾンジャルダン-ワンルーム-0",
  "title": "メゾンジャルダン",
  "price": 29800000,
  "address": "東京都渋谷区千駄ヶ谷３-8-4",
  "station": "東京メトロ副都心線「北参道」徒歩5分",
  "layout": "ワンルーム",
  "areaSqm": "28.78m²",
  "buildingAge": "1968年1月",
  "source": "suumo_sale",
  "shop": "SUUMO 中古マンション",
  "ward": "渋谷区"
}
```

The `source` + `shop` fields let you compare the same building across portals.

## Use Cases

- **Cross-portal arbitrage** — find the same building listed cheaper on another portal
- **Price trend tracking** — schedule daily runs to monitor ward-level price movements
- **Investment research** — one dataset covering both major portals

## Pricing

Pay-per-event — **$0.00005/run start + $0.002/item**.

## Data Source

Public used condo listings from SUUMO and at home (price, address, station, layout, area, building age).

## Connect

Connect to your workflow via **Apify Connectors**: Google Sheets, Slack, or webhooks — automate price monitoring without code.
