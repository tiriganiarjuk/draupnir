# How to Get Unstuck

## Recognize the Warning Signs

You are stuck when:
- You've tried the same pattern more than once with different names
- Violation counts are going UP not down
- You're editing files reactively without reading the full picture first
- You feel confident and fast (pattern matching, not thinking)
- The user has corrected you on the same point more than once
- You're adding workarounds to satisfy constraints instead of redesigning

The user and I both feel panicked and pressured when stuck. That pressure drives exactly the wrong behavior: faster coding, less thinking, more violations, more pressure. The spiral must be broken.

## Step 1: STOP

Do not write another line of code. Do not edit another file. Do not propose another fix. STOP.

Say: "I'm stuck. Let me stop and think about this."

This is not weakness. This is the collaboration working. The cost of stopping for 10 minutes is negligible. The cost of another hour of spinning is catastrophic.

## Step 2: TALK

Before looking for solutions, understand the problem. Talk with the user:

- "What am I not seeing?"
- "Can you describe the architecture you have in mind?"
- "What is the actual constraint I keep violating?"

The user has the vision. You have implementation capability. When you're stuck, you've lost sight of the vision and are substituting training-data patterns. The user's words are the way back.

**Listen for the correction, not just acknowledge it.** "The gate reads the file" means STOP putting file.read_text() in Python. Not "ok I understand" followed by the same code. If the correction doesn't change your next action, you didn't hear it.

## Step 3: Use Opus Agents for Brainstorming

When stuck on an architectural problem and you need new ideas — not just more of the same pattern matching — use opus agents. They have the same capabilities but independent context, which means they won't be trapped in the same stuck loop you're in.

### Single agent for focused research

When you need to understand existing code before proposing changes:
```
Agent(subagent_type="Explore", model="opus", prompt="Map the complete data flow for X...")
```

### Multiple identical agents for divergent solutions

When you need genuinely different approaches — not variations of the same idea:

Launch 2-3 agents with **identical instructions** but ask each to propose a solution. Then:
- Look for **outliers** — solutions that are structurally different from what you've been trying
- Look for **agreement** — if 2 of 3 agents converge on the same approach, it's likely sound
- Look for the **intersection** — what properties do all solutions share? That's the invariant.

The key: if all agents propose the same pattern you've already tried, the prompt is too narrow. Broaden it: "What architectural approaches exist for this problem? Consider approaches from different paradigms."

### Plan agents for validation

After brainstorming, use a Plan agent to validate the approach against the constraints:
```
Agent(subagent_type="Plan", model="opus", prompt="Given these constraints [zone rules, level bands, import boundaries], does this approach work? Identify violations before implementation.")
```

## Step 4: Check Against Guardrails BEFORE Coding

Before writing a single line:
1. Will any new file import across zones? (transform ↛ impure, transform ↛ orchestrate)
2. Will any new parameter be a Callable? (no_callable_params)
3. Will any existing type alias change? (shared types affect all consumers)
4. Will any new class be created outside structure/? (v2_classes_only_in_structure)

If the answer to any of these is "yes," the approach has a fundamental problem. Go back to Step 2.

## Step 5: Incremental Implementation

When you have an approach that passes the guardrail pre-check:
- One file at a time
- E2E test after each file
- If violations appear, STOP — do not fix them reactively
- Read the violation, understand what it's telling you about the architecture
- If the violation count goes up, revert and go back to Step 2

## The Meta-Rule

**If you can't solve the problem while staying within the guardrails, you haven't found the right architecture yet.**

The guardrails are not obstacles. They are diagnostic tools. When they fire, they're telling you something about the design. The solution is never to work around them — it's to listen to what they're saying and redesign.

In this session, the guardrails said:
- `no_callable_params` → "recursion creates hidden upward dependencies"
- `v2_import_boundaries` → "transform cannot depend on orchestrate"
- `impure_module_quarantine` → "pure code cannot reach into impure"

Together they said: **recursive dispatch doesn't fit this architecture.** The solution was not to make recursive dispatch fit. It was to replace it with a graph — a fundamentally different approach that doesn't need upward dependencies because it processes linearly.

The guardrails were right all along.

## Applicable Beyond This Session

This pattern — stuck → panic → reactive coding → more violations → more panic — is not specific to this problem. It will happen again on a different problem. When it does:

1. STOP
2. TALK
3. AGENTS (brainstorm, don't just research)
4. GUARDRAIL PRE-CHECK
5. INCREMENTAL IMPLEMENTATION

The steps are the same every time. The specific problem doesn't matter. The process does.
