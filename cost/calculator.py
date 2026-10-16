"""OFFLINE cost and runtime calculator. Never calls an API and needs no key.

    python -m cost.calculator                     # replay saved pilot usage with cost/rates.csv
    python -m cost.calculator --rate-multiplier 2 # every API rate x2: API subtotal doubles, time unchanged

Inputs (all saved under cost/): rates.csv (editable dated prices), usage.csv (billed units per pilot run
and stage), pilot_measurements.json (timings and counts), assumptions.json (editable full-run scenarios).
Output: report.md and report.json.

item_cost = billed_units x price_per_unit; total = sum(item_cost). Prices quoted per million tokens are
divided by 1,000,000. A price that is not known stays "unknown" - it is never treated as zero.
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

COST = Path(__file__).resolve().parent
ITEMS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")


def load_rates(path, multiplier, overrides):
    rates, sources = {}, {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["model"], row["item"])
            price = row["price"].strip()
            if row["provider"] == "typesafe" and overrides.get(row["item"]) is not None:
                price = str(overrides[row["item"]])
            rates[key] = None if price == "" else float(price) / float(row["per_units"]) * multiplier
            sources[key] = {"provider": row["provider"], "checked_on": row["checked_on"], "source": row["source"],
                            "quoted": f"{row['price'] or 'unknown'} {row['currency']} per {int(float(row['per_units'])):,} {row['unit']}s"}
    return rates, sources


def load_usage(path):
    usage = defaultdict(dict)  # (run, stage, provider, model) -> item -> units
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            k = (row["pilot_run"], row["stage"], row["provider"], row["model"])
            usage[k][row["item"]] = int(row["units"])
            if row["item"] == "attempts":
                usage[k]["failed_attempts"] = int(row["failed_attempts"] or 0)
    return usage


def price(rates, model, units_by_item):
    """Return (usd or None if any billed item has an unknown rate, list of unknown items)."""
    total, unknown = 0.0, []
    for item in ITEMS:
        units = units_by_item.get(item, 0)
        if not units:
            continue
        rate = rates.get((model, item))
        if rate is None:
            unknown.append(item)
        else:
            total += units * rate
    return (None if unknown else total), unknown


def fmt_usd(x, digits=4):
    return "unknown" if x is None else f"${x:,.{digits}f}"


def calculate(multiplier=1.0):
    a = json.loads((COST / "assumptions.json").read_text(encoding="utf-8"))
    m = json.loads((COST / "pilot_measurements.json").read_text(encoding="utf-8"))
    rates, sources = load_rates(COST / "rates.csv", multiplier, a["typesafe_rate_override_usd_per_mtok"])
    usage = load_usage(COST / "usage.csv")

    # ---- measured pilot ---------------------------------------------------------------------------
    measured = {}
    for run in ("cold", "warm"):
        rows, api_known, api_unknown_items = [], 0.0, []
        for (r, stage, prov, model), u in sorted(usage.items()):
            if r != run:
                continue
            usd, unknown = price(rates, model, u)
            rows.append({"stage": stage, "provider": prov, "model": model, "attempts": u.get("attempts", 0),
                         "failed_attempts": u.get("failed_attempts", 0),
                         **{i: u.get(i, 0) for i in ITEMS}, "usd": usd, "unknown_rate_items": unknown})
            if usd is None:
                api_unknown_items += [f"{model}:{i}" for i in unknown]
            else:
                api_known += usd
        summary = m["runs"][run]
        completed = m["status_counts"].get("completed", 0)
        wall = summary["end_to_end_wall_seconds"]
        measured[run] = {
            "stages": rows, "api_usd_known": api_known, "api_usd_unknown_items": api_unknown_items,
            "wall_seconds": wall, "stage_seconds": {k: v["seconds"] for k, v in summary["stages"].items()},
            "throughput_rows_per_sec": round(m["rows"] / wall, 2) if wall else None,
            "usd_per_1000_rows_known": api_known / m["rows"] * 1000,
            "usd_per_completed_known": api_known / completed if completed else None,
            "result_cache_hits": m["result_cache_hits"][run],
            "enrich_calls": sum(s["attempts"] for s in rows if s["stage"] == "enrich"),
        }

    # ---- full-run projection ----------------------------------------------------------------------
    cold = {(s["stage"], s["model"]): s for s in measured["cold"]["stages"]}
    enrich = next(s for (st, _), s in cold.items() if st == "enrich")
    texts_pilot = m["distinct_nonempty_texts"]
    per_text = {i: enrich[i] / texts_pilot for i in ITEMS}
    verify = next((s for (st, _), s in cold.items() if st == "verify"), None)
    verified_pilot = m["runs"]["cold"]["stages"]["verify"]["sent_to_model"]
    group = next((s for (st, _), s in cold.items() if st == "group"), None)
    issues_pilot = m["runs"]["cold"]["stages"]["group"]["issues"]
    memo = next((s for (st, _), s in cold.items() if st == "memo"), None)
    enrich_rate = m["runs"]["cold"]["stages"]["enrich"]["completed"] / m["runs"]["cold"]["stages"]["enrich"]["seconds"]
    fr = a["full_run"]

    def project(scenario, texts):
        sc = a["scenarios"][scenario]
        lines = []
        er = 1 + sc["enrich_retry_rate"]
        e_units = {i: per_text[i] * texts * er for i in ITEMS}
        lines.append(("enrich", enrich["provider"], enrich["model"], e_units))
        ar = 1 + sc["anthropic_retry_rate"]
        if verify:
            k = a["verify_sample_reviews"] / verified_pilot * ar
            lines.append(("verify", verify["provider"], verify["model"], {i: verify[i] * k for i in ITEMS}))
        if group:
            k = a["issues"] / issues_pilot * ar
            lines.append(("group", group["provider"], group["model"], {i: group[i] * k for i in ITEMS}))
        if memo:
            k = a["memo_calls"] * ar
            lines.append(("memo", memo["provider"], memo["model"], {i: memo[i] * k for i in ITEMS}))
        by_provider, out = defaultdict(lambda: 0.0), []
        unknown_providers = set()
        for stage, prov, model, units in lines:
            usd, unknown = price(rates, model, units)
            out.append({"stage": stage, "provider": prov, "model": model,
                        **{i: round(units[i]) for i in ITEMS}, "usd": usd})
            if usd is None:
                unknown_providers.add(prov)
            else:
                by_provider[prov] += usd
        workers = a["max_workers"]
        enrich_hours = texts * er / (enrich_rate * max(1, workers * a["parallel_efficiency"])) / 3600
        warnings = []
        for prov, budget in a["budget_usd"].items():
            if prov in unknown_providers:
                warnings.append(f"{prov}: cost unknown (no published rate) - cannot confirm it fits the ${budget:.2f} budget")
            elif by_provider[prov] > budget:
                warnings.append(f"OVER BUDGET: {prov} projected ${by_provider[prov]:.2f} > budget ${budget:.2f}")
        return {"texts_classified": texts, "lines": out, "usd_by_provider": dict(by_provider),
                "unknown_cost_providers": sorted(unknown_providers),
                "enrich_hours_modeled": round(enrich_hours, 2), "workers_modeled": workers, "warnings": warnings}

    projections = {f"{s}_{mode}": project(s, n) for s in a["scenarios"]
                   for mode, n in (("reuse", fr["distinct_nonempty_texts"]), ("no_reuse", fr["nonempty"]))}

    recon = a["typesafe_balance_reconciliation"]
    derived = None
    if all(recon.get(k) is not None for k in ("balance_before_usd", "balance_after_usd", "tokens_between_readings")):
        derived = (recon["balance_before_usd"] - recon["balance_after_usd"]) / recon["tokens_between_readings"] * 1e6

    return {"rate_multiplier": multiplier, "pilot": {k: m[k] for k in ("input", "input_sha256", "rows",
            "distinct_nonempty_texts", "status_counts", "limits")}, "rates": {f"{k[0]}:{k[1]}": {**sources[k],
            "usd_per_unit": v} for k, v in rates.items()}, "measured": measured,
            "per_text_enrich_tokens": {i: round(v, 1) for i, v in per_text.items() if v},
            "enrich_texts_per_second_1_worker": round(enrich_rate, 2), "full_run": fr, "assumptions": a,
            "projections": projections, "typesafe_derived_blended_usd_per_mtok": derived}


def render(r):
    L = []
    p = r["pilot"]
    L += ["# 100-review pilot: cost and runtime calculator", "",
          "Generated offline by `python -m cost.calculator` from saved evidence; no API calls.",
          f"Rate multiplier: {r['rate_multiplier']}", "",
          "## Pilot input", "",
          f"- File `{p['input']}` · SHA-256 `{p['input_sha256']}`",
          f"- Rows {p['rows']} · distinct nonempty texts {p['distinct_nonempty_texts']} · statuses {p['status_counts']}",
          f"- Limits: {p['limits']}", ""]
    L += ["## Rates (editable: `cost/rates.csv`)", "", "| model:item | quoted | checked | source |", "|---|---|---|---|"]
    for k, v in r["rates"].items():
        L.append(f"| {k} | {v['quoted']} | {v['checked_on']} | {v['source']} |")
    for run in ("cold", "warm"):
        mm = r["measured"][run]
        L += ["", f"## Measured {run} run", "",
              f"- End-to-end wall clock **{mm['wall_seconds']} s** · throughput {mm['throughput_rows_per_sec']} rows/s",
              f"- Stage seconds: {mm['stage_seconds']}",
              f"- Result-cache hits: {mm['result_cache_hits']} · enrichment calls: {mm['enrich_calls']}",
              f"- Known API spend **{fmt_usd(mm['api_usd_known'])}**" +
              (f" + unknown-rate items {mm['api_usd_unknown_items']}" if mm["api_usd_unknown_items"] else ""),
              f"- Known cost per 1,000 rows {fmt_usd(mm['usd_per_1000_rows_known'])} · per completed record "
              f"{fmt_usd(mm['usd_per_completed_known'], 6)}", "",
              "| stage | provider | model | attempts | failed | input | cache read | cache write | output | cost |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for s in mm["stages"]:
            L.append(f"| {s['stage']} | {s['provider']} | {s['model']} | {s['attempts']} | {s['failed_attempts']} | "
                     f"{s['input_tokens']:,} | {s['cache_read_input_tokens']:,} | {s['cache_creation_input_tokens']:,} | "
                     f"{s['output_tokens']:,} | {fmt_usd(s['usd'])} |")
        if not mm["stages"]:
            L.append("| (no model calls) | | | 0 | 0 | 0 | 0 | 0 | 0 | $0.0000 |")
    L += ["", "## Full-run projection", "",
          f"Measured enrichment: {r['per_text_enrich_tokens']} tokens per distinct text; "
          f"{r['enrich_texts_per_second_1_worker']} texts/s with 1 worker.",
          f"Full run: {r['full_run']['rows']:,} rows · {r['full_run']['nonempty']:,} nonempty · "
          f"{r['full_run']['empty_quarantined']} empty-text quarantines · {r['full_run']['distinct_nonempty_texts']:,} distinct texts.", ""]
    for name, pr in r["projections"].items():
        L += [f"### {name.replace('_', ' ')} ({pr['texts_classified']:,} texts classified)", "",
              "| stage | model | input | output | cost |", "|---|---|---|---|---|"]
        for ln in pr["lines"]:
            L.append(f"| {ln['stage']} | {ln['model']} | {ln['input_tokens']:,} | {ln['output_tokens']:,} | {fmt_usd(ln['usd'], 2)} |")
        L += ["", f"- Known API cost by provider: { {k: round(v, 2) for k, v in pr['usd_by_provider'].items()} }",
              f"- Unknown-cost providers: {pr['unknown_cost_providers'] or 'none'}",
              f"- Enrichment time (modeled, {pr['workers_modeled']} workers): **{pr['enrich_hours_modeled']} h**"]
        L += [f"- ⚠ {w}" for w in pr["warnings"]] + [""]
    L += ["## Controls", "",
          f"- Budgets: {r['assumptions']['budget_usd']} · output-token caps per call: {r['assumptions']['output_token_cap_per_call']}",
          f"- Max workers {r['assumptions']['max_workers']} · declared max fallback fraction {r['assumptions']['max_fallback_fraction']}",
          f"- Jev derived blended rate from balance reconciliation: {r['typesafe_derived_blended_usd_per_mtok'] or 'not yet reconciled'}",
          "- Local compute: unknown (laptop; not metered) - reported separately from API spend, never as zero."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rate-multiplier", type=float, default=1.0)
    ap.add_argument("--out", default=None, help="default: cost/report.md (multiplier 1) or cost/report_x<m>.md")
    args = ap.parse_args()
    r = calculate(args.rate_multiplier)
    stem = "report" if args.rate_multiplier == 1 else f"report_x{args.rate_multiplier:g}"
    out = Path(args.out) if args.out else COST / f"{stem}.md"
    out.write_text(render(r), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    for run in ("cold", "warm"):
        mm = r["measured"][run]
        print(f"{run}: wall {mm['wall_seconds']}s, known API {fmt_usd(mm['api_usd_known'])}, "
              f"unknown-rate items {mm['api_usd_unknown_items']}, enrich calls {mm['enrich_calls']}")
    for name, pr in r["projections"].items():
        print(f"{name}: {pr['usd_by_provider']} unknown={pr['unknown_cost_providers']} time={pr['enrich_hours_modeled']}h")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
