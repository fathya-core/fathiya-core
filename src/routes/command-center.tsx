import { createFileRoute, Link } from "@tanstack/react-router";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import {
  Activity,
  ArrowRight,
  BadgeCheck,
  BrainCircuit,
  ClipboardList,
  FileCheck2,
  FolderKanban,
  GitPullRequest,
  Receipt,
  ShieldCheck,
  SquareStack,
  TriangleAlert,
  Workflow,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  getStatusTone,
  loadCommandCenterSnapshot,
  type CommandCenterSnapshot,
  type DataProvenance,
} from "@/lib/command-center";

export const Route = createFileRoute("/command-center")({
  head: () => ({
    meta: [
      { title: "Command Center v0 — FATHIYA" },
      {
        name: "description",
        content:
          "Command Center v0 for the FATHIYA operating backbone. Surfaces overview, intake, knowledge cards, routing, operations staging, runtime queue, receipts, agents, playbooks, tool contracts, radar, scope, and approvals from local knowledge files.",
      },
    ],
  }),
  loader: () => loadCommandCenterSnapshot(),
  component: CommandCenterPage,
});

const SCREEN_TABS = [
  { value: "overview", label: "Overview" },
  { value: "queue", label: "Runtime Queue" },
  { value: "receipts", label: "Receipt Ledger" },
  { value: "agents", label: "Agents" },
  { value: "playbooks", label: "Playbooks" },
  { value: "tools", label: "Tool Contracts" },
  { value: "intake", label: "Daily Intake" },
  { value: "radar", label: "Crypto Radar" },
  { value: "scope", label: "Scope & Authorization" },
  { value: "approvals", label: "Approval Queue" },
] as const;

