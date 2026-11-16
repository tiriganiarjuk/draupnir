<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- DO NOT EDIT THE PRELUDE. Before editing ANY part of this file, read     -->
<!-- /Users/johnny/ai/CONTEXT_MANAGEMENT_SYSTEM.md — the KFM section        -->
<!-- defines what this file is for and why it is not linked from anywhere.   -->
<!--                                                                          -->
<!-- DO NOT LINK THIS FILE. Not from the CONTEXT_MAP, not from CLAUDE.md,    -->
<!-- not from the README. Its name is uninformative on purpose.              -->
<!--                                                                          -->
<!-- Entries are FAILURE SHAPE with concrete facts routed out. An entry that -->
<!-- names files and functions is a clock: it will outlive them and then     -->
<!-- assert something false to a reader who arrived here because something   -->
<!-- had already gone wrong.                                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# KFM — Draupnir

Known failure modes. Each entry records something that actually went wrong here, badly
enough or often enough to be worth writing down: a mistake that kept recurring, one that
was tedious to rediscover, or one that cost hours nobody wanted to spend twice.

**This file is deliberately not linked from anything.** Not the CONTEXT_MAP, not CLAUDE.md,
not the README. It has a name that tells you nothing on purpose. That is not tidiness — it
is the point:

> A list of failure modes read *before* you have a model of the project is not a warning,
> it is a set of suggestions. Naming a mistake supplies it. And a vivid catalogue of
> concrete failures shadows the orientation gate it sits above — a reader absorbs the
> stories, feels informed about the project, and skips the documents that would actually
> have oriented them.
>
> Read at the right moment — when something has already gone wrong, or when you are about
> to touch a part with a known history — the same entries are worth what they cost. The
> content is not the problem. The timing is.

The mechanism for *when* a reader gets sent here is undecided. Until it is decided, nothing
points here, and that is intentional rather than an oversight.

**If you have landed here anyway:** read it as history, not as instruction. Nothing below
is a description of the tree as it stands now — check anything concrete against the code
before acting on it.

**Maintenance:** an entry retires when its vector is gone. A trap guarding code that no
longer exists is worse than no trap, because it is a confident false claim in the one
document a reader reaches for after something has already broken. Nothing automatic
enforces this.

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- EVERYTHING ABOVE THIS LINE IS THE PRELUDE — DO NOT MODIFY              -->
<!-- EVERYTHING BELOW IS PROJECT-SPECIFIC AND GROWS ONLY FROM REAL FAILURES -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

---

### A step that turns references into something else
**Detection:** If you find yourself writing a function, a validator or a pass whose job is to look a reference up and replace it with the thing it names...
**Why it's wrong:** A reference is a graph edge and stays the string it was authored as. A lookup step creates a half-formed state every consumer then has to handle, and it was built and scrapped here more than once.
**Recovery:** `~/ai/smidja/galdr/context/DRAUPNIR_ELEMENT.md` § Loading is the pipeline, and § Why a graph.

### Loosening a type that both loading and output use
**Detection:** If you find yourself widening a shared type so that input parsing will accept one more shape, or writing an input model by hand...
**Why it's wrong:** A type shared between input loading and schema output reaches every generated schema, so loosening it for the loader's convenience loosens the whole pipeline's validation at once. Input models are generated from the exported schemas, which is what keeps the validator and the parser the same definition.
**Recovery:** `~/ai/smidja/galdr/context/DRAUPNIR_ELEMENT.md` § The self-hosting loop, and § Why a graph.

### A conditional whose `if` matches when the predicate field is absent
**Detection:** If you find yourself emitting an `if`/`then`/`else` whose `if` block constrains a property without also requiring it...
**Why it's wrong:** A JSON Schema `if` that only constrains a property is satisfied when that property is missing, so the branch applies to data the condition was never meant to cover.
**Recovery:** `~/ai/smidja/galdr/context/VERDANDI_ELEMENT.md` § Conditionals for what each keyword must mean; the conditional builders in the transform zone for where it is emitted.

### Testing for a dot anywhere to find a cross-section predicate
**Detection:** If you find yourself deciding whether a predicate reaches another section by checking whether its target contains a dot...
**Why it's wrong:** Scope is carried by one position, not by the presence of a character, and a containment test misclassifies targets at the schema root.
**Recovery:** `~/ai/smidja/galdr/context/VERDANDI_ELEMENT.md` § Conditionals.

### Rewriting a schema's references to its own type during export
**Detection:** If you find yourself applying one replacement pass over every type name in an exported input schema...
**Why it's wrong:** The model being exported must be left out of the pass that rewrites reference fields, or the schema replaces references to itself and comes out corrupted while still looking well-formed.
**Recovery:** `~/ai/smidja/galdr/context/DRAUPNIR_ELEMENT.md` § The self-hosting loop for what the export is for; the schema-export transform for the pass itself.

### Expressing "may be absent" as a nullable wrapper
**Detection:** If you find yourself wrapping a section or field so that it accepts either its schema or null...
**Why it's wrong:** The data format has no null and the generated models give absent and null the same type, so the wrapper adds a branch nothing downstream can tell apart. Absence is expressed by the zone.
**Recovery:** `~/ai/smidja/verdandi/PLAN_SCHEMA_ZONE_UNIFICATION.md`.
