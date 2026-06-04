# FATHIYA Trading Account Setup

Do not paste broker passwords, API secrets, seed phrases, or withdrawal keys
into chat, source control, browser-exposed environment variables, or receipts.

## Required Operator Choices

Before implementing the first real broker connector, provide:

- broker or exchange name;
- market type, such as crypto spot, crypto futures, or US equities;
- first symbols to allow;
- paper or testnet account availability;
- maximum order notional;
- maximum total position notional;
- daily loss limit;
- whether short selling or leverage must remain disabled.

## Credential Requirements

Create a dedicated automation account or API key with:

- trading permission only;
- withdrawal and transfer permissions disabled;
- IP allowlisting enabled when the provider supports it;
- the smallest practical symbol and account scope;
- paper or testnet access before any live activation.

Store credentials only on the local runtime host using the provider-specific
environment variables or an approved local secret manager. The website must
never receive or expose broker secrets.

## Activation Order

1. Connect read-only market data and account status.
2. Reconcile balances and positions without submitting orders.
3. Run the one-second agent against the provider's paper or testnet order API.
4. Verify fills, rejects, latency, daily-loss stop, emergency stop, and
   receipts.
5. Request explicit action-time approval before enabling any live order path.

Current state: no broker or exchange account is configured. The local agent
runs against a synthetic feed and paper ledger only.