function CommandCenterPage() {
  const data = Route.useLoaderData() as CommandCenterSnapshot;
  const latestReceipts = data.receipts.slice(-5).reverse();

  return (
    <div dir="ltr" lang="en" className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-primary/20 bg-primary/10">
              <SquareStack className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-semibold tracking-tight">
                  FATHIYA Command Center v0
                </h1>
                <StatusBadge status={data.loaderMode} />
              </div>
              <p className="text-xs text-muted-foreground">
                Operating Backbone control surface backed by local knowledge files and documented
                fallback lanes.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
            >
              <ArrowRight className="h-3.5 w-3.5" />
              Back to Ops Console
            </Link>
            <Link
              to="/ai-runs"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
            >
              <Receipt className="h-3.5 w-3.5" />
              AI Runs
            </Link>
            <Link
              to="/ai-console"
              className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
            >
              <BrainCircuit className="h-3.5 w-3.5" />
              AI Console
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            icon={Activity}
            label="Current focus"
            value={data.overview.currentFocus}
            help="From FATHIYA_AWARENESS_STATE current_focus with a bootstrap default when empty."
          />
          <MetricCard
            icon={FolderKanban}
            label="Active queue count"
            value={String(data.overview.activeQueueCount)}
            help="Uses live queue entries when present; otherwise falls back to the awareness-state count."
          />
          <MetricCard
            icon={TriangleAlert}
            label="Blocked items"
            value={String(data.overview.blockedItemsCount)}
            help="Awareness blockers plus blocked queue entries."
          />
          <MetricCard
            icon={BadgeCheck}
            label="Latest receipts"
            value={String(data.overview.latestReceiptsCount)}
            help="Uses live receipt ledger rows when present; otherwise falls back to awareness latest_receipts."
          />
          <MetricCard
            icon={GitPullRequest}
            label="Open PRs"
            value={String(data.overview.openPrCount)}
            help="Pulled from awareness state; the skeleton is still empty in v0."
          />
          <MetricCard
            icon={Workflow}
            label="Active agents"
            value={String(data.overview.activeAgentsCount)}
            help="Pulled from awareness state; registered agents remain visible below even when no active execution is recorded."
          />
          <MetricCard
            icon={FileCheck2}
            label="Backbone validation"
            value={data.overview.validationStatus}
            help="Sourced from knowledge/audit/FATHIYA_BACKBONE_VALIDATION_REPORT_v0.json."
          />
          <MetricCard
            icon={TriangleAlert}
            label="Validation warnings"
            value={String(data.overview.warningsCount)}
            help="Warnings from the validated backbone report."
          />
        </div>

        <Card className="mb-4 border-primary/20 bg-primary/5">
          <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-[0.22em] text-primary/80">
                Loader note
              </div>
              <p className="text-sm text-foreground">{data.loaderNote}</p>
            </div>
            <div className="max-w-md text-xs text-muted-foreground">
              <div className="font-medium text-foreground">Next recommended action</div>
              <p className="mt-1">{data.overview.nextRecommendedAction}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="mb-6 border-sky-500/20 bg-sky-500/5">
          <CardContent className="p-4">
            <div className="mb-1 text-xs font-semibold uppercase tracking-[0.22em] text-sky-400/80">
              Build lineage
            </div>
            <div className="grid gap-2 text-sm md:grid-cols-2">
              <div>
                <span className="text-xs text-muted-foreground">Validated checkpoint:</span>
                <div className="font-medium">{data.lineage.backbonePR}</div>
              </div>
              <div>
                <span className="text-xs text-muted-foreground">Current layer:</span>
                <div className="font-medium">{data.lineage.commandCenterPR}</div>
              </div>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">{data.lineage.note}</p>
          </CardContent>
        </Card>

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 bg-muted/30 p-1">
            {SCREEN_TABS.map((tab) => (
              <TabsTrigger
                key={tab.value}
                value={tab.value}
                className="text-xs data-[state=active]:bg-background"
              >
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <SectionHeader
              title="Expansion surface"
              description="Daily intake, knowledge cards, Apps/GPTs routing, staged operations, and recent receipts now render together in one compact overview while the existing detailed tabs remain available below."
            />
            <div className="grid gap-4 xl:grid-cols-2">
              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <CardTitle>Daily Intake</CardTitle>
                      <CardDescription>
                        Latest canonical batch summary from the intake batch and source manifest.
                      </CardDescription>
                    </div>
                    <StatusBadge
                      status={data.sectionProvenance.dailyIntake?.data_status ?? "planned"}
                    />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {data.latestDailyIntake ? (
                    <>
                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        <OverviewField
                          label="Latest batch date"
                          value={data.latestDailyIntake.latestBatchDate}
                        />
                        <OverviewField
                          label="Source count"
                          value={String(data.latestDailyIntake.sourceCount)}
                        />
                        <OverviewField
                          label="Derived card count"
                          value={String(data.latestDailyIntake.derivedCardCount)}
                        />
                        <OverviewField
                          label="Receipt id"
                          value={data.latestDailyIntake.receiptId}
                        />
                        <OverviewField label="Queue id" value={data.latestDailyIntake.queueId} />
                        <OverviewField label="Cycle" value={data.latestDailyIntake.cycle} />
                      </div>
                      <div>
                        <div className="mb-2 text-sm font-medium">Pending items</div>
                        <TagList
                          items={
                            data.latestDailyIntake.pendingItems.length > 0
                              ? data.latestDailyIntake.pendingItems
                              : ["No pending items"]
                          }
                        />
                      </div>
                    </>
                  ) : (
                    <EmptyState
                      title="No daily intake batch detected"
                      description="As soon as a canonical daily intake batch is bundled into knowledge/intake/daily, the latest batch summary will appear here."
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <CardTitle>Apps/GPTs Routing</CardTitle>
                      <CardDescription>
                        Structured spreadsheet parse status, routing counts, and hard rules from the
                        routing artifacts.
                      </CardDescription>
                    </div>
                    <StatusBadge
                      status={data.sectionProvenance.routing?.data_status ?? "planned"}
                    />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {data.routingSummary ? (
                    <>
                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        <OverviewField
                          label="Spreadsheet status"
                          value={data.routingSummary.sourceSpreadsheetStatus}
                        />
                        <OverviewField
                          label="App rows"
                          value={String(data.routingSummary.appRows)}
                        />
                        <OverviewField
                          label="GPT rows"
                          value={String(data.routingSummary.gptRows)}
                        />
                        <OverviewField
                          label="Sample workflows"
                          value={String(data.routingSummary.sampleWorkflows)}
                        />
                      </div>
                      <OverviewField
                        label="Source spreadsheet"
                        value={data.routingSummary.sourceSpreadsheet}
                      />
                      <StringListPanel
                        title="High-level routing rules"
                        items={data.routingSummary.highLevelRules}
                      />
                    </>
                  ) : (
                    <EmptyState
                      title="No routing summary available"
                      description="The Apps/GPTs routing map and rules files will populate this section once bundled into the knowledge layer."
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <CardTitle>Operations Queue</CardTitle>
                      <CardDescription>
                        Staged operations status from operations_autopilot_queue_v0.json.
                      </CardDescription>
                    </div>
                    <StatusBadge
                      status={data.sectionProvenance.operationsQueue?.data_status ?? "planned"}
                    />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {data.operationsQueue ? (
                    <>
                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        <OverviewField label="Queue status" value={data.operationsQueue.status} />
                        <OverviewField
                          label="Staged entries"
                          value={String(data.operationsQueue.stagedEntriesCount)}
                        />
                        <OverviewField
                          label="Total entries"
                          value={String(data.operationsQueue.totalEntries)}
                        />
                        <OverviewField
                          label="Queues defined"
                          value={String(data.operationsQueue.queueDefinitions.length)}
                        />
                      </div>
                      <OverviewField label="Purpose" value={data.operationsQueue.purpose} />
                      <div>
                        <div className="mb-2 text-sm font-medium">Status breakdown</div>
                        <TagList
                          items={data.operationsQueue.statusBreakdown.map(
                            (entry) => `${entry.status}: ${entry.count}`,
                          )}
                        />
                      </div>
                    </>
                  ) : (
                    <EmptyState
                      title="No operations queue metadata"
                      description="This section will render as soon as the operations staging queue file is available."
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <CardTitle>Runtime & recent receipts</CardTitle>
                      <CardDescription>
                        Live runtime counts plus the most relevant recent intake and routing
                        receipts.
                      </CardDescription>
                    </div>
                    <StatusBadge
                      status={data.sectionProvenance.runtimeAndReceipts?.data_status ?? "empty"}
                    />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <OverviewField
                      label="Active queue count"
                      value={String(data.overview.activeQueueCount)}
                    />
                    <OverviewField
                      label="Receipt ledger rows"
                      value={String(data.receipts.length)}
                    />
                    <OverviewField
                      label="Latest receipts"
                      value={String(data.overview.latestReceiptsCount)}
                    />
                    <OverviewField
                      label="Blocked items"
                      value={String(data.overview.blockedItemsCount)}
                    />
                  </div>
                  <RecentReceiptList receipts={data.recentIntakeRoutingReceipts} />
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <CardTitle>Knowledge Cards</CardTitle>
                      <CardDescription>
                        Latest daily cards from knowledge/cards/daily/2026-05-17 with source
                        coverage.
                      </CardDescription>
                    </div>
                    <StatusBadge status={data.knowledgeCards.length > 0 ? "active" : "empty"} />
                  </div>
                </CardHeader>
                <CardContent>
                  {data.knowledgeCards.length === 0 ? (
                    <EmptyState
                      title="No daily knowledge cards found"
                      description="The latest dated daily card folder will render here once card files exist."
                    />
                  ) : (
                    <DataTable
                      headers={["card id", "domain / title", "status", "source coverage"]}
                      rows={data.knowledgeCards.map((card) => [
                        <code key="id">{card.cardId}</code>,
                        <div key="title">
                          <div className="font-medium">{card.title}</div>
                          <div className="text-[11px] text-muted-foreground">{card.domain}</div>
                        </div>,
                        <StatusBadge key="status" status={card.status} />,
                        <div key="coverage" className="space-y-2">
                          <div>{card.sourceCoverage}</div>
                          <TagList items={card.sourceFiles} />
                        </div>,
                      ])}
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <CardTitle>Tool Contracts</CardTitle>
                      <CardDescription>
                        Operations-layer contract drafts from operations_tool_contracts_v0.json.
                      </CardDescription>
                    </div>
                    <StatusBadge
                      status={
                        data.sectionProvenance.operationsToolContracts?.data_status ?? "planned"
                      }
                    />
                  </div>
                </CardHeader>
                <CardContent>
                  {data.operationsToolContracts.length === 0 ? (
                    <EmptyState
                      title="No operations tool contracts"
                      description="This section will render once operations-specific contract drafts are available."
                    />
                  ) : (
                    <DataTable
                      headers={["id", "name", "status", "category"]}
                      rows={data.operationsToolContracts.map((contract) => [
                        <code key="id">{contract.toolId}</code>,
                        contract.name,
                        <StatusBadge key="status" status={contract.status} />,
                        contract.category,
                      ])}
                    />
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <CardTitle>Operational overview</CardTitle>
                  <CardDescription>
                    Backbone state from awareness, runtime, receipts, and validation files.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <OverviewField label="Current focus" value={data.overview.currentFocus} />
                    <OverviewField
                      label="Next recommended action"
                      value={data.overview.nextRecommendedAction}
                    />
                  </div>
                  <Separator />
                  <div className="grid gap-3 md:grid-cols-3">
                    <SmallStat
                      label="Workflows"
                      value={String(data.registriesSummary.workflowCount)}
                      icon={Workflow}
                    />
                    <SmallStat
                      label="Skills"
                      value={String(data.registriesSummary.skillCount)}
                      icon={SquareStack}
                    />
                    <SmallStat
                      label="Machine tasks"
                      value={String(data.registriesSummary.machineTaskCount)}
                      icon={ClipboardList}
                    />
                    <SmallStat
                      label="Model lanes"
                      value={String(data.registriesSummary.modelLaneCount)}
                      icon={BrainCircuit}
                    />
                    <SmallStat
                      label="Approval classes"
                      value={String(data.registriesSummary.approvalClassCount)}
                      icon={ShieldCheck}
                    />
                    <SmallStat
                      label="Queue catalog"
                      value={String(data.queueCatalog.length)}
                      icon={FolderKanban}
                    />
                  </div>
                  <Separator />
                  <div>
                    <div className="mb-2 text-sm font-medium">Latest receipts</div>
                    {latestReceipts.length === 0 ? (
                      <EmptyState
                        title="No receipts recorded yet"
                        description="The ledger file exists and is wired up. As soon as receipts are written into the local JSON ledger, they will appear here automatically."
                      />
                    ) : (
                      <div className="space-y-2">
                        {latestReceipts.map((receipt) => (
                          <div
                            key={receipt.receipt_id}
                            className="rounded-lg border border-border/50 bg-muted/20 p-3"
                          >
                            <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                              <div className="font-mono text-xs">{receipt.receipt_id}</div>
                              <StatusBadge status={receipt.status} />
                            </div>
                            <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
                              <div>Queue: {receipt.queue}</div>
                              <div>Adapter: {receipt.adapter}</div>
                              <div>Input: {receipt.input_artifact}</div>
                              <div>Output: {receipt.output_artifact}</div>
                            </div>
                            <p className="mt-2 text-xs text-foreground">
                              Next: {receipt.next_step}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <div className="space-y-4">
                <Card className="border-border/60 bg-card/50">
                  <CardHeader>
                    <CardTitle>Data source map</CardTitle>
                    <CardDescription>
                      How the UI maps back to the operating backbone files.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {data.sources.map((source) => (
                      <div
                        key={source.path}
                        className="rounded-lg border border-border/50 bg-muted/20 p-3"
                      >
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <div className="text-sm font-medium">{source.label}</div>
                          <Badge variant="outline" className="text-[10px]">
                            {source.kind}
                          </Badge>
                        </div>
                        <div className="font-mono text-[11px] text-muted-foreground">
                          {source.path}
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">{source.note}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card className="border-border/60 bg-card/50">
                  <CardHeader>
                    <CardTitle>Awareness state</CardTitle>
                    <CardDescription>
                      Live bootstrap values straight from the awareness file.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <OverviewField
                      label="Last updated"
                      value={data.awareness.last_updated ?? "Not yet updated"}
                    />
                    <OverviewField
                      label="Completed artifacts"
                      value={
                        data.awareness.completed_artifacts.length > 0
                          ? data.awareness.completed_artifacts.join(", ")
                          : "No completed artifacts recorded yet."
                      }
                    />
                    <OverviewField
                      label="Open PRs"
                      value={
                        data.awareness.open_prs.length > 0
                          ? data.awareness.open_prs.join(", ")
                          : "No PRs recorded in awareness state yet."
                      }
                    />
                    <OverviewField
                      label="Active agents"
                      value={
                        data.awareness.active_agents.length > 0
                          ? data.awareness.active_agents.join(", ")
                          : "No active agents recorded in awareness state yet."
                      }
                    />
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="queue" className="space-y-4">
            <SectionHeader
              title="Runtime Queue"
              description="Every routed task should appear here before or during execution. The table below renders live canonical rows from runtime_queue_v0.json, including the hardening, Crypto Radar, and PB005 scope/auth preparation batches."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.runtimeQueue} />
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Queue entries</CardTitle>
                <CardDescription>
                  Live rows render directly from <code>queue_entries</code> in PLAYBOOK 003's
                  runtime queue file.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.queueEntries.length === 0 ? (
                  <EmptyState
                    title="No runtime queue entries yet"
                    description="This table stays empty until a routed task is written into runtime_queue_v0.json."
                  />
                ) : (
                  <DataTable
                    headers={[
                      "id",
                      "timestamp",
                      "source",
                      "requested by",
                      "queue",
                      "adapter",
                      "mode",
                      "input artifact",
                      "expected output",
                      "approval",
                      "status",
                      "receipt path",
                      "next step",
                    ]}
                    rows={data.queueEntries.map((entry) => [
                      <code key="id">{entry.id}</code>,
                      entry.timestamp,
                      entry.source,
                      entry.requested_by ?? "—",
                      entry.queue,
                      entry.adapter,
                      entry.mode,
                      entry.input_artifact ?? "—",
                      entry.expected_output,
                      formatApproval(entry.approval_required),
                      <StatusBadge key="status" status={entry.status} />,
                      entry.receipt_path ?? "—",
                      entry.next_step,
                    ])}
                  />
                )}

                <div>
                  <div className="mb-2 text-sm font-medium">Required entry fields</div>
                  <TagList items={data.runtimeRequiredFields} />
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Queue catalog</CardTitle>
                <CardDescription>
                  Canonical queue definitions from runtime_queue_v0.json.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  headers={[
                    "queue",
                    "purpose",
                    "default approval",
                    "allowed outputs",
                    "allowed adapters",
                  ]}
                  rows={data.queueCatalog.map((queue) => [
                    queue.name,
                    queue.purpose,
                    queue.defaultApproval,
                    <TagList
                      key="outputs"
                      items={queue.outputs.length > 0 ? queue.outputs : ["—"]}
                    />,
                    <TagList
                      key="adapters"
                      items={queue.adapters.length > 0 ? queue.adapters : ["—"]}
                    />,
                  ])}
                />
              </CardContent>
            </Card>

            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Operations staging queue</CardTitle>
                <CardDescription>
                  Staged operations metadata from the separate operations autopilot queue.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <ProvenanceBanner provenance={data.sectionProvenance.operationsQueue} />
                {data.operationsQueue ? (
                  <>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <OverviewField label="Status" value={data.operationsQueue.status} />
                      <OverviewField
                        label="Staged entries"
                        value={String(data.operationsQueue.stagedEntriesCount)}
                      />
                      <OverviewField
                        label="Total entries"
                        value={String(data.operationsQueue.totalEntries)}
                      />
                      <OverviewField
                        label="Defined queues"
                        value={String(data.operationsQueue.queueDefinitions.length)}
                      />
                    </div>
                    <OverviewField label="Purpose" value={data.operationsQueue.purpose} />
                    <div>
                      <div className="mb-2 text-sm font-medium">Queue definitions</div>
                      <DataTable
                        headers={["queue", "purpose", "default status", "allowed statuses"]}
                        rows={data.operationsQueue.queueDefinitions.map((queue) => [
                          queue.name,
                          queue.purpose,
                          queue.defaultStatus,
                          <TagList key="statuses" items={queue.allowedStatuses} />,
                        ])}
                      />
                    </div>
                    <div>
                      <div className="mb-2 text-sm font-medium">Required entry fields</div>
                      <TagList items={data.operationsQueue.entryFields} />
                    </div>
                  </>
                ) : (
                  <EmptyState
                    title="No operations staging queue"
                    description="The operations staging queue file is not currently available."
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="receipts" className="space-y-4">
            <SectionHeader
              title="Receipt Ledger"
              description="No meaningful action is complete without a receipt. The table below renders live canonical receipts from receipt_ledger_v0.json for the hardening, Crypto Radar, and PB005 scope/auth preparation batches."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.receiptLedger} />
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Recent intake and routing receipts</CardTitle>
                <CardDescription>
                  The latest receipts tied directly to Daily Intake Cycle 001 and the Apps/GPTs
                  routing integration.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <RecentReceiptList receipts={data.recentIntakeRoutingReceipts} />
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Receipts</CardTitle>
                <CardDescription>
                  Proof rows render directly from the <code>receipts</code> array in
                  knowledge/runtime/receipt_ledger_v0.json.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.receipts.length === 0 ? (
                  <EmptyState
                    title="No receipts recorded yet"
                    description="The ledger schema is in place and this table will populate once receipt rows are written into the local JSON file."
                  />
                ) : (
                  <DataTable
                    headers={[
                      "receipt id",
                      "timestamp",
                      "source request",
                      "queue",
                      "adapter",
                      "input artifact",
                      "output artifact",
                      "status",
                      "error",
                      "approval reference",
                      "next step",
                    ]}
                    rows={data.receipts.map((receipt) => [
                      <code key="id">{receipt.receipt_id}</code>,
                      receipt.timestamp,
                      receipt.source_request ?? "—",
                      receipt.queue,
                      receipt.adapter,
                      receipt.input_artifact,
                      receipt.output_artifact,
                      <StatusBadge key="status" status={receipt.status} />,
                      receipt.error ?? "—",
                      receipt.approval_reference ?? "—",
                      receipt.next_step,
                    ])}
                  />
                )}

                <div className="grid gap-4 lg:grid-cols-2">
                  <div>
                    <div className="mb-2 text-sm font-medium">Required receipt fields</div>
                    <TagList items={data.receiptRequiredFields} />
                  </div>
                  <div>
                    <div className="mb-2 text-sm font-medium">Receipt policy</div>
                    <DataTable
                      headers={["queue", "policy"]}
                      rows={data.receiptPolicy.map((policy) => [policy.queue, policy.policy])}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="agents" className="space-y-4">
            <SectionHeader
              title="Agents"
              description="Registered operators and their workflow context from the agent and workflow registries."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.agents} />
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Agent registry</CardTitle>
                <CardDescription>
                  Agent role, queue, tools, permissions, and failure modes.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  headers={[
                    "agent id",
                    "name",
                    "role",
                    "queue",
                    "capabilities",
                    "tools",
                    "permissions",
                    "status",
                    "failure modes",
                  ]}
                  rows={data.agents.map((agent) => [
                    <code key="id">{agent.agentId}</code>,
                    agent.name,
                    agent.role,
                    agent.queue,
                    <TagList key="caps" items={agent.capabilities} />,
                    <TagList key="tools" items={agent.tools} />,
                    <TagList key="permissions" items={agent.permissions} />,
                    <StatusBadge key="status" status={agent.status} />,
                    <TagList key="failures" items={agent.failureModes} />,
                  ])}
                />
              </CardContent>
            </Card>

            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Workflow registry</CardTitle>
                <CardDescription>
                  Repeatable operating workflows already promoted into the backbone.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  headers={[
                    "workflow id",
                    "name",
                    "playbook",
                    "trigger",
                    "queue",
                    "mode",
                    "adapters",
                    "status",
                  ]}
                  rows={data.workflows.map((workflow) => [
                    <code key="id">{workflow.workflowId}</code>,
                    workflow.name,
                    workflow.playbook,
                    workflow.trigger,
                    workflow.queue,
                    workflow.mode,
                    <TagList key="adapters" items={workflow.adapters} />,
                    <StatusBadge key="status" status={workflow.status} />,
                  ])}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="playbooks" className="space-y-4">
            <SectionHeader
              title="Playbooks"
              description="Parsed from the markdown playbooks, with status, purpose, required files, next chain, and last validation date."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.playbooks} />
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Playbook chain</CardTitle>
                <CardDescription>
                  The validated backbone sequence from PB001 through PB009.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  headers={[
                    "playbook id",
                    "title",
                    "status",
                    "purpose",
                    "required files",
                    "next playbook",
                    "last validation",
                  ]}
                  rows={data.playbooks.map((playbook) => [
                    <code key="id">{playbook.playbookId}</code>,
                    playbook.title,
                    <StatusBadge key="status" status={playbook.status} />,
                    playbook.purpose,
                    <TagList
                      key="files"
                      items={playbook.requiredFiles.length > 0 ? playbook.requiredFiles : ["—"]}
                    />,
                    playbook.nextPlaybook,
                    playbook.lastValidation,
                  ])}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="tools" className="space-y-4">
            <SectionHeader
              title="Tool Contracts"
              description="Adapter boundaries, approval flags, and failure modes from the tool contract registry, plus the model-router registry that guides cost-aware inference."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.toolContracts} />
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Tool contract registry</CardTitle>
                <CardDescription>
                  The contract layer that prevents random execution.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  headers={[
                    "tool id",
                    "name",
                    "adapter",
                    "queue",
                    "allowed actions",
                    "side effects",
                    "approval required",
                    "receipt required",
                    "failure modes",
                    "status",
                  ]}
                  rows={data.toolContracts.map((contract) => [
                    <code key="id">{contract.toolId}</code>,
                    contract.name,
                    contract.adapter,
                    contract.queue,
                    <TagList key="actions" items={contract.allowedActions} />,
                    <TagList key="effects" items={contract.sideEffects} />,
                    contract.approvalRequired ? "yes" : "no",
                    contract.receiptRequired ? "yes" : "no",
                    <TagList key="failures" items={contract.failureModes} />,
                    <StatusBadge key="status" status={contract.status} />,
                  ])}
                />
              </CardContent>
            </Card>

            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Operations tool contracts</CardTitle>
                <CardDescription>
                  Staged webhook, workflow, messaging, and repository-operation contracts.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <ProvenanceBanner provenance={data.sectionProvenance.operationsToolContracts} />
                {data.operationsToolContracts.length === 0 ? (
                  <EmptyState
                    title="No operations tool contracts"
                    description="Operations-specific contract drafts will appear here when they are present in the knowledge registry."
                  />
                ) : (
                  <DataTable
                    headers={["tool id", "name", "category", "queue", "approval class", "status"]}
                    rows={data.operationsToolContracts.map((contract) => [
                      <code key="id">{contract.toolId}</code>,
                      contract.name,
                      contract.category,
                      contract.queue,
                      contract.approvalClass,
                      <StatusBadge key="status" status={contract.status} />,
                    ])}
                  />
                )}
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <CardTitle>Model router lanes</CardTitle>
                  <CardDescription>
                    Cost-aware inference lanes sourced from model_router_registry_v0.json.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <DataTable
                    headers={["lane id", "name", "use when", "outputs", "approval required"]}
                    rows={data.modelRouter.lanes.map((lane) => [
                      <code key="id">{lane.laneId}</code>,
                      lane.name,
                      <TagList key="useWhen" items={lane.useWhen} />,
                      <TagList key="outputs" items={lane.outputs} />,
                      lane.approvalRequired ? "yes" : "no",
                    ])}
                  />
                </CardContent>
              </Card>

              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <CardTitle>Router guardrails</CardTitle>
                  <CardDescription>
                    Fallback rules and cost controls from the model router registry.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="mb-2 text-sm font-medium">Fallback rules</div>
                    <TagList items={data.modelRouter.fallbackRules} />
                  </div>
                  <div>
                    <div className="mb-2 text-sm font-medium">Cost controls</div>
                    <TagList items={data.modelRouter.costControls} />
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="intake" className="space-y-4">
            <SectionHeader
              title="Daily Intake"
              description="This view now surfaces the latest real daily intake batch, the current daily knowledge cards, and the historical intake rows that were already part of the Command Center loader."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.dailyIntake} />
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Latest batch summary</CardTitle>
                <CardDescription>
                  Canonical intake facts from daily_intake_batch_001.json and the matching source
                  manifest.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.latestDailyIntake ? (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <OverviewField
                      label="Latest batch date"
                      value={data.latestDailyIntake.latestBatchDate}
                    />
                    <OverviewField
                      label="Source count"
                      value={String(data.latestDailyIntake.sourceCount)}
                    />
                    <OverviewField
                      label="Derived card count"
                      value={String(data.latestDailyIntake.derivedCardCount)}
                    />
                    <OverviewField label="Cycle" value={data.latestDailyIntake.cycle} />
                    <OverviewField label="Queue id" value={data.latestDailyIntake.queueId} />
                    <OverviewField label="Receipt id" value={data.latestDailyIntake.receiptId} />
                    <div className="md:col-span-2 xl:col-span-3">
                      <div className="mb-2 text-sm font-medium">Pending items</div>
                      <TagList
                        items={
                          data.latestDailyIntake.pendingItems.length > 0
                            ? data.latestDailyIntake.pendingItems
                            : ["No pending items"]
                        }
                      />
                    </div>
                  </div>
                ) : (
                  <EmptyState
                    title="No live daily batch summary"
                    description="The latest batch summary will render here once a daily intake batch file is present."
                  />
                )}
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Latest knowledge cards</CardTitle>
                <CardDescription>
                  Daily cards from the latest dated daily folder, including source coverage and
                  receipt linkage.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.knowledgeCards.length === 0 ? (
                  <EmptyState
                    title="No daily knowledge cards"
                    description="Card files from the latest daily folder will appear here when present."
                  />
                ) : (
                  <DataTable
                    headers={["card id", "domain / title", "status", "source coverage", "receipt"]}
                    rows={data.knowledgeCards.map((card) => [
                      <code key="id">{card.cardId}</code>,
                      <div key="title">
                        <div className="font-medium">{card.title}</div>
                        <div className="text-[11px] text-muted-foreground">{card.domain}</div>
                      </div>,
                      <StatusBadge key="status" status={card.status} />,
                      <div key="coverage" className="space-y-2">
                        <div>{card.sourceCoverage}</div>
                        <TagList items={card.sourceFiles} />
                      </div>,
                      card.receiptId,
                    ])}
                  />
                )}
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Historical intake rows</CardTitle>
                <CardDescription>
                  Legacy retrieval-backed and derived audit rows preserved for historical context.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  headers={[
                    "source",
                    "captured count",
                    "duplicates",
                    "classified domains",
                    "cards drafted",
                    "blockers",
                    "receipts",
                    "next actions",
                    "source type",
                  ]}
                  rows={data.dailyIntake.map((row) => [
                    row.source,
                    String(row.capturedCount),
                    String(row.duplicates),
                    <TagList key="domains" items={row.classifiedDomains} />,
                    String(row.cardsDrafted),
                    <TagList key="blockers" items={row.blockers} />,
                    <TagList key="receipts" items={row.receipts} />,
                    <TagList key="actions" items={row.nextActions} />,
                    <Badge key="type" variant="outline" className="text-[10px]">
                      {row.sourceType}
                    </Badge>,
                  ])}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="radar" className="space-y-4">
            <SectionHeader
              title="Crypto Radar"
              description="PB006 now renders the first live monitoring batch from the preserved Manus source brief. This section stays explicitly research-only and does not authorize trading execution."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.cryptoRadar} />
            {data.cryptoRadarBatch ? (
              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <CardTitle>Live batch summary</CardTitle>
                  <CardDescription>
                    Canonical PB006 batch manifest and queue/receipt linkage for the first live
                    Crypto Radar intake.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <OverviewField label="Batch id" value={data.cryptoRadarBatch.batchId} />
                    <OverviewField
                      label="Card count"
                      value={String(data.cryptoRadarBatch.cardCount)}
                    />
                    <OverviewField
                      label="Queue entry id"
                      value={data.cryptoRadarBatch.queueEntryId}
                    />
                    <OverviewField label="Receipt id" value={data.cryptoRadarBatch.receiptId} />
                    <OverviewField label="Mode" value={data.cryptoRadarBatch.mode} />
                    <OverviewField label="Playbook" value={data.cryptoRadarBatch.playbook} />
                    <OverviewField label="Status" value={data.cryptoRadarBatch.status} />
                    <OverviewField label="Created at" value={data.cryptoRadarBatch.createdAt} />
                  </div>
                  <OverviewField label="Source file" value={data.cryptoRadarBatch.sourceFile} />
                  <OverviewField label="Boundary" value={data.cryptoRadarBatch.boundary} />
                  <div>
                    <div className="mb-2 text-sm font-medium">Batch notes</div>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {data.cryptoRadarBatch.notes.map((note) => (
                        <li
                          key={note}
                          className="rounded-lg border border-border/50 bg-muted/20 p-3"
                        >
                          {note}
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            ) : null}

            {data.cryptoRadar.length === 0 ? (
              <Card className="border-border/60 bg-card/50">
                <CardContent className="p-6">
                  <EmptyState
                    title="No crypto radar signals yet"
                    description="This is a planned section. Signal cards will appear once the first PLAYBOOK 006 intake batch runs and routes signals into the runtime queue. The intake process, approval gates, and risk-factor requirements are defined in PB006 and the approval policy registry."
                  />
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 xl:grid-cols-2">
                {data.cryptoRadar.map((card) => (
                  <RadarCard key={card.id} card={card} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="scope" className="space-y-4">
            <SectionHeader
              title="Scope & Authorization"
              description="PB005 now renders the first live owned-surface Target Card and Scope Map for FATHIYA Core. This section is explicitly preparation-only with status draft / needs_policy, and it does not authorize active testing."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.scopeAuthorization} />
            {data.targetCards.length > 0 ? (
              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <CardTitle>Live target cards</CardTitle>
                  <CardDescription>
                    Canonical Target Cards define the named target, authorization context, allowed
                    artifacts, and explicit no-testing boundary for PB005 preparation.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {data.targetCards.map((card) => (
                    <div
                      key={card.targetId}
                      className="space-y-4 rounded-xl border border-border/50 bg-muted/10 p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="text-lg font-semibold">{card.name}</div>
                          <div className="mt-1 text-sm text-muted-foreground">{card.program}</div>
                        </div>
                        <StatusBadge status={card.status} />
                      </div>
                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        <OverviewField label="Target id" value={card.targetId} />
                        <OverviewField label="Policy URL" value={card.policyUrl} />
                        <OverviewField label="Authorization" value={card.authorization} />
                        <OverviewField label="Mode" value={card.mode} />
                        <OverviewField label="Asset status" value={card.assetStatus} />
                        <OverviewField label="Approval required" value={card.approvalRequired} />
                        <OverviewField label="Reporting channel" value={card.reportingChannel} />
                        <OverviewField label="Created at" value={card.createdAt} />
                      </div>
                      <OverviewField label="Boundary note" value={card.boundaryNote} />
                      <div className="grid gap-4 xl:grid-cols-2">
                        <div className="space-y-4">
                          <div>
                            <div className="mb-2 text-sm font-medium">Allowed artifacts</div>
                            <TagList items={card.allowedArtifacts} />
                          </div>
                          <StringListPanel title="Engagement rules" items={card.engagementRules} />
                          <StringListPanel title="Rate limits" items={card.rateLimits} />
                        </div>
                        <div className="space-y-4">
                          <StringListPanel
                            title="Forbidden actions"
                            items={card.forbiddenActions}
                          />
                          <StringListPanel title="Data handling" items={card.dataHandling} />
                        </div>
                      </div>
                      <div>
                        <div className="mb-2 text-sm font-medium">Declared assets</div>
                        <DataTable
                          headers={["url", "asset status", "testing status"]}
                          rows={card.assets.map((asset) => [
                            <span key="url" className="font-mono text-[11px]">
                              {asset.url}
                            </span>,
                            asset.assetStatus,
                            asset.testingStatus,
                          ])}
                        />
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : null}

            {data.scopeMaps.length > 0 ? (
              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <CardTitle>Live scope maps</CardTitle>
                  <CardDescription>
                    Scope maps classify what is in scope for preparation, what is out of scope, and
                    what still requires policy clarification before any external activity.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {data.scopeMaps.map((scopeMap) => (
                    <div
                      key={scopeMap.scopeMapId}
                      className="space-y-4 rounded-xl border border-border/50 bg-muted/10 p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="text-lg font-semibold">{scopeMap.name}</div>
                          <div className="mt-1 text-sm text-muted-foreground">
                            {scopeMap.program}
                          </div>
                        </div>
                        <StatusBadge status={scopeMap.status} />
                      </div>
                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        <OverviewField label="Scope map id" value={scopeMap.scopeMapId} />
                        <OverviewField label="Target id" value={scopeMap.targetId} />
                        <OverviewField label="Mode" value={scopeMap.mode} />
                        <OverviewField label="Created at" value={scopeMap.createdAt} />
                        <OverviewField
                          label="Authorization status"
                          value={scopeMap.authorizationStatus}
                        />
                        <OverviewField label="Policy status" value={scopeMap.policyStatus} />
                        <OverviewField label="Playbook" value={scopeMap.playbook} />
                        <OverviewField label="Status" value={scopeMap.status} />
                      </div>
                      <OverviewField label="Boundary note" value={scopeMap.boundaryNote} />
                      <div>
                        <div className="mb-2 text-sm font-medium">In-scope preparation rows</div>
                        <DataTable
                          headers={["asset", "asset status", "allowed activity", "notes"]}
                          rows={scopeMap.inScope.map((item) => [
                            <span key="asset" className="font-mono text-[11px]">
                              {item.asset}
                            </span>,
                            item.assetStatus,
                            item.allowedActivity,
                            item.notes,
                          ])}
                        />
                      </div>
                      <div className="grid gap-4 xl:grid-cols-2">
                        <StringListPanel title="Out of scope" items={scopeMap.outOfScope} />
                        <StringListPanel title="Unknown scope" items={scopeMap.unknownScope} />
                        <StringListPanel
                          title="Requires clarification"
                          items={scopeMap.requiresClarification}
                        />
                        <div>
                          <div className="mb-2 text-sm font-medium">Next artifacts</div>
                          <TagList items={scopeMap.nextArtifacts} />
                        </div>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : null}
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Scope & authorization summary rows</CardTitle>
                <CardDescription>
                  Condensed rows for the canonical PB005 target-preparation state. The current
                  target stays visible as live documentation only and does not unlock active
                  testing.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.scopeAuthorization.length === 0 ? (
                  <EmptyState
                    title="No target cards or scope maps yet"
                    description="This section stays empty until PLAYBOOK 005 preparation writes canonical Target Card and Scope Map files into the knowledge bundle."
                  />
                ) : (
                  <DataTable
                    headers={[
                      "target id",
                      "name",
                      "policy URL",
                      "scope status",
                      "authorization status",
                      "blocked reason",
                      "next artifact",
                      "receipt",
                      "source type",
                    ]}
                    rows={data.scopeAuthorization.map((row) => [
                      <code key="id">{row.targetId}</code>,
                      row.name,
                      row.policyUrl,
                      <StatusBadge key="scope" status={row.scopeStatus} />,
                      <StatusBadge key="auth" status={row.authorizationStatus} />,
                      row.blockedReason,
                      row.nextArtifact,
                      row.receipt,
                      <Badge key="type" variant="outline" className="text-[10px]">
                        {row.sourceType}
                      </Badge>,
                    ])}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="approvals" className="space-y-4">
            <SectionHeader
              title="Approval Queue"
              description="No live approval requests exist yet. The rows below are derived from the backbone approval policy registry and show which gates are defined, not pending requests."
            />
            <ProvenanceBanner provenance={data.sectionProvenance.approvalQueue} />
            <Card className="border-border/60 bg-card/50">
              <CardHeader>
                <CardTitle>Approval-required policy lanes</CardTitle>
                <CardDescription>
                  Derived from approval_policy_registry_v0.json — these are policy classes, not live
                  approval requests. Labeled as <code>derived_from_backbone</code>.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  headers={[
                    "approval id",
                    "requested action",
                    "tool contract",
                    "payload preview",
                    "side effects",
                    "rollback / recovery",
                    "requester",
                    "status",
                    "source type",
                  ]}
                  rows={data.approvalQueue.map((row) => [
                    <code key="id">{row.approvalId}</code>,
                    row.requestedAction,
                    row.toolContract,
                    row.payloadPreview,
                    <TagList key="effects" items={row.sideEffects} />,
                    row.rollbackOrRecovery,
                    row.requester,
                    <StatusBadge key="status" status={row.status} />,
                    <Badge key="type" variant="outline" className="text-[10px]">
                      {row.sourceType}
                    </Badge>,
                  ])}
                />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  help,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  help: string;
}) {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardContent className="p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              {label}
            </div>
            <div className="mt-2 text-lg font-semibold leading-snug">{value}</div>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
            <Icon className="h-4 w-4 text-primary" />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">{help}</p>
      </CardContent>
    </Card>
  );
}

function SmallStat({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">{label}</span>
        <Icon className="h-3.5 w-3.5 text-primary" />
      </div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}

function OverviewField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
      <div className="mb-1 text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <div className="text-sm leading-6">{value}</div>
    </div>
  );
}

function SectionHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-card/40 p-4">
      <div className="text-base font-semibold">{title}</div>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border/60 bg-muted/10 p-6 text-center">
      <div className="text-sm font-medium">{title}</div>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function RecentReceiptList({
  receipts,
}: {
  receipts: CommandCenterSnapshot["recentIntakeRoutingReceipts"];
}) {
  if (receipts.length === 0) {
    return (
      <EmptyState
        title="No recent intake or routing receipts"
        description="Once the receipt files are present, their latest status and next step will appear here."
      />
    );
  }

  return (
    <div className="space-y-3">
      {receipts.map((receipt) => (
        <div key={receipt.receiptId} className="rounded-lg border border-border/50 bg-muted/20 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="font-mono text-xs">{receipt.receiptId}</div>
            <StatusBadge status={receipt.status} />
          </div>
          <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
            <div>Timestamp: {receipt.timestamp}</div>
            <div>Queue: {receipt.queue}</div>
          </div>
          <p className="mt-2 text-sm text-foreground">{receipt.summary}</p>
          <p className="mt-1 text-xs text-muted-foreground">Next: {receipt.nextStep}</p>
        </div>
      ))}
    </div>
  );
}

function StringListPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <div className="mb-2 text-sm font-medium">{title}</div>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="rounded-lg border border-border/50 bg-muted/20 p-3 text-sm">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function RadarCard({ card }: { card: CommandCenterSnapshot["cryptoRadar"][number] }) {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">{card.title}</CardTitle>
            <CardDescription className="mt-1">{card.assetOrSector}</CardDescription>
          </div>
          <StatusBadge status={card.status} />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {card.classification.map((item) => (
            <Badge key={item} variant="outline" className="text-[10px]">
              {item}
            </Badge>
          ))}
          <Badge variant="outline" className="text-[10px]">
            {card.confidence}
          </Badge>
          <Badge variant="outline" className="text-[10px]">
            {card.timeframe}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <OverviewField label="Card id" value={card.id} />
        <OverviewField label="Source file" value={card.sourceFile} />
        <OverviewField label="What changed" value={card.whatChanged} />
        <OverviewField label="Why it matters" value={card.whyItMatters} />
        <OverviewField label="Catalyst" value={card.catalyst} />

        <div>
          <div className="mb-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Risks
          </div>
          <ul className="space-y-2">
            {card.risks.map((risk) => (
              <li key={risk} className="rounded-lg border border-border/50 bg-muted/20 p-3">
                {risk}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <div className="mb-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Invalidation conditions
          </div>
          <ul className="space-y-2">
            {card.invalidationConditions.map((condition) => (
              <li key={condition} className="rounded-lg border border-border/50 bg-muted/20 p-3">
                {condition}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <div className="mb-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Source URLs
          </div>
          <div className="space-y-2">
            {card.sourceUrls.map((url) => (
              <a
                key={url}
                href={url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-lg border border-border/50 bg-muted/20 p-3 font-mono text-xs text-primary underline-offset-2 hover:underline"
              >
                {url}
              </a>
            ))}
          </div>
        </div>

        <OverviewField label="Boundary" value={card.boundary} />
      </CardContent>
    </Card>
  );
}

function ProvenanceBanner({ provenance }: { provenance: DataProvenance | undefined }) {
  if (!provenance) return null;

  const statusColors: Record<string, string> = {
    live: "border-emerald-500/30 bg-emerald-500/5 text-emerald-300",
    empty: "border-amber-500/30 bg-amber-500/5 text-amber-300",
    derived_from_backbone: "border-sky-500/30 bg-sky-500/5 text-sky-300",
    planned: "border-violet-500/30 bg-violet-500/5 text-violet-300",
  };

  return (
    <div
      className={cn(
        "rounded-lg border p-3 text-xs",
        statusColors[provenance.data_status] ?? "border-border/60 bg-muted/10",
      )}
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="font-semibold uppercase tracking-[0.16em]">
          {provenance.data_status.replaceAll("_", " ")}
        </span>
        {provenance.source_file !== "—" && (
          <span className="font-mono text-muted-foreground">{provenance.source_file}</span>
        )}
      </div>
      <p className="mt-1 text-muted-foreground">{provenance.notes}</p>
    </div>
  );
}

function DataTable({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) {
  return (
    <ScrollArea className="w-full rounded-lg border border-border/50">
      <Table className="min-w-[920px] text-xs">
        <TableHeader>
          <TableRow className="bg-muted/30 hover:bg-muted/30">
            {headers.map((header) => (
              <TableHead key={header} className="px-3 py-2 text-[10px] uppercase tracking-[0.18em]">
                {header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <TableCell key={`${rowIndex}-${cellIndex}`} className="px-3 py-3 align-top">
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </ScrollArea>
  );
}

function TagList({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <Badge key={item} variant="outline" className="max-w-full truncate text-[10px]">
          {item}
        </Badge>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone = getStatusTone(status);

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-1 text-[10px] font-medium uppercase tracking-[0.14em]",
        tone === "good" && "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
        tone === "warn" && "border-amber-500/30 bg-amber-500/10 text-amber-300",
        tone === "danger" && "border-destructive/30 bg-destructive/10 text-destructive",
        tone === "info" && "border-sky-500/30 bg-sky-500/10 text-sky-300",
        tone === "neutral" && "border-border/60 bg-muted/20 text-muted-foreground",
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

function formatApproval(value: boolean | string) {
  if (typeof value === "boolean") {
    return value ? "required" : "not required";
  }
  return value.replaceAll("_", " ");
}
