// FATHIYA CORE — Crypto Intelligence MCP Tools v0
// قاعدة: لا buy/sell/enter/exit — فقط سيناريوهات ومخاطر وإشارات

import type { MCPToolDefinition, MCPToolResult, CoinCard, SignalCard } from "../types.ts";
import { runQualityGate, validateSignalCard } from "../utils/validator.ts";
import { MCP_CONFIG } from "../config.ts";

export const CRYPTO_TOOLS: MCPToolDefinition[] = [
  {
    name: "crypto_create_signal_card",
    description:
      "إنشاء Signal Card من خبر أو حدث. لا ينتج buy/sell. ينتج سيناريوهات وشروط إبطال ومخاطر مخفية.",
    inputSchema: {
      type: "object",
      properties: {
        source: { type: "string", description: "مصدر الخبر" },
        asset: { type: "string", description: "العملة أو الأصل" },
        sector: { type: "string", description: "القطاع: Bitcoin, Ethereum, DeFi, RWA, Macro, إلخ" },
        event_type: { type: "string", description: "نوع الحدث" },
        signal_direction: { type: "string", description: "supportive | negative | mixed | unclear | noise" },
        time_horizon: { type: "string", description: "immediate | short | medium | long" },
        impact_score: { type: "number", description: "درجة التأثير (0-10)" },
        confidence_score: { type: "number", description: "درجة الثقة (0-1)" },
        what_changed: { type: "string", description: "ماذا تغيّر" },
        what_did_not_change: { type: "string", description: "ماذا لم يتغيّر" },
        bullish_scenario: { type: "string", description: "سيناريو إيجابي" },
        bearish_scenario: { type: "string", description: "سيناريو سلبي" },
        invalidation_conditions: { type: "array", items: { type: "string" }, description: "شروط الإبطال" },
        hidden_risk: { type: "string", description: "الخطر المخفي" },
        bias_traps: { type: "array", items: { type: "string" }, description: "فخاخ التحيز" },
        next_data_needed: { type: "array", items: { type: "string" }, description: "بيانات مطلوبة" },
        decision_boundary: { type: "string", description: "حدود القرار" },
      },
      required: ["source", "asset", "sector", "signal_direction", "impact_score", "confidence_score", "what_changed", "invalidation_conditions", "hidden_risk"],
    },
  },
  {
    name: "crypto_get_coin_card",
    description: "جلب بطاقة عملة بالرمز (BTC, ETH, SOL, إلخ)",
    inputSchema: {
      type: "object",
      properties: { symbol: { type: "string", description: "رمز العملة" } },
      required: ["symbol"],
    },
  },
  {
    name: "crypto_list_watchlist",
    description: "قائمة المراقبة الحالية — ليست توصيات، فقط أصول تحت المراقبة",
    inputSchema: {
      type: "object",
      properties: {
        status: { type: "string", description: "watching | cooling | invalidated | high_noise | needs_data" },
      },
      required: [],
    },
  },
  {
    name: "crypto_run_quality_gate",
    description: "تشغيل Quality Gate على مخرج كريبتو. يمنع أوامر التداول المباشرة.",
    inputSchema: {
      type: "object",
      properties: { content: { type: "string", description: "المحتوى المراد فحصه" } },
      required: ["content"],
    },
  },
  {
    name: "crypto_get_narrative_map",
    description: "جلب خريطة السرديات الحالية: Bitcoin ETF, AI+Crypto, RWA, DePIN, إلخ",
    inputSchema: { type: "object", properties: {}, required: [] },
  },
];

