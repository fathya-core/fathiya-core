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
paper-only and long-only. It observes public Coinbase spot data by default,
evaluates eligible predictions against the next tick, and keeps broker and
engine state isolated per symbol.

Provider failure activates a labeled synthetic fallback for observability only.
The risk engine blocks fills and prediction scoring on fallback ticks so
simulated prices cannot be mistaken for market evidence.

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
- Prediction quality is recorded from observed outcomes instead of claimed by
  the model.
- Heavy AI models can inform strategy without controlling timing or bypassing
  deterministic risk checks.
- Broker credentials and live-order code remain a separate reviewed change.
