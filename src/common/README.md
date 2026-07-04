# `common` — shared kernel (intentionally near-empty)

Reserved for cross-cutting primitives shared by the other packages — identifiers,
clocks, shared error bases — that will land here **as concrete needs appear**.

> Up one level: [`../README.md`](../README.md).

It is deliberately empty right now. That is a design decision, not an oversight:
per the project's "avoid premature abstraction" bias, a shared-kernel package
earns its contents only when two or more packages genuinely need the same
primitive. Until then, keeping it empty avoids inventing a home for abstractions
nobody uses yet. When something does belong here, add it with a note on *which*
packages share it and why it was lifted.
