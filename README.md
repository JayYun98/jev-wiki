<div align="center">

# Jev Wiki
### Jev decides. Your LLM writes. Markdown remembers.

**A small wiki skill. A clear division of intelligence.**

[Get started](#get-started) · [Architecture](#architecture) · [Technical design](references/technical-design.md) · [Operations](references/operations.md) · [Estimated cost](#estimated-cost-1000-documents-across-five-domains) · [Evidence](references/evaluation.json)

</div>

![Sources flow through a decision prism and a writer into a connected knowledge archive. Concept illustration, not a product screenshot.](assets/hero.png)

> **Jev + a writer LLM + deterministic code.**
> Jev cannot write summaries or answers. Your host agent supplies the LLM.

## Same wiki idea. Different division of work.

```text
KARPATHY'S LLM WIKI PATTERN              JEV WIKI

Source + wiki + schema                 Source + wiki + skill
           │                                      │
           ▼                                      ▼
┌───────────────────────────┐          ┌───────────────────────────┐
│ LLM agent orchestrates    │          │ HOST LLM                  │
│                           │          │ Read · extract new claims │
│ Read and understand       │          └─────────────┬─────────────┘
│ Find relevant pages       │                        ▼
│ Decide what to update     │          ┌───────────────────────────┐
│ Notice contradictions     │          │ CODE / SEARCH             │
│ Write summaries / answers │          │ Hash · shortlist pages    │
│ Maintain links and index  │          └─────────────┬─────────────┘
│ Coordinate wiki upkeep    │                        ▼
└─────────────┬─────────────┘          ┌───────────────────────────┐
              │                        │ JEV                       │
              │                        │ Where to edit? New page?  │
              │                        │ Duplicate? Conflict?      │
              │                        │ Relevant? Enough evidence?│
              │                        └─────────────┬─────────────┘
              │                                      ▼
              │                        ┌───────────────────────────┐
              │                        │ HOST LLM                  │
              │                        │ Summarize · revise · answer│
              │                        └─────────────┬─────────────┘
              │                                      ▼
              │                        ┌───────────────────────────┐
              │                        │ JEV → CODE                │
              │                        │ Verify → publish → index  │
              │                        └─────────────┬─────────────┘
              ▼                                      ▼
       Markdown wiki                          Markdown wiki
```

Simplified responsibility comparison with [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), which also allows search and custom tools. This is not a performance benchmark.

| Work | Jev Wiki owner |
| :--- | :--- |
| Where to edit? Duplicate? Conflict? Enough evidence? | **Jev** |
| New concepts, summaries, synthesis, final answers | **Host LLM** |
| Retrieval, hashes, links, revisions, index | **Code** |

### One source → several page decisions

```text
New policy: “Refunds within 30 days”
                   │
          CODE: shortlist pages
                   │
          JEV: one shared request
           ┌───────┼──────────────┐
           ▼       ▼              ▼
      Policy     FAQ           Billing
      update     conflict      keep
           │       │              └── No edit
           ▼       ▼
      HOST LLM: draft / investigate
                   │
          JEV: verify source support
                   │
          CODE: publish each page
```

Illustrative plan, not a captured model result. A conflict requires review before editing.
[What moves to Jev?](references/technical-design.md#what-moves-to-jev) · [Full ingest diagram](references/technical-design.md#the-original-proposal-llm--jev-ingestion) · [Batched page decisions](references/technical-design.md#fan-out-batch-the-judgments-then-write)

## Architecture

![System architecture: Code retrieves and commits; Jev plans and verifies; the host LLM generates pages and answers.](assets/architecture.svg)

```text
OPEN WORLD                  BOUNDED DECISIONS                DURABLE MEMORY
LLM discovers knowledge  →  Jev selects the next action  →  Code commits Markdown
```

**[Read the technical design →](references/technical-design.md)** Ingest planning, retrieval, decision gates, storage, and extension boundaries.

## Get started

**Python 3.11+ · macOS / Linux · OpenRouter key · a skill-capable coding agent**

```bash
# Private repository: access required. No pip install.
gh repo clone JayYun98/jev-wiki ~/.codex/skills/jev-wiki

# Use OPENROUTER_API_KEY or the existing ~/.codex/global.env.
# Start a fresh agent session, then:
```

```text
Use $jev-wiki to build a wiki from these documents.
Verify every draft. Keep citations. Spend under $0.01.
```

<details>
<summary><strong>Prefer the CLI?</strong></summary>

```bash
python3 scripts/jev_wiki.py init ./vault
python3 scripts/jev_wiki.py ingest ./vault examples/refund-policy.md
# Host LLM drafts → publish verifies and commits.
python3 scripts/jev_wiki.py query ./vault "What is the refund window?"
python3 scripts/jev_wiki.py lint ./vault --semantic
```

[Complete draft → publish walkthrough](references/operations.md#complete-cli-walkthrough).
</details>

## Small surface. Real safeguards.

```text
sources/     immutable evidence     SHA-256 integrity
wiki/        readable Markdown     source-backed pages
.jev-wiki/   machine bookkeeping    index · history · cache · usage

✓ Atomic publication       ✓ Expected-revision checks
✓ Explicit uncertainty     ✓ Current-price budget preflight
✓ No automatic retries     ✓ No silent evidence truncation
```

**No server. No database. No runtime dependencies.**

## Estimated cost: 1,000 documents across five domains

**Planning estimate, not a benchmark.** USD API inference only, including the writer LLM. Start with **1,000 documents total** (200/domain); add **100 / 500 / 1,000 total per month** (20 / 100 / 200 per domain). Use five separately selected vaults, with no automatic cross-domain replication.

```text
                       SAME EXTRACTION + WRITING
                       13,000 input / 2,000 output tokens per document
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
       LLM-led wiki                              Jev Wiki
       Same LLM plans + verifies                 Jev plans + verifies
       +13,500 input / 750 output                +13,500 input / 0 output
                 │                                         │
       LLM semantic lint                         Jev semantic lint
```

| Ingestion + bounded maintenance | DeepSeek V4.1 Flash: LLM-led | DeepSeek + Jev | Qwen3.8 Flash: LLM-led | Qwen + Jev |
| :--- | ---: | ---: | ---: | ---: |
| Initial 1,000 documents, once | $4.88 | **$3.30** | $5.27 | **$3.46** |
| +100 documents / month | $0.51 | **$0.34** | $0.55 | **$0.35** |
| +500 documents / month | $2.46 | **$1.66** | $2.66 | **$1.74** |
| +1,000 documents / month | $4.90 | **$3.30** | $5.30 | **$3.46** |
| Year 1: initial + 12 × 100 | $11.03 | **$7.34** | $11.93 | **$7.69** |
| Year 1: initial + 12 × 500 | $34.43 | **$23.16** | $37.21 | **$24.28** |
| Year 1: initial + 12 × 1,000 | $63.68 | **$42.94** | $68.82 | **$45.02** |

Under these assumptions, replacing separate decision calls saves roughly **32–36%**, but only **$0.18–$1.83/month** at these volumes. A fused writer-only workflow can be cheaper than adding Jev; see the counterexample below. These user-selected models are comparison choices, not a claim about LLM Wiki adoption or equivalent quality.

<details>
<summary><strong>Prices, workload assumptions, formulas, and sensitivity</strong></summary>

### OpenRouter price snapshot — September 20, 2026 (KST)

| Model / selected provider | Input / 1M tokens | Output / 1M tokens |
| :--- | ---: | ---: |
| [DeepSeek V4.1 Flash](https://openrouter.ai/deepseek/deepseek-v4.1-flash) / Relace | $0.13 | $0.52 |
| [Qwen3.8 Flash](https://openrouter.ai/qwen/qwen3.8-flash) / Alibaba | $0.15 | $0.47 |
| [Jev 1.13](https://openrouter.ai/typesafe/jev-1.13) / TypeSafe | $0.042 | $0.00 |

These are paired input/output prices from individual endpoints, not a blend of the cheapest rate for each token type. DeepSeek uses the **V4.1** alias, not V4 Flash 0423 or 0731. Prices were read from the public endpoint API; [the saved snapshot](references/cost-pricing.json) includes exact endpoint names, retrieval time, and source URLs. No paid inference was needed.

The estimate assumes requests use these providers and uncached, short-context rates. This skill does not configure or pin the host writer provider. Automatic routing, failover, promotions, time-based pricing, and alias changes can change the bill. Cache discounts are excluded for both approaches.

### Per-document workload

Assume a focused **2,000-token text source**, six candidate excerpts/pages averaging 250 tokens, and **three 500-token page drafts** per source. These are synthetic sizing assumptions, not averages measured on 1,000 real documents. Count repeated source/context tokens on each call.

| Stage | Calls / document | Input / call | Output / call | LLM-led owner | Hybrid owner |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Extract entities and claims | 1 | 2,500 | 500 | Writer LLM | Same writer LLM |
| Plan updates against candidates | 1 | 4,500 | 300 | Writer LLM | Jev; no output-token charge |
| Draft or revise a page | 3 | 3,500 | 500 | Writer LLM | Same writer LLM |
| Verify each draft against sources | 3 | 3,000 | 150 | Writer LLM | Jev; no output-token charge |
| **Total writer generation** | **4** | **13,000 total** | **2,000 total** | Same | Same |
| **Total replaceable decisions** | **4** | **13,500 total** | **750 total** | LLM tokens | Jev input only |

Input allowances include instructions and supplied evidence. LLM output allowances include any billed reasoning tokens; a reasoning-heavy run needs a larger allowance. Identical decision input counts are a comparison assumption, not a claim that model tokenizers agree.

Use one bounded semantic lint pass after bootstrap: **5 domains × 4 pairs = 20 pairs**. Subsequently use **4 passes/month × 5 domains × 4 pairs = 80 pairs/month**, with 2,000 input tokens per pair and 100 output tokens for the LLM baseline. Jev output has no token charge. This is not exhaustive wiki lint; fixed top pairs may be revisited, and cache hits are conservatively ignored.

Five domains partition the corpus; they do not multiply document charges by five. The host chooses the vault. Cross-domain synthesis, full-corpus rescans, and automatic domain routing are not included. Candidate and page sizes stay bounded as the corpus grows. The bootstrap uses the same steady-state per-document allowance even while vaults are initially small.

### Formula and reproducibility

Let `p` and `q` be writer input/output USD per million tokens, `j = 0.042`, `N` documents, and `L` checked lint pairs:

```text
Shared writing = N × (13,000p + 2,000q) / 1,000,000
LLM-led        = Shared writing
                 + N × (13,500p + 750q) / 1,000,000
                 + L × (2,000p + 100q) / 1,000,000
Jev hybrid     = Shared writing
                 + (N × 13,500 + L × 2,000)j / 1,000,000

Initial = C(N=1,000, L=20)
Monthly = C(N=100 or 500 or 1,000, L=80)
Year 1  = Initial + 12 × Monthly
```

```bash
python3 scripts/estimate_cost.py  # offline; saved prices; no API calls
```

Calculations use unrounded values; display rounds to cents. Monthly totals exclude the initial build. Year-one totals include it once.

### Sensitivity and a cheaper baseline

At **+500 documents/month**, changing aggregate token usage gives:

| Token workload | DeepSeek LLM-led / hybrid | Qwen LLM-led / hybrid |
| :--- | ---: | ---: |
| 0.5× | $1.23 / $0.83 | $1.33 / $0.87 |
| 1× | $2.46 / $1.66 | $2.66 / $1.74 |
| 2× | $4.92 / $3.31 | $5.32 / $3.47 |
| 5× | $12.31 / $8.28 | $13.31 / $8.68 |

Multipliers apply to all billed input/output volume, not to document count. Large inputs must be split across requests to honor the current 16 KB source/draft and 28 KB decision-payload limits. A 2,000-token source is not guaranteed to fit 16 KB in every language. Splitting, larger page fan-out, retained multi-source evidence, and expanded context can change call counts beyond this simple scaling model.

If an efficient LLM agent **folds planning and review into writing** with no additional billed tokens and omits separate lint calls, its optimistic writer-only cost at +500/month is **$1.37 DeepSeek / $1.45 Qwen**, below the hybrid's **$1.66 / $1.74**. This counterexample has fewer independent checks, but shows why savings are not inherent to Jev. Cached LLM inputs or different review policies may also narrow or reverse the difference. The main table compares explicitly separated, equivalent stage budgets; it is not a measured cost of Karpathy's pattern.

Excluded: user queries/answers, extra conflict-resolution passes, retries, OCR/vision, embeddings/hosted search, taxes, credit-purchase fees, hosting, and agent subscription charges. This estimates direct OpenRouter API token costs, not a subscription bill. Writer quality and Jev decisions have not been benchmarked against each other on this corpus.

</details>

## Show the work

```bash
python3 -m unittest discover -s tests -v   # offline
python3 scripts/evaluate.py --budget 0.04  # opt-in, synthetic only
```

**11 live checks · 10 paid requests · $0.000347172** in the latest captured smoke run.
English + Korean contradictions, semantic duplicates, evidence gates, and abstention.
[Captured results](references/evaluation.json) · [Security boundaries](SECURITY.md)

<sub>A small smoke evaluation—not a production accuracy claim. Writer-LLM costs excluded. Source/draft limit: 16 KB; decision payload: 28 KB. Retrieval and pair checks are bounded, with explicit coverage. Defaults need domain calibration. See the operating contract for budgets, recovery, and limits.</sub>

---

<sub>Independent implementation inspired by the LLM Wiki pattern. Not affiliated with Jev, TypeSafe, OpenRouter, or other wiki projects. Private repository.</sub>
