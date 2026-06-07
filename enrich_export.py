#!/usr/bin/env python3
"""Enrich the scraper DB with EGX-collected full-life performance stats and export
a data module (data/data.js) that the static web app reads.

Real data sources used here:
  * rights_issues  -> the scraper's seeded master list (12 instruments, 2021-2025)
  * egx_performance-> full-life trading stats pulled from EGX's "Historical Statistics
                      > Stocks Data" tool (egx.com.eg) via a real browser session, for
                      the 5 rights instruments EGX currently exposes (2026 round).

EGX's public site exposes, per instrument, only: a latest-session OHLC line + the
high/low/volume/value/#trades aggregated over the chosen period, plus a chart *image*.
It does NOT expose an extractable per-day OHLCV series for these short-lived rights,
so the app shows the official EGX performance envelope (range + liquidity), not a
fabricated daily line.
"""
from __future__ import annotations
import json, sqlite3, datetime, pathlib

ROOT = pathlib.Path(__file__).parent
DB = ROOT / "egx_rights.sqlite"

# --- 5 rights instruments EGX currently exposes, with REAL full-life stats ----
# (captured from egx.com.eg Historical Statistics > Stocks Data, period = 3 years,
#  which fully contains each instrument's short separate-trading window)
EGX_LIVE = [
    dict(isin="EGS924G1C014", parent_ticker="ASPI", rights_ticker="ASPI_r3.CA", market="Main", round=3,
         company_name_en="Aspire Capital Holding for Financial Investments (rights, round 3)",
         company_name_ar="حق اكتتاب شركة اسباير كابيتال القابضة للاستثمارات المالية-3",
         ref_date="2026-06-03", ref_close=0.110, high=0.176, low=0.056,
         volume=825_296_060, value=91_457_090.68, trades=5_539),
    dict(isin="EGS924D1C017", parent_ticker="KRDI", rights_ticker="KRDI_r1.CA", market="Main", round=1,
         company_name_en="Al Khair River for Development, Agriculture Investment & Environmental Services (rights, round 1)",
         company_name_ar="حق اكتتاب شركة نهر الخير للتنمية والاستثمار الزراعي والخدمات-1",
         ref_date="2026-04-14", ref_close=0.225, high=0.235, low=0.188,
         volume=825_478_964, value=177_415_283.03, trades=12_029),
    dict(isin="EGS924E1C016", parent_ticker="SVCE", rights_ticker="SVCE_r1.CA", market="Main", round=1,
         company_name_en="South Valley Cement (rights, round 1)",
         company_name_ar="حق اكتتاب شركة جنوب الوادى للاسمنت-1",
         ref_date="2026-05-04", ref_close=4.100, high=4.400, low=1.870,
         volume=19_398_055, value=52_607_217.42, trades=6_649),
    dict(isin="EGS924C1C018", parent_ticker="ARAB", rights_ticker="ARAB_r2.CA", market="Main", round=2,
         company_name_en="Arab Developers Holding (rights, round 2)",
         company_name_ar="حق اكتتاب شركة المطورون العرب القابضة - 2",
         ref_date="2026-04-05", ref_close=0.059, high=0.083, low=0.059,
         volume=3_633_218_221, value=243_193_748.72, trades=11_128),
    dict(isin="EGS924F1C015", parent_ticker="AMES", rights_ticker="AMES_r2.CA", market="Main", round=2,
         company_name_en="Alexandria New Medical Center (rights, round 2)",
         company_name_ar="حق اكتتاب شركة الاسكندرية للخدمات الطبية-المركز الطبي جديد-2",
         ref_date="2026-05-04", ref_close=50.050, high=52.700, low=43.000,
         volume=1_483_994, value=67_720_072.20, trades=5_642),
]

# Real per-right opening-price anchors found in primary disclosures (seed notes).
SEED_ANCHORS = {
    "EGX-FWRY-202104": dict(open_price=20.29, note="Opening price of the right on its first separate-trading day (20 Apr 2021)."),
    "EGX-MNHD-202202": dict(open_price=1.392, note="Opening price of the right (closing value set at EGP 152.4m)."),
    "EGX-DSCW-202206": dict(note="Subscription up to 250% of holdings; cash-paid, no issuance fees."),
}


