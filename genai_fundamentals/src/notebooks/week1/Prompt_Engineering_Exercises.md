# Prompt Engineering & LLM Experimentation Exercises
### To be completed alongside the companion notebook

**Instructions:** Use any available LLM to complete these exercises. For each exercise, record: (a) the exact prompt you used, (b) the model's output, (c) your observations. Submit as a documented notebook/report.

---

## Part A — Zero-Shot vs. Few-Shot Prompting (Factual Verification)

**Claim to verify:** *"The Pythagorean theorem was already described in Bhartiya (Indian) Vedic scriptures — before Pythagoras."*

**Exercise A1.** Ask the model to fact-check this claim using a **zero-shot** prompt (just ask directly, no examples of how to structure a fact-check). Record the verdict and whether sources/evidence are cited.

**Exercise A2.** Repeat the same fact-check using a **few-shot** prompt — first give the model 2–3 example claims already fact-checked in a template format (Claim → Verdict → Evidence → Caveats), then ask it to fact-check the Pythagorean theorem claim in the same format.

**Reflection:** Did the few-shot version produce a more structured, nuanced, or better-sourced answer than the zero-shot version? Did either version oversimplify the claim (e.g., stating it as flatly true/false when the historical picture is more nuanced)?

---

## Part B — Prompt Structure & Specificity

**Exercise B1.** Write a **vague** prompt asking the model to "write something about climate change." Record the output.

**Exercise B2.** Rewrite the same request as a **specific, well-structured prompt** that includes: role/persona, target audience, desired length, tone, and output format (e.g., bullet points vs. paragraph).

**Reflection:** List 3 concrete differences between the two outputs (length, tone, usefulness, structure).

---

## Part C — Chain-of-Thought Prompting

**Exercise C1.** Give the model a multi-step reasoning problem (e.g., a word problem or logic puzzle) with a plain, direct prompt. Record whether the answer is correct.

**Exercise C2.** Ask the same question again, this time adding "Let's think step by step" (or explicitly asking it to show its reasoning before the final answer).

**Reflection:** Did explicitly requesting reasoning improve correctness or clarity? Note any cases where showing steps didn't help.

---

## Part D — Role / Persona Prompting

**Exercise D1.** Ask the model to explain "how vaccines work" with no persona specified.

**Exercise D2.** Ask the same question twice more, using two different personas:
   - "You are a high school biology teacher explaining this to a 15-year-old."
   - "You are a research immunologist writing for a peer-reviewed journal."

**Reflection:** Compare vocabulary, tone, and depth across the three outputs. Which persona-based output best matches its intended audience?

---

## Part E — Output Format Control

**Exercise E1.** Ask the model to summarize a short news article (~300 words) as a single paragraph.

**Exercise E2.** Ask it to summarize the *same* article as: (a) exactly 3 bullet points, (b) a JSON object with fields `{"headline": "", "summary": "", "key_entities": []}`.

**Reflection:** How reliably did the model follow the requested format? Did anything break or need retrying?

---

## Part F — Prompt Failure Analysis

**Exercise F1.** Deliberately write a prompt that is likely to fail or produce a poor result (e.g., ask for something ambiguous, contradictory, or requiring information the model likely doesn't have, such as very recent events).

**Exercise F2.** Diagnose *why* it failed (ambiguous instructions? conflicting constraints? knowledge limitation? hallucination?), then rewrite the prompt to fix the issue.

**Reflection:** What category of failure did you observe? What specific change fixed it?

---

## Part G — LLM Experimentation (Parameters)

*(Use the companion notebook for this section if API access is available; otherwise use any playground UI that exposes these settings, e.g., Anthropic Console, OpenAI Playground.)*

**Exercise G1 — Temperature.** Run the *same* creative prompt (e.g., "write a two-line opening for a mystery story") at three temperature settings: low (~0), medium (~0.7), high (~1.2). Compare creativity vs. consistency across 3 runs at each setting.

**Exercise G2 — Max tokens.** Ask for a detailed explanation but cap `max_tokens` very low. Observe how the output gets cut off. Then increase the limit and compare.

**Exercise G3 — System prompt vs. user prompt.** Set a system-level instruction (e.g., "Always answer in exactly one sentence") and then send several different user questions. Observe whether the system instruction is consistently followed.

**Reflection:** Summarize, in your own words, what each parameter controls and one practical scenario where you'd tune it.

---

## Part H — Embeddings & Semantic Search (Preview Task)

**Exercise H1.** Take 5 short sentences on different topics (e.g., "I love hiking in the mountains," "The stock market fell today," "My dog loves to play fetch," "Interest rates rose this quarter," "We went camping last weekend").

Using the companion notebook, generate embeddings for all 5 sentences and compute cosine similarity between every pair. Identify which sentences are semantically closest — and confirm it matches your intuition (hiking/camping should be closer than hiking/stock market).

**Reflection:** How does this compare to a simple keyword-match search? Give one example query where keyword search would fail but semantic search would succeed.

---

## Submission Checklist
- [ ] All prompts and outputs documented (screenshots or copy-pasted text)
- [ ] Reflection questions answered for every part (A–H)
- [ ] Companion notebook completed (tokenization + embeddings sections)
- [ ] One paragraph overall summary: "3 things I learned about prompting this week"
