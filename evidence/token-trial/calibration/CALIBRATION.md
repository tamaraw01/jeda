# Usage accounting calibration

Ran before any benchmark, on 2026-11-20, against the local gateway
`http://localhost:20128/v1/chat/completions`, model `ag/claude-sonnet-4-6`
(response label `claude-sonnet-4-6`).

Purpose: decide whether gateway `usage` can carry a token-savings claim at all.
Byte counts alone cannot; earlier trials compared bytes and calls.

## Method

Six fixed prompts (two short, two medium, two long) shuffled with seed 11920,
`temperature: 0`, `max_tokens: 12`. Each prompt was sent twice by its own
independent call, so identical request hashes exist in pairs. Full request and
response bodies are in `records.json`; the authorization header is not stored.

Required payload flags, both found by failure first:

| Flag | Without it | With it |
|---|---|---|
| `stream: false` | SSE chunks returned, JSON parse fails | one JSON completion |
| `stream_options.include_usage: true` | usage omitted | usage returned |

Model must be the `ag/` prefixed route. The bare alias `claude-sonnet-4-6`
returns HTTP 404 `No active credentials for provider: anthropic`.

## Result

| Label | Requests | Request bytes | prompt_tokens | completion_tokens | token spread |
|---|---:|---:|---:|---:|---:|
| short | 2 | 275 | 2830 | 5 | 0 |
| medium | 2 | 6562 | 4630 | 4 | 0 |
| long | 2 | 25413 | 10030 | 4 | 0 |

Every request hash repeats exactly and every repeat returned the same totals.

Least squares over the six points:

```text
prompt_tokens = 2751 + 0.28643 x request_bytes     max abs error 0
```

`total_tokens` equaled `prompt_tokens + completion_tokens` in all six records.

## What this establishes

- Identical requests returned identical input usage in these three probe pairs.
- Reported input increased with context length on this route for these probes.
- `total_tokens` arithmetic is internally consistent in these six records.

The linear fit is descriptive only. The probes repeat similar English records;
this does not establish a tokenizer formula for arbitrary text. The intercept
is not proof of a hidden prompt, a gateway estimate, or billed tokens. Output
usage must be recorded rather than inferred from input bytes.

## What this does not establish

- Billed cost. Prompt caching, cache-write pricing and quota units are provider
  side and were not reconciled against a provider usage panel.
- A stable model deployment. Labels alone do not prove backend revision.
- Cache semantics. Responses do not expose separate cache counts here.
- A universal bytes-to-token ratio or explanation of the intercept.

## Consequences for the benchmark

The candidate instruction block is paid on every call. Reuse must therefore
remove a call often enough to outweigh the block. Because the block is a fixed
per-call cost and a saved call is roughly the payload it never sent, the
break-even ratio is `block_bytes / payload_bytes` avoided calls per call. A
smaller block lowers it. That ratio, not the call count, is what trials test.
