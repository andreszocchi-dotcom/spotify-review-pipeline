"""Claude calls for the verify, group and memo roles.

Every attempt (including failures) is written to the `calls` table. A dollar ledger, priced from
cost/rates.csv, reserves the worst case for each call before dispatch and refuses work once the
cap would be exceeded. Transient errors get bounded exponential backoff with jitter; output that
fails validation gets exactly one retry.
"""

import csv
import json
import random
import time

import anthropic

from pipeline.common import ROOT, log_call, now

HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"
MAX_TRANSIENT_ATTEMPTS = 4
MAX_INVALID_ATTEMPTS = 2
RATES_CSV = ROOT / "cost" / "rates.csv"


class BudgetStop(Exception):
    pass


class InvalidOutput(ValueError):
    pass


def load_rates(path=RATES_CSV):
    """{(model, item): usd_per_unit} for rows with a known price."""
    rates = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["price"].strip():
                rates[(row["model"], row["item"])] = float(row["price"]) / float(row["per_units"])
    return rates


def call_usd(rates, model, usage):
    """Mutually exclusive billing items: uncached input, cache reads, cache writes, output."""
    return sum(units * rates.get((model, item), 0.0) for item, units in (
        ("input_tokens", usage.get("input_tokens") or 0),
        ("cache_read_input_tokens", usage.get("cache_read_input_tokens") or 0),
        ("cache_creation_input_tokens", usage.get("cache_creation_input_tokens") or 0),
        ("output_tokens", usage.get("output_tokens") or 0)))


class Claude:
    def __init__(self, con, run_id, phase, usd_cap=None):
        self.client = anthropic.Anthropic(max_retries=0, timeout=120)
        self.con, self.run_id, self.phase = con, run_id, phase
        self.rates = load_rates()
        self.usd_cap = usd_cap
        spent = 0.0
        for model, i, o, cr, cw in con.execute("""SELECT model, input_tokens, output_tokens, cache_read_input_tokens,
                cache_creation_input_tokens FROM calls WHERE provider = 'anthropic'"""):
            spent += call_usd(self.rates, model, {"input_tokens": i, "output_tokens": o,
                                                  "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw})
        self.spent_usd = spent

    def _reserve(self, model, input_estimate, max_tokens):
        worst = call_usd(self.rates, model, {"input_tokens": input_estimate, "output_tokens": max_tokens})
        if self.usd_cap is not None and self.spent_usd + worst > self.usd_cap:
            raise BudgetStop(f"Anthropic cap ${self.usd_cap:.2f} reached (spent ${self.spent_usd:.4f}, next call up to ${worst:.4f})")

    def json_call(self, *, role, system, user, schema, review_ids, validate, max_tokens=4000, model=HAIKU,
                  label_config="n/a", effort="low"):
        """Return validate(parsed_json). Raises BudgetStop, InvalidOutput (after one retry) or the last API error."""
        invalid, attempt, last = 0, 0, None
        while attempt < MAX_TRANSIENT_ATTEMPTS:
            attempt += 1
            self._reserve(model, len(system + user) // 2, max_tokens)  # chars/2 overestimates tokens
            started, t0 = now(), time.perf_counter()
            usage, request_id = {}, None
            try:
                r = self.client.messages.create(
                    model=model, max_tokens=max_tokens, system=system,
                    messages=[{"role": "user", "content": user}],
                    output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}})
                request_id = r._request_id
                usage = {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens,
                         "cache_read_input_tokens": r.usage.cache_read_input_tokens or 0,
                         "cache_creation_input_tokens": r.usage.cache_creation_input_tokens or 0}
                self.spent_usd += call_usd(self.rates, model, usage)
                if r.stop_reason != "end_turn":
                    raise InvalidOutput(f"stop_reason={r.stop_reason}")
                text = next(b.text for b in r.content if b.type == "text")
                result = validate(json.loads(text))
            except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as e:
                last = e
                self._log(role, review_ids, model, effort, "failed", label_config, started, t0, attempt, usage,
                          f"{type(e).__name__}: {str(e)[:200]}", request_id)
                time.sleep(min(30, 2 ** attempt) * (1 - 0.25 * random.random()))
                continue
            except anthropic.APIStatusError as e:
                self._log(role, review_ids, model, effort, "failed", label_config, started, t0, attempt, usage,
                          f"{type(e).__name__}: {str(e)[:200]}", request_id)
                raise
            except (InvalidOutput, ValueError, KeyError, StopIteration) as e:
                last = InvalidOutput(f"invalid_output: {e}")
                self._log(role, review_ids, model, effort, "failed", label_config, started, t0, attempt, usage, str(last), request_id)
                invalid += 1
                if invalid >= MAX_INVALID_ATTEMPTS:
                    raise last
                continue
            self._log(role, review_ids, model, effort, "succeeded", label_config, started, t0, attempt, usage, None, request_id)
            return result
        raise last

    def _log(self, role, review_ids, model, effort, outcome, label_config, started, t0, attempt, usage, error, request_id):
        log_call(self.con, run_id=self.run_id, role=role, provider="anthropic", review_ids=review_ids, model=model,
                 settings={"thinking": "adaptive", "effort": effort}, phase=self.phase, outcome=outcome, label_config=label_config, started=started,
                 seconds=time.perf_counter() - t0, attempt=attempt, input_tokens=usage.get("input_tokens"),
                 output_tokens=usage.get("output_tokens"), cache_read=usage.get("cache_read_input_tokens"),
                 cache_write=usage.get("cache_creation_input_tokens"), error=error, request_id=request_id)
        self.con.commit()
