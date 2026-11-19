# Decisions in practice

These examples illustrate the procedure. They are not benchmark observations.

## Reformatting does not refresh evidence

The agent has the complete, authorized invoice table and has checked the selected IDs. The user asks for the same selection in JSON. The agent converts the existing selection and validates the output. Searching for the invoices again adds nothing if the source and freshness requirement have not changed.

If the user changes the overdue threshold, the prior selection is insufficient. The agent recalculates from all source rows. If the user asks whether payment arrived today, an old table is insufficient even when the threshold stays the same.

## A summary is not an exact source

A policy summary says that ordinary records expire after 30 days. The user asks for every exception. The agent must retrieve the relevant original sections if the available evidence omits definitions, legacy treatment, disputes, or legal holds. Reusing an incomplete summary would save work by losing information.

An exhaustive request requires every relevant section and page. The smallest complete unit may be the entire document.

## Independent reads can share a batch

The agent needs three unrelated source files before making a decision. It can read them together if none depends on another result. It must not batch a write with a check that assumes the write has already completed.

## An uncertain write is not permission to repeat it

A payment request times out. The agent checks the operation status or uses the service's idempotency mechanism before retrying. Jeda does not authorize payments or relax the host's approval requirements.

## Verification belongs after the final change

The tests pass. The agent then edits the boundary condition again. The old test result no longer verifies the current code. The agent reruns the required tests and reports their actual result.

## Stopping depends on completion

The requested deliverable exists, coverage is complete, and required checks passed. Another search with no missing fact can stop. A requested explanation or unresolved conflicting source still belongs in the answer; it is not optional work to delete.
