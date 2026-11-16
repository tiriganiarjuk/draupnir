# Draupnir — Context Refresh Protocol

## STOP. Read this before writing any code.

You have context from a compaction summary or from earlier in this session. You feel like you understand this project well enough to start working. **You are almost certainly wrong.**

After compaction, you have a summary — not understanding. The summary preserves conclusions but loses reasoning, constraints, and the specific shapes of things. You will produce output that looks right, compiles, and silently violates the project's architecture because the summary told you WHAT but not HOW or WHY NOT.

**This has happened before.** Previous sessions in this project have produced output that compiled, passed review, and implemented the wrong architecture — work that had to be thrown away.

None of them felt uncertain while doing it.

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- NOTE what is NOT above: worked examples of the failures.               -->
<!-- Naming a mistake in the most-read position on the page supplies the    -->
<!-- mistake — for a reader, negation and instruction are the same tokens.  -->
<!-- The assertion that scrapped work happened carries the force; the       -->
<!-- enumeration only plants patterns. Specific failures live in KFM.md.    -->
<!-- ══════════════════════════════════════════════════════════════════════ -->

**The test:** Can you state three specific constraints of this project that diverge from how you'd normally write this code? Not "I should be careful" — actual constraints, with reasons. If you can't, you don't have enough context to write code. Orient via the CONTEXT_MAP `@import`ed below before proceeding — start with its orientation gate.

---
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- EVERYTHING ABOVE THIS LINE IS STANDARDIZED — DO NOT MODIFY            -->
<!-- EVERYTHING BELOW THIS LINE IS PROJECT-SPECIFIC                        -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
---

## Project Instructions

<!-- Behavioral rules: HOW to work in this project. Never WHAT exists in it.
     Nothing here names a file, a function, a directory, or a count. -->

- **Write one file, then read the feedback.** Guardrail feedback arrives on every file you write. Follow its direction before writing the next file, so each finding lands on a small surface.
- **Fail closed.** A read or a validation counts as a success only when it is typed as one. A refusal stops the run and is reported with its failure class.
- **Change generated code at its source.** Edit what it is generated from, then regenerate.
- **A compiler change is finished when its output is proven.** Run the drift check against every project, then run the downstream cascade or hand it off by name.
- **Shared types are changed with the user.** A type used by both input loading and schema output reaches every downstream schema, so a change to one is agreed before it is made.
- **Every function is a public, composable unit**, named without a leading underscore.

---

## How you orient — first time or recovery (same thing)

Orienting and recovering are one act: read the project's main documents, **routed by the
`CONTEXT_MAP` auto-included below** — start with its **orientation gate**, which *is* the
recovery-source list. If already verifiably oriented you needn't re-read everything; the map
always tells you where things live.

---

@CONTEXT_MAP.md
