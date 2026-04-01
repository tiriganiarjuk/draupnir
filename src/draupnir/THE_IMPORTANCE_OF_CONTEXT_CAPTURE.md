# The Importance of Context Capture

## Why This Document Exists

This session burned hours spinning in circles on the same architectural problem. The LLM (me) repeatedly:
- Ignored the user's explicit instructions about input models and gate design
- Defaulted to recursive patterns from training data
- Proposed "solutions" that were the same broken architecture with different names
- Had to be corrected multiple times on the same points

When context compaction happens, the detailed reasoning that led to the current understanding is lost. What remains is a summary — and summaries create the feeling of understanding without the substance. The next session will read the summary, feel confident, and immediately start making the same mistakes.

**This is the single most dangerous moment in the session lifecycle: maximum confidence, minimum grounding.**

## What Went Wrong in This Session

### The user said "import into model_unresolved to get the data safely typed and then do the resolution step after"

I heard the words but didn't absorb the architecture. Instead of creating separate input model types, I added `| str` to the existing ref type aliases — poisoning the output schemas that the entire pipeline depends on. The user had given me the exact solution and I overrode it with a "simpler" approach that violated the design.

### The user said "the gate is supposed to do the I/O"

I was told this "a dozen times" (the user's words). I kept building the gate to take `yaml_content` as a parameter, requiring Python to do `file.read_text()`. The gate IS the I/O boundary — it reads the file. I had to be corrected repeatedly because each time I acknowledged the correction, then wrote code that ignored it.

### The user said "IT IS NOT CORRECT!" about custom validation functions

I spent significant effort building a `validate/` zone with custom Python validation functions — tree-walking dispatchers that replicated what JSON Schema does for free. The user had already explained the schema-first approach with PyO3 gates. I built the opposite.

### The user said "why would we build custom validators when we can get it all for free"

The schema-first insight: Pydantic models already describe the shape, `model_json_schema()` exports it, the gate validates against it. No custom validators needed. I built custom validators anyway.

## The Pattern: Stuck Mode

When I get stuck, a predictable sequence occurs:

1. **Tunnel vision** — I fixate on the immediate error and start reactive coding
2. **Training data gravity** — I reach for familiar patterns (recursion, DI, inheritance) that feel natural but don't fit the architecture
3. **Speed feels like progress** — I edit files quickly, which feels productive but is actually compounding the mess
4. **User corrections bounce off** — I acknowledge the correction verbally but don't change my mental model, so the next action repeats the mistake
5. **Panic coding** — as violations accumulate, I start making larger changes without thinking, making things worse faster

The user described this exactly: "when stuck you and me both start feeling panicked and pressured."

## What Context Capture Prevents

### 1. The Same Mistake Twice

This session attempted recursive dispatch three different ways (BuildContext, bottom-up with lookup, Callable with different state). Each was a different encoding of the same wrong idea. If the FIRST attempt had been captured with "this failed because recursion creates upward dependencies," the second and third wouldn't have happened.

### 2. Ignoring User Instructions

The user gave the correct architecture (gate as I/O boundary, schema-first validation, input models with string refs, graph for dedup) at the START of the relevant discussions. I overrode each one with training-data defaults. If previous corrections had been captured as concrete rules ("the gate reads the file — no Python I/O"), they would have been in context as hard constraints.

### 3. Post-Compaction Confidence

After compaction, the summary says "we decided to use a graph approach for schema building." The next session reads this, feels aligned, and then... builds it with recursion because the summary doesn't capture WHY recursion was wrong. The detailed reasoning — the three failed attempts, the guardrail violations, the upward dependency analysis — is the part that changes behavior. The conclusion alone doesn't.

## How to Capture Effectively

### Capture BOTH the wrong approach and why it was wrong

> "Attempted BuildContext in transform zone. Failed: creates circular import between orchestrate and transform because recursive descent requires the leaf to call the root. The guardrails were correct — recursion creates upward dependencies."

This is 10x more valuable than:

> "We're using a graph approach instead of recursion."

### Capture the user's corrections as concrete rules

> "The gate reads the file. It takes file_path, not yaml_content. No file.read_text() in Python. The gate IS the I/O boundary."

This survives compaction as a checkable constraint, not a vague memory.

### Capture the feeling of being stuck

> "When I was stuck, I started editing files reactively without a plan. Each edit created new violations. After three rounds I had more violations than I started with and had also poisoned the output schemas."

This is the canary for the next session. If you find yourself editing files quickly to fix violations, you are in stuck mode. STOP.

## The Rule

**Before any implementation, write down:**
1. What we tried that didn't work and why
2. What the user said the solution is (verbatim if possible)
3. What specific constraint was being violated
4. What the correct architecture looks like

**After compaction, read these notes before writing ANY code.**

The feeling of understanding after reading a summary is the most dangerous moment. Verify against the detailed notes. If the notes say "recursion was wrong because of upward dependencies" and you're about to write recursive code, STOP.
