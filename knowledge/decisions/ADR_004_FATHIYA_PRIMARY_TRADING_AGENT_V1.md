# ADR 004: FATHIYA Primary Trading Agent v1

## Status

Accepted for local paper execution. Live broker execution is not yet approved
or implemented.

## Decision

The first specialist execution agent is a trading agent with two independent
speeds:

1. A deterministic market, prediction, risk, paper-fill, and receipt loop runs
   every second.
2. Slower OpenRouter, Hugging Face, research, and evaluation work may update a
   strategy signal asynchronously, but may never block the one-second risk
   loop.

Every cycle records the observed tick, prediction, risk result, optional fill,
portfolio state, latency, and a unique receipt. The first implementation is
paper-only, long-only, and uses a deterministic synthetic feed until a broker
market-data connector is selected.

## Live Activation Gates

Live execution requires all of the following:

- a named broker or exchange and market;
- a paper-account proof using the broker's real market-data and order APIs;
- trade-only credentials with withdrawal permission disabled;
- explicit symbol, order, position, and daily-loss limits;
- an emergency stop and reconciliation proof;
- explicit action-time approval before enabling live mode.

Changing `FATHIYA_TRADING_MODE` away from `paper` blocks the agent in v1.

## Consequences

- The agent can be measured and improved now without risking funds.
- Heavy AI models can inform strategy without controlling timing or bypassing
  deterministic risk checks.
- Broker credentials and live-order code remain a separate reviewed change.