def enrich(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS egx_performance (
        isin TEXT PRIMARY KEY,
        rights_ticker TEXT, ref_date TEXT, ref_close REAL,
        period_high REAL, period_low REAL,
        total_volume REAL, total_value REAL, total_trades INTEGER,
        period_label TEXT, source TEXT, captured_at TEXT
    );
    """)
    now = "2026-06-07"
    for r in EGX_LIVE:
        # master row
        conn.execute("""INSERT INTO rights_issues
            (isin, rights_ticker, parent_ticker, company_name_en, company_name_ar, market)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(isin) DO UPDATE SET
              rights_ticker=excluded.rights_ticker, parent_ticker=excluded.parent_ticker,
              company_name_en=excluded.company_name_en, company_name_ar=excluded.company_name_ar,
              market=excluded.market""",
            (r["isin"], r["rights_ticker"], r["parent_ticker"],
             r["company_name_en"], r["company_name_ar"], r["market"]))
        conn.execute("""INSERT OR REPLACE INTO egx_performance VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["isin"], r["rights_ticker"], r["ref_date"], r["ref_close"],
             r["high"], r["low"], r["volume"], r["value"], r["trades"],
             "Full separate-trading life (EGX 3-year window)", "egx.com.eg/StocksData", now))
    conn.commit()


def export(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row
    rights = [dict(r) for r in conn.execute("SELECT * FROM rights_issues")]
    perf = {r["isin"]: dict(r) for r in conn.execute("SELECT * FROM egx_performance")}
    live_meta = {r["isin"]: r for r in EGX_LIVE}

    insts = []
    for ri in rights:
        isin = ri["isin"]
        p = perf.get(isin)
        anchor = SEED_ANCHORS.get(isin, {})
        # derive a year for grouping
        d = ri.get("first_trading_day") or ri.get("listing_decision_date")
        if p and not d:
            d = live_meta.get(isin, {}).get("ref_date")
        year = (d or "")[:4] or "—"
        insts.append({
            "isin": isin,
            "rightsTicker": ri.get("rights_ticker"),
            "parentTicker": ri.get("parent_ticker"),
            "nameEn": ri.get("company_name_en"),
            "nameAr": ri.get("company_name_ar"),
            "market": ri.get("market"),
            "round": live_meta.get(isin, {}).get("round"),
            "firstDay": ri.get("first_trading_day"),
            "lastDay": ri.get("last_trading_day"),
            "decisionDate": ri.get("listing_decision_date"),
            "numRights": ri.get("num_rights"),
            "parValue": ri.get("par_value"),
            "capitalBefore": ri.get("capital_before"),
            "capitalAfter": ri.get("capital_after"),
            "openAnchor": anchor.get("open_price"),
            "anchorNote": anchor.get("note"),
            "year": year,
            "dataStatus": "egx_live" if p else "metadata_only",
            "perf": ({
                "refDate": p["ref_date"], "refClose": p["ref_close"],
                "high": p["period_high"], "low": p["period_low"],
                "volume": p["total_volume"], "value": p["total_value"],
                "trades": p["total_trades"], "source": p["source"],
                "periodLabel": p["period_label"],
            } if p else None),
        })

    # order: live (EGX) first, then by year desc
    insts.sort(key=lambda x: (0 if x["dataStatus"] == "egx_live" else 1, x["year"]), reverse=False)
    insts.sort(key=lambda x: (0 if x["dataStatus"] == "egx_live" else 1, -(int(x["year"]) if x["year"].isdigit() else 0)))

    payload = {
        "generatedAt": "2026-06-07",
        "instrumentCount": len(insts),
        "liveCount": sum(1 for i in insts if i["dataStatus"] == "egx_live"),
        "instruments": insts,
    }
    out = ROOT / "data" / "data.js"
    out.write_text("window.RIGHTS_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";",
                   encoding="utf-8")
    # also a plain json for reuse
    (ROOT / "data" / "rights.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"exported {len(insts)} instruments ({payload['liveCount']} with live EGX stats) -> {out}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    enrich(conn)
    export(conn)
    conn.close()
