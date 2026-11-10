# nse-algo

A test-first, paper-only harness for exploring NSE trading-system controls. **This repository does not contain a trading strategy, broker integration, live order submission, or evidence of profitability.**

## Entry limits implemented

The initial rule set is deliberately narrow:

- Use completed 5-minute bars, on the Asia/Kolkata (IST) exchange clock.
- Reject new entries before 10:00 IST and at/after 15:30 IST.
- Allow at most 2 new entry orders from 10:00 to 12:59 IST and at most 2 from 13:00 to 15:29 IST.
- Allow at most 1 new entry per completed 5-minute bar.
- Opening entries consume quota when reserved, even if an external submission later fails; this favors avoiding duplicate retries. Exits are outside this entry policy and must remain available for risk reduction.

The limits are software guardrails, not a recommendation to place trades. The policy keeps state in memory and is only suitable for a single-process test/paper harness. A real system would need durable, atomic state and independent broker-side controls before any live use.

## Run tests

```bash
python -m pip install pytest
python -m pytest -q
```

Tests use synthetic timestamps only to check policy behavior. They do not measure or imply strategy performance. No market data or broker API is used.

## Next steps before any strategy work

1. Confirm the exact instrument/asset class, broker, exchange segment, account risk budget, and data source.
2. Confirm broker fees, taxes, spread, slippage, order/quantity limits, API limits, and market calendar from current official documentation.
3. Add validated historical-data ingestion and point-in-time safeguards; keep secrets and market data out of Git.
4. Add a backtest harness with fees, spread, slippage, walk-forward evaluation, and a simple benchmark. Report only reproducible results from real data.
5. Add risk limits and a kill switch, then paper trade and review results. Keep live execution disabled unless explicitly approved and independently reviewed.

All market, cost, and operational assumptions remain unverified until documented and checked against the selected broker and exchange.
