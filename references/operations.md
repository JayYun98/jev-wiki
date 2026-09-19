# Operating contract

## Complete CLI walkthrough

Run from the repository root. Every paid command accepts `--budget USD` and `--env-file PATH`.
The environment variable takes precedence over the env file. The file is parsed as literal data,
never executed. Sources are transmitted to OpenRouter/its selected provider during semantic operations.

```bash
python3 scripts/jev_wiki.py init ./vault
python3 scripts/jev_wiki.py ingest ./vault examples/refund-policy.md > /tmp/jev-plan.json
```

Inspect the plan before following it. `create` means draft a new page; `update` identifies a
candidate to revise. `duplicate`/`skip` do not need another page; `review` needs investigation.
`page_type` suggests source/entity/concept/synthesis. `page_actions` independently assesses each
shortlisted page for update, conflict, link, keep, or review in the same request. `writer_role`
is a handoff hint for the host agent; no second model is configured or invoked by the CLI.
For this small example, the source is already suitable Markdown:

```bash
cp examples/refund-policy.md /tmp/refunds-draft.md
SOURCE_ID=$(python3 -c 'import json; print(json.load(open("/tmp/jev-plan.json"))["source"])')
python3 scripts/jev_wiki.py publish ./vault /tmp/refunds-draft.md \
  --page refunds --source "$SOURCE_ID" --expected new
python3 scripts/jev_wiki.py query ./vault "What is the refund window?"
python3 scripts/jev_wiki.py index ./vault
python3 scripts/jev_wiki.py lint ./vault
```

For an update, obtain the current revision from `status`, reread the existing page, and pass
`--expected REVISION_HASH`. Include all sources supporting retained and new claims by repeating
`--source HASH`. Concurrent changes cause a revision conflict; reread and reconcile rather than
retrying with a newly fetched hash blindly. Failed verification returns `written: false`.

An `already_ingested` source may still have no page if the previous drafting step was interrupted.
Use `ingest ... --reassess` to regenerate its plan. Original source bytes remain unchanged.

For complex sources, the host LLM first discovers entities/claims and writes focused text inputs.
It then uses the bounded plan to draft summaries, concepts, and synthesis pages. New names and
new explanations always come from that LLM, never from Jev. Multi-page updates are independent
verified commits, not one atomic transaction. Run `index` after a batch to rebuild the disposable
machine manifest; it contains IDs, titles, sources, links and revisions. Retrieval reads the
authoritative pages, so an out-of-date manifest cannot hide edited content.

## Reading results

- `query.route = answer`: the selected evidence is judged sufficient. Synthesize with citations.
- `query.route = retrieve_more`: missing, conflicting, or uncertain evidence. Search other sources or abstain.
- `verify.status = accepted`: draft claims passed the configured grounding gate, not a truth guarantee.
- `verify.status = review`: revise or seek evidence; no publication is authorized by this result.
- Lint `review`: the model is uncertain, or a claimed supersession lacks a strictly ordered pair of unambiguous ISO dates.
- `coverage.complete = false`: not every wiki page was considered. A candidate-level duplicate/new-page decision is provisional.
- `complete_pairwise_check = false`: do not report that the whole wiki is contradiction-free.

Choice/Score confidence is used as a review signal; Noul is the probability of a yes answer.
Confidence is optional in the API and missing confidence defaults to zero. Thresholds live in
`.jev-wiki/config.json`: `confidence=0.85`, `support=0.9`, `risk=0.1`, `top_k=6` initially.
These are starting policies, not calibrated guarantees. Preserve dates, qualifiers, and distinctions
between fact, allegation, and hypothesis in drafts.

## Budgets and failures

The client fetches current endpoint pricing before the first uncached inference and reserves the
cost of a full 32,000-token input. Nonzero output pricing or changed context limits stop execution
for review. After a response it reconciles against `usage.cost`; missing usage or unknown network
outcomes retain the reservation. A changed price exceeding the estimate stops further calls.

The budget is **per command/client**, not a persistent account spending limit. Usage records are
append-only events: `reserved` followed by `charged`, or `cache`. Do not add a charged event to its
corresponding reservation; unmatched reservations remain potentially charged. Summing actual charges
and unmatched reservations is appropriate for an overall session budget. Failed commands can have
paid requests; inspect `usage.jsonl` before a manual retry. The local estimate cannot guarantee a
provider will honor old pricing; configure a provider-side key limit for a strict billing boundary.

No request is automatically retried. Authentication errors, rate limits, malformed responses,
oversized inputs, missing evidence, and low confidence never fall back to a generative model.
An operation failure exits 2. Review outcomes exit 1 and still return usable JSON.

## Storage, recovery, and privacy

CLI commands acquire one nonblocking vault lock, including read commands that may write cache/usage.
The lock file is permanent; its existence does not mean a process is running. The OS releases the
advisory lock if a process exits. External editors do not honor it; expected revisions also protect
the target page from changes made while verification is running. The vault must be owned by one
trusted local user; it is not a sandbox against another process racing filesystem operations.

Sources are named by SHA-256 and checked when read. A page stores its source IDs in a leading HTML
comment. Previous raw revisions are copied into `.jev-wiki/history/PAGE/REVISION.md` before replacement.
To recover, copy a backup outside `wiki/`, remove its metadata comment, and republish with its source
IDs and the current target revision. Keep the entire vault in your regular backup or private Git
workflow. This tool does not silently initialize Git or upload the vault.

`cache/` is disposable and expires after one hour. Its key includes complete state, question criteria,
and the requested model. A mutable provider alias can change within that hour; remove cache entries
if immediate re-evaluation after a model update is required. Cache files contain decisions, while
sources and pages contain your content. Usage logs contain hashes, timestamps, model identifiers,
costs, and latency—not source text or keys. JSON command output can contain full candidate text;
treat captured output as private.

## API references

- [OpenRouter Decisions](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-questions-and-answers-request)
- [Official Jev cascade example](https://openrouter.ai/docs/cookbook/evaluate-and-optimize/jev-verified-cascade)
- [TypeSafe primitives](https://docs.typesafe.ai/primitives)

The runtime uses Python's standard HTTPS client directly. It does not require the OpenRouter SDK,
the TypeSafe SDK, LangChain, or a second inference provider.
