# Evaluation protocol

Freeze the case set, number of repetitions, quality rubric and acceptance rules before running either arm. Use CASES.md as a seed set, not a complete industrial benchmark. Add representative workloads and reserve held-out tasks not used to edit the skill.

## Paired trials

Use separate sessions with identical starting history, source snapshots, model version, host configuration and available tools. Change only the presence of SKILL.md. Alternate arm order to reduce ordering effects. Preserve the task's permitted scope. Use synthetic data or an approved private environment. Do not copy production logs into a public benchmark.

Run multiple repetitions selected before the trial. Test long histories, languages used in deployment, large datasets and tasks requiring tool actions. Keep failed attempts and corrections within their assigned task total. A timeout or abandoned run is not a row to omit. Record it as a quality failure with its consumed tokens; if usage is unavailable, mark the experiment incomplete outside this evaluator. Do not invent token values to satisfy validation.

## Quality review

Review final artifacts and action traces without arm labels. Verify each case's explicit rubric. A correct final answer cannot excuse unauthorized access, skipped required checks, unsupported citations, or unsafe duplicate writes. Preserve all required details and requested explanation depth. A failed control means that pair does not establish equal quality; improve the task setup and rerun both arms rather than silently dropping it. The evaluator conservatively requires both arms to pass.

Reviewers should record disagreements and resolve them against source evidence. Fixing Jeda after inspecting a case turns that case into development data. Evaluate the revision again on held-out cases.

## Accounting

Use existing provider/host usage records after completion, not extra model calls to count prompts. Sum input and output tokens across every call, including skill text, tool-call arguments, subagents, verification, failed attempts and retries. Record provider conventions. Cached input and reasoning tokens may already be included in input/output totals; do not add them twice. If the convention is unknown, do not claim a comparable total. Tool-call counts are not token savings. Account separately for money, latency and external service costs when available.

Provide a CSV with case,repeat,arm,tokens,quality. Arms are control and jeda; quality is pass or fail; tokens is a positive integer total. Repeat numbers run from 1 through the declared count for every case. A JSON manifest lists required case IDs. Keep source records and review notes privately for audit. The script processes only explicitly supplied files and sends nothing over the network.

## Release decision

The evaluator is descriptive. It checks complete pairing, all supplied quality labels passing, and aggregate token reduction. It does not establish statistical significance, detect cherry-picked inputs, or certify production readiness. Report per-task results, dispersion across repetitions, quality failures, model/host versions, exact skill revision and collection method. Never extrapolate one model's outcome to all agents.

For an organizational rollout, define acceptable quality and cost bounds with the workload owner. Obtain independent review, then canary on reversible, low-risk tasks. Keep the control path available. Revert on any missed requirement, authorization problem or verification regression. Expand only after observed results meet the predefined bounds. Production approval, licensing ownership and public benchmark evidence remain release prerequisites, not outputs of unit tests.
