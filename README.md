# EGX Rights-Issue Performance Tracker

A web app that shows **every EGX subscription-right that traded as a separate instrument
since April 2021**, one by one, with how each performed over the window it was tradable.

Built from the bundled `egx_rights_scraper` (master list) + **live stats pulled from EGX's
own Historical-Statistics tool via a real browser session**.

## What you see

- **17 rights instruments** (2021 → 2026), each shown separately with its ISIN, rights
  ticker, market segment and separate-trading window.
- **5 instruments carry live EGX trading stats** — the rights EGX currently exposes in its
  *Market Data → Historical Statistics → Stocks Data* tool:

  | Right | Ticker | ISIN | Range (low–high) | Rights traded | Value (EGP) |
  |-------|--------|------|------------------|---------------|-------------|
  | Aspire Capital (r3) | `ASPI_r3.CA` | EGS924G1C014 | 0.056 – 0.176 | 825.3M | 91.5M |
  | Al Khair River (r1) | `KRDI_r1.CA` | EGS924D1C017 | 0.188 – 0.235 | 825.5M | 177.4M |
  | South Valley Cement (r1) | `SVCE_r1.CA` | EGS924E1C016 | 1.870 – 4.400 | 19.4M | 52.6M |
  | Arab Developers (r2) | `ARAB_r2.CA` | EGS924C1C018 | 0.059 – 0.083 | 3.63B | 243.2M |
  | Alex New Medical (r2) | `AMES_r2.CA` | EGS924F1C015 | 43.0 – 52.7 | 1.48M | 67.7M |

- **12 instruments** (Fawry, Arab Dairy/Panda, Madinet Nasr, Dice, Al Tawfeek, Medical
  Packaging, ADIB, Beltone, M.B Engineering, Integrated Engineering, Cooper, ICMI) come
  from the scraper's verified master list — trading windows + capital-increase economics.

## Why the live set is only the price *envelope*, not a daily line

This was the hard part, and the README is honest about it. For these short-lived rights:

- The **server-side scrapers are geo-blocked** (EGX/MCDR/FRA only answer Egyptian IPs) and
  TradingView's old history endpoint is dead and never carried the rights instruments.
- EGX's public site has **no dated EOD cross-section** (`prices.aspx?date=` is ignored) and
  archives only *today's* daily report.
- EGX's **Historical Statistics → Stocks Data** tool *does* index the rights instruments
  (in Arabic, "حق اكتتاب …"), but it returns a **period high/low + total volume/value/#trades
  + a chart image** — **not** a downloadable per-day OHLCV series — and only looks back 3 years.

So the app shows each live right's **real trading range and liquidity over its full
separate-trading life** (the most granular figure EGX publishes), instead of inventing a
daily series. A true day-by-day chart would need a paid vendor feed (EODHD / Refinitiv /
Argaam / Mubasher Pro) or a broker terminal export — drop that into `egx_performance` and the
app upgrades automatically.

## Run it

```bash
cd C:\Users\acer\egx-rights-tracker
python -m http.server 8902
# open http://127.0.0.1:8902/index.html
```

It's a static page — you can also just open `index.html` directly.

## Rebuild / extend the data

```bash
python enrich_export.py          # rebuilds data/data.js + data/rights.json from egx_rights.sqlite
```

- `egx_rights.sqlite` — `rights_issues` (master list) + `egx_performance` (live EGX stats).
- To add a real **daily series** for any instrument, insert daily bars into a `daily_prices`
  table (the scraper's schema already defines it) and extend `enrich_export.py` to emit them;
  the card/modal can then render a true daily chart.

## Files

| File | What |
|------|------|
| `index.html` | the app (self-contained: layout, styling, logic) |
| `data/data.js` | generated data module the app reads |
| `data/rights.json` | same data as plain JSON |
| `egx_rights.sqlite` | source DB (scraper seed + EGX-collected stats) |
| `enrich_export.py` | adds EGX stats to the DB and regenerates the data module |