export async function handleCryptoTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const timestamp = new Date().toISOString();

  switch (toolName) {
    case "crypto_create_signal_card": {
      const cardData = params as Partial<SignalCard>;
      const gateResult = validateSignalCard(cardData);

      if (!gateResult.passed) {
        return {
          success: false, tool: toolName, timestamp,
          error: gateResult.blocked_reason ?? "Signal Card failed Quality Gate",
          quality_gate_passed: false,
          quality_warnings: [...gateResult.missing_fields, ...gateResult.unsafe_content, ...gateResult.warnings],
          requires_approval: true,
        };
      }

      const newCard: Partial<SignalCard> = {
        ...cardData,
        id: `signal_${Date.now()}`,
        timestamp,
        status: "draft",
        invalidation_conditions: (cardData.invalidation_conditions as string[]) ?? [],
        bias_traps: (cardData.bias_traps as string[]) ?? [],
        next_data_needed: (cardData.next_data_needed as string[]) ?? [],
      };

      return {
        success: true, tool: toolName, timestamp,
        data: newCard,
        quality_gate_passed: true,
        requires_approval: true, // كل Signal Card تحتاج Approval
        receipt_id: `receipt_${Date.now()}`,
      };
    }

    case "crypto_get_coin_card": {
      const symbol = String(params["symbol"] ?? "").toUpperCase();
      if (!symbol) return { success: false, tool: toolName, timestamp, error: "Missing required field: symbol" };

      // v0 static coin cards for major assets
      const coinCards: Record<string, Partial<CoinCard>> = {
        BTC: {
          symbol: "BTC", name: "Bitcoin", sector: "Bitcoin", chain: "Bitcoin",
          market_role: "Macro/liquidity/risk-on proxy",
          main_narrative: "Store of value, institutional adoption, ETF flows",
          macro_sensitivity: "high", status: "draft",
        },
        ETH: {
          symbol: "ETH", name: "Ethereum", sector: "Ethereum", chain: "Ethereum",
          market_role: "L2/ecosystem/fees/staking",
          main_narrative: "Smart contract platform, L2 ecosystem, staking yield",
          macro_sensitivity: "high", status: "draft",
        },
        SOL: {
          symbol: "SOL", name: "Solana", sector: "Solana", chain: "Solana",
          market_role: "throughput/memecoin/liquidity cycle",
          main_narrative: "High throughput, memecoin activity, DeFi growth",
          macro_sensitivity: "medium", status: "draft",
        },
      };

      const card = coinCards[symbol];
      if (!card) {
        return {
          success: true, tool: toolName, timestamp,
          data: { symbol, note: "No static card. Wire to knowledge/crypto/coin-cards/ for live data." },
          quality_gate_passed: true, requires_approval: false,
        };
      }

      return { success: true, tool: toolName, timestamp, data: card, quality_gate_passed: true, requires_approval: false };
    }

    case "crypto_list_watchlist": {
      const status = params["status"] as string | undefined;
      return {
        success: true, tool: toolName, timestamp,
        data: {
          status_filter: status ?? "all",
          source: "knowledge/crypto/watchlist.json",
          items: [],
          note: "v0: wire to knowledge/crypto/watchlist.json for live data",
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }

    case "crypto_run_quality_gate": {
      const content = String(params["content"] ?? "");
      const gateResult = runQualityGate(content);
      return {
        success: true, tool: toolName, timestamp,
        data: gateResult,
        quality_gate_passed: gateResult.passed,
        requires_approval: gateResult.needs_human_review,
      };
    }

    case "crypto_get_narrative_map": {
      return {
        success: true, tool: toolName, timestamp,
        data: {
          narratives: [
            { name: "Bitcoin ETF / liquidity", status: "active", assets: ["BTC"], risk: "narrative exhaustion" },
            { name: "Fed / rates / dollar", status: "active", assets: ["BTC", "ETH"], risk: "macro reversal" },
            { name: "AI + crypto", status: "active", assets: ["AI tokens"], risk: "high volatility, narrative-sensitive" },
            { name: "RWA", status: "watching", assets: ["RWA tokens"], risk: "regulatory" },
            { name: "DePIN", status: "watching", assets: ["DePIN tokens"], risk: "adoption pace" },
            { name: "Solana memecoin cycle", status: "cooling", assets: ["SOL", "Memecoins"], risk: "liquidity drain" },
            { name: "Ethereum L2 fragmentation", status: "active", assets: ["ETH", "L2s"], risk: "fee compression" },
            { name: "Stablecoin regulation", status: "watching", assets: ["Stablecoins"], risk: "regulatory" },
            { name: "Exchange insolvency risk", status: "monitoring", assets: ["all"], risk: "counterparty" },
          ],
          source: "knowledge/crypto/narrative-map.json",
          note: "v0: static map. Wire to live narrative tracker for updates.",
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }

    default:
      return { success: false, tool: toolName, timestamp, error: `Unknown crypto tool: ${toolName}` };
  }
}
