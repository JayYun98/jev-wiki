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

**Two alternatives: the LLM alone, or that same LLM + Jev.** Both read existing content to decide where to split, revise, or update pages; both include extraction, writing, and verification. This estimate now assumes **a full model-based rescan on every arrival**, rather than only a retrieved shortlist.

![Estimated full-domain rescan costs: LLM only versus the same LLM plus Jev, including corpus growth.](assets/cost-comparison.png)

**Base case:** 1,000 initial documents total, five balanced domains, 2,000 retained tokens/document. Each new document rereads its entire domain, including earlier arrivals in the same month. Monthly additions are totals across all five domains. Estimates are USD API token charges, not observed bills.

| Workload | DeepSeek only | DeepSeek + Jev | Qwen only | Qwen + Jev |
| :--- | ---: | ---: | ---: | ---: |
| Initial 1,000 | $34.96 | $16.91 | $39.64 | $17.07 |
| Month 1 +100 | $6.80 | $3.19 | $7.74 | $3.21 |
| Month 12 +100 | $13.40 | $6.20 | $15.28 | $6.21 |
| Month 1 +500 | $39.98 | $18.69 | $45.54 | $18.77 |
| Month 12 +500 | $205.03 | $93.77 | $234.19 | $93.85 |
| Month 1 +1,000 | $94.97 | $44.21 | $108.23 | $44.37 |
| Month 12 +1,000 | $755.16 | $344.51 | $862.84 | $344.67 |

Month 12 is the cost of that month alone after eleven months of accumulation. **Monthly cost increases even when monthly arrivals stay constant.** Bootstrap is separate and rereads the growing initial corpus as the first 1,000 documents are ingested sequentially.

```text
New document
    │
    ├─ LLM only:     read whole domain in batches → decide edits → LLM writes/checks
    └─ LLM + Jev:    Jev reads whole domain in batches → LLM writes → Jev checks

More retained documents → more repeated input → increasing cost per new document
```

<details>
<summary><strong>Year-one totals, all-domain scans, enterprise scale, and assumptions</strong></summary>

### First year: bootstrap + twelve growing months

| Workload | DeepSeek only | DeepSeek + Jev | Qwen only | Qwen + Jev |
| :--- | ---: | ---: | ---: | ---: |
| Year 1 +100/mo | $156.12 | $73.23 | $177.75 | $73.58 |
| Year 1 +500/mo | $1,505.03 | $691.64 | $1,718.03 | $692.76 |
| Year 1 +1,000/mo | $5,135.70 | $2,349.17 | $5,866.03 | $2,351.25 |

### If every arrival rereads all five domains

The base case assumes domain routing is already known. Cross-domain review reads the entire retained corpus instead:

| Workload | DeepSeek only | DeepSeek + Jev | Qwen only | Qwen + Jev |
| :--- | ---: | ---: | ---: | ---: |
| Initial 1,000 | $154.99 | $71.51 | $176.83 | $71.67 |
| Month 1 +100 | $32.00 | $14.66 | $36.55 | $14.67 |
| Month 1 +500 | $190.02 | $86.94 | $217.04 | $87.02 |
| Month 1 +1,000 | $455.07 | $208.01 | $519.83 | $208.17 |
| Month 12 +1,000 | $3,755.99 | $1,709.51 | $4,292.83 | $1,709.67 |

### Enterprise: full rescanning becomes the bottleneck

These are separate hypothetical starting corpora, still divided into five domains. Each row shows **one month's** cost, including growth during that month, excluding bootstrap. They are workload extrapolations, not validated enterprise capacity or a deployment recommendation.

| Existing documents → new this month | DeepSeek only | DeepSeek + Jev | Qwen only | Qwen + Jev |
| :--- | ---: | ---: | ---: | ---: |
| 10,000 → +10,000 | $9,051.95 | $4,127.55 | $10,343.32 | $4,129.15 |
| 100,000 → +10,000 | $63,066.95 | $28,697.55 | $72,083.32 | $28,699.15 |
| 100,000 → +100,000 | $900,744.54 | $409,825.50 | $1,029,533.25 | $409,841.50 |

At 100,000 existing documents plus 10,000 arrivals, the chosen batching policy requires **105 million Jev scan requests in one month**. Rate limits, elapsed time, orchestration, and failure handling make this unsuitable as a practical architecture, regardless of token savings. The current single-owner CLI is not an enterprise service.

For enterprise use, full **local index scans** need not become full **model input scans**. Incremental indexing, changed-claim tracking, document dependencies, and retrieval can identify affected pages before inference. Global reviews can run separately at a controlled cadence. Jev reduces decision-token cost; it does not remove the quadratic growth of repeated full scans. Measure retrieval misses and maintenance coverage before reducing the scope.

### Current prices and selected providers

OpenRouter endpoint snapshot, **September 20, 2026 KST**, USD per million tokens:

