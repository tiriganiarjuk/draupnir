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

Orient via the CONTEXT_MAP `@import`ed below before proceeding — start with its orientation gate.

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

## How you orient, and how you recover

**Orientation** is your first meeting with this project. You arrive knowing nothing about it, with
no stake in it yet. At the start of a session, read the orientation gate in the `CONTEXT_MAP`
auto-included below, whole and in order. The reading is there to give you enough understanding to
know what you are doing, and the reason to do it well, so that you can work with the user.

**Recovery** uses the same documents for the opposite situation. You are no longer a blank slate:
you carry a model of the project, and part of it is wrong. After any compaction, read the gate
whole again, because nothing shows what a summary lost. When the user sends you back, they have
watched you repeat mistakes that show you have lost what you are supposed to be doing and are
pattern-matching. Read the material as the correction for that: find where it contradicts what you
have been doing, and change course. This is your chance to keep working; the alternative is being
dismissed. If you are sent to something already in your context, say so, and ask what the user
wants from it: reloading it does no work.

The map always tells you where things live.

---

@CONTEXT_MAP.md