| Model / provider | Input | Output |
| :--- | ---: | ---: |
| [DeepSeek V4.1 Flash](https://openrouter.ai/deepseek/deepseek-v4.1-flash) / Relace | $0.13 | $0.52 |
| [Qwen3.8 Flash](https://openrouter.ai/qwen/qwen3.8-flash) / Alibaba | $0.15 | $0.47 |
| [Jev 1.13](https://openrouter.ai/typesafe/jev-1.13) / TypeSafe | $0.042 | $0.00 |

[Saved API pricing snapshot](references/cost-pricing.json) includes endpoint names, retrieval time, and public source URLs. Input/output rates come from the same provider. No cache discounts, subscription pricing, or assumed model-quality equivalence. Routing, provider pricing, and promotions may change; the host writer is not pinned by this skill. These are user-selected comparison models, not a measured LLM Wiki popularity ranking.

### Token and batching assumptions

| Work per new document | Input tokens | Output tokens | LLM only | Same LLM + Jev |
| :--- | ---: | ---: | :--- | :--- |
| Extract + draft/revise three pages | 13,000 total | 2,000 total | LLM | Same LLM |
| Consolidate plan + verify three drafts | 13,500 total | 750 total | LLM | Jev, no billed output |
| Read **every retained document in scope** | 2,000 per retained document | See scan batch | LLM | Jev |
| Each scan batch: repeat new source + instructions | 2,500 extra | 300 decision tokens | LLM | Jev, no billed output |

Each source contributes **2,000 net retained tokens** to the maintained corpus; this is an explicit proxy for the aggregate pages that need rereading, not a claim that raw sources and wiki pages are identical. Three page edits do not necessarily create three new pages. If retention, duplication, or page fan-out changes, replace this assumption. Edits may include splitting or consolidation, but only three generated page drafts are budgeted per arrival. More rewrites require extra generation.

- **LLM-only scan batch:** 12 retained documents, up to 26,500 input tokens including the repeated new source. The LLM may batch more efficiently; this is a chosen working-context policy, not its maximum context window.
- **Jev scan batch:** 2 retained documents, up to 6,500 input tokens including the new source. This conservatively targets the current 28 KB serialized-payload limit for compact English text. Token-to-byte ratios and question overhead must be checked; some inputs need smaller batches.
- The same old content is read by both approaches. Jev pays more repeated-source overhead because its batches are smaller. Generation and verification budgets are identical between approaches.
- All documents are distinct; no cache hits, duplicate skips, or early exits. Domains receive round-robin arrivals and no deletions. Old content is reviewed for changes on each arrival.
- Multi-batch selection/consolidation is **hypothetical**, not implemented in this repository. Current ingest sends only a retrieved shortlist. The fixed consolidation allowance assumes few relevant changes; many affected pages or multi-level result aggregation increase cost further.
- No extra periodic lint is added: each arrival already triggers a full old-versus-new review. This does not compare every old page against every other old page, or guarantee whole-wiki consistency.

**The earlier few-dollar estimate applied only to bounded retrieval. It did not include these full rescans and is not the headline estimate here.** A local lexical scan of all files has CPU/I/O cost but no API token charge; sending their contents to either model does.

### Formula and reproduction

For an arrival with `n` existing documents in scope, let `B` be the batch size:

```text
scan_calls(n, B) = ceil(n / B)
scan_input(n, B) = 2,000 × n + 2,500 × scan_calls(n, B)

LLM-only cost / arrival:
  [(26,500 + scan_input(n, 12)) × input_price
   + (2,750 + 300 × scan_calls(n, 12)) × output_price] / 1,000,000

Same LLM + Jev cost / arrival:
  [13,000 × LLM_input_price + 2,000 × LLM_output_price
   + (13,500 + scan_input(n, 2)) × Jev_input_price] / 1,000,000

Domain scan: n = floor(total existing documents / 5)
All-domain scan: n = total existing documents
Sum over each arrival; increment the corpus after every arrival.
Month m starts with 1,000 + (m - 1) × monthly_arrivals documents.
Year 1 = bootstrap + sum(months 1 through 12), not 12 × month 1.
```

```bash
python3 scripts/estimate_cost.py          # offline calculation + arithmetic checks
python3 scripts/estimate_cost.py --chart  # optional: requires matplotlib for chart build
```

The runtime remains standard-library-only. The chart is a documentation artifact. Display rounds to cents after calculating totals.

Input sizes, retention, batching, and output allowances are estimates, not measurements. Larger LLM batches or cached inputs may narrow or reverse the advantage; more reviews and rewrites may increase both bills. Reasoning tokens must fit the output allowance or be added separately. Excludes user queries/answers, extra conflict-resolution passes, retries, OCR/vision, embeddings/search services, infrastructure, taxes, credit-purchase fees, and agent subscriptions. No paid inference was performed to make this estimate.

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
