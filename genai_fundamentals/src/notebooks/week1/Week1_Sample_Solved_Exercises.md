# Sample Solved Exercises — How to Attempt the Prompt Engineering Worksheet

These are **worked examples** — one fully solved sample per section (A–H) — showing the level of detail and format expected. Follow this structure exactly for every exercise in your submission: **Prompt → Output → Reflection.**

> Note: The outputs below are illustrative samples written to show the expected pattern. Your actual outputs will vary depending on which model you use — that's fine, just document what you actually get.

---

## Part A — Zero-Shot vs. Few-Shot Prompting: Factual Verification (Sample: A1 + A2)

**Claim being checked:** *"The Pythagorean theorem was already described in Bhartiya (Indian) Vedic scriptures — before Pythagoras."*

**A1 — Zero-shot prompt:**
```
Fact-check this claim: "The Pythagorean theorem was already described in
Bhartiya (Indian) Vedic scriptures, before Pythagoras."
```
**Output:**
```
This is largely true. The Baudhayana Sulba Sutra, part of the Vedic corpus
and generally dated to around 800 BCE, contains a statement equivalent to
the Pythagorean theorem, along with specific right-triangle measurements
used for constructing fire altars. This predates Pythagoras (c. 570-495 BCE)
by several centuries. So the core claim checks out — the relationship was
documented in Vedic mathematical texts before Pythagoras' traditional dates.
```
*(Reasonably accurate, but stated as a flat "true/false" verdict with no
caveats about proof vs. discovery, or about even earlier Babylonian evidence.)*

**A2 — Few-shot prompt (fact-check template given first):**
```
Fact-check each claim using this format:
Claim → Verdict (True / False / Partly True) → Evidence → Caveats

Example 1:
Claim: "The Great Wall of China is visible from space with the naked eye."
Verdict: False
Evidence: Astronauts have repeatedly confirmed it is not distinguishable
from low Earth orbit without aid; it's too narrow relative to viewing distance.
Caveats: Many artificial structures are visible under specific conditions
(lighting, aids), so the claim persists as a popular myth.

Example 2:
Claim: "Einstein failed math in school."
Verdict: False
Evidence: School records show Einstein excelled in mathematics from a young age.
Caveats: The myth likely spread due to grading-scale confusion between
German and Swiss school systems.

Now fact-check:
Claim: "The Pythagorean theorem was already described in Bhartiya (Indian)
Vedic scriptures, before Pythagoras."
```
**Output:**
```
Claim: "The Pythagorean theorem was already described in Bhartiya Vedic
scriptures, before Pythagoras."
Verdict: Partly True
Evidence: The Baudhayana Sulba Sutra (~800 BCE), part of the Vedic Shrauta
tradition, states a rule equivalent to the Pythagorean theorem and lists
specific right-triangle triples used for altar construction — centuries
before Pythagoras (c. 570-495 BCE).
Caveats: (1) The Sulba Sutras present the rule as a practical/geometric
statement for construction, not a formal deductive proof in the Greek
mathematical sense — Pythagoras (or his school) is generally credited with
an early formal proof, not the discovery of the relationship itself.
(2) Even earlier evidence exists outside India: the Babylonian tablet
Plimpton 322 (~1800 BCE) shows Pythagorean triples in use over a thousand
years before both Baudhayana and Pythagoras. (3) Multiple ancient
civilizations appear to have independently discovered this geometric
relationship before it was named after Pythagoras.
```

**Reflection (sample):**
Both versions agreed on the core historical fact — the zero-shot answer wasn't *wrong*, but it presented the claim as a simple true/false statement and stopped there. The few-shot version, primed by the template's "Verdict / Evidence / Caveats" structure, produced a much more careful answer: it correctly labeled the claim "Partly True" rather than flatly "True," and surfaced two important nuances the zero-shot version missed entirely — (1) the distinction between *stating/using* a mathematical relationship and *formally proving* it, and (2) the existence of even older Babylonian evidence, which means "Vedic scriptures predate Pythagoras" is accurate but "Vedic scriptures were first" is not. **Takeaway:** for claims that sound like simple true/false questions but actually have historical nuance, few-shot examples that model *how to caveat* an answer are far more valuable than few-shot examples that just show output format — they push the model to actively look for the nuance instead of settling for the first plausible verdict.

---

## Part B — Prompt Structure & Specificity (Sample)

**B1 — Vague prompt:**
```
Write something about climate change.
```
**Output (excerpt):**
```
Climate change refers to long-term shifts in temperatures and weather patterns...
[generic 150-word overview, no clear audience or purpose]
```

**B2 — Specific, well-structured prompt:**
```
You are a science communicator writing for a general audience of high school
students. Write a 100-word explanation of climate change that:
- Uses simple, everyday language (no jargon)
- Includes one concrete real-world example
- Ends with one actionable takeaway
Format: a single paragraph.
```
**Output (excerpt):**
```
Climate change means our planet is slowly heating up because of gases like
carbon dioxide trapping heat in the atmosphere — like a blanket that's gotten
too thick. For example, glaciers in Greenland are melting faster than ever
recorded. The good news? Small actions add up: using less energy at home,
walking or biking short trips, and talking about it with others all help
slow the warming down.
```

**Reflection (sample):**
Three concrete differences: (1) **Length control** — B2 respected the 100-word constraint almost exactly, while B1 produced a generic-length response with no target. (2) **Audience fit** — B2's vocabulary ("blanket that's gotten too thick") is clearly tuned for teenagers, while B1 read like a textbook definition suitable for any reader. (3) **Actionability** — only B2 ended with a concrete takeaway, because I explicitly asked for one; B1 stayed purely descriptive. **Takeaway:** specificity doesn't just make the output "better" in a vague sense — it directly determines which concrete features (length, tone, structure) actually show up.

---

## Part C — Chain-of-Thought Prompting (Sample)

**C1 — Direct prompt:**
```
A store had 84 apples. They sold 3/7 of them in the morning and 2/5 of the
remainder in the afternoon. How many apples are left?
```
**Output:**
```
20 apples left.
```
*(Incorrect — direct answer, no reasoning shown, arrived at the wrong number.)*

**C2 — Chain-of-thought prompt:**
```
A store had 84 apples. They sold 3/7 of them in the morning and 2/5 of the
remainder in the afternoon. How many apples are left? Let's think step by step.
```
**Output:**
```
Step 1: Morning sales = 3/7 × 84 = 36 apples sold. Remaining = 84 − 36 = 48.
Step 2: Afternoon sales = 2/5 × 48 = 19.2 → but apples must be whole, so
        recheck the problem setup — assuming exact division, afternoon sales = 19.2,
        which suggests the numbers should divide evenly; recomputing carefully:
        2/5 × 48 = 19.2 (not whole) → flag this as a likely rounding issue in the
        problem itself, but mathematically, remaining = 48 − 19.2 = 28.8.
Final answer: ≈ 29 apples (with a note that the numbers don't divide evenly).
```

**Reflection (sample):**
The direct prompt gave a confident but wrong final number with zero visibility into *how* it got there — I had no way to catch the error without solving it myself. The chain-of-thought version not only got closer to a defensible answer, it also **surfaced a genuine issue with the problem itself** (the numbers don't divide evenly), which the direct version silently ignored. This is the key benefit of CoT: it doesn't just sometimes improve correctness, it makes the model's reasoning inspectable, so errors and edge cases become visible instead of hidden inside a single guessed number. **Takeaway:** for anything involving multi-step arithmetic or logic, always request reasoning — the "final answer only" mode is much more likely to fail silently.

---

## Part D — Role / Persona Prompting (Sample)

**D1 — No persona:**
```
Explain how vaccines work.
```
**Output (excerpt):**
```
Vaccines work by introducing a harmless piece or weakened form of a pathogen
into the body, prompting the immune system to produce antibodies...
```

**D2a — Persona: high school teacher:**
```
You are a high school biology teacher explaining this to a 15-year-old.
Explain how vaccines work.
```
**Output (excerpt):**
```
Think of your immune system like a security team that learns to recognize
troublemakers. A vaccine shows your body a "wanted poster" of a germ — not
the real dangerous germ, just enough of it to recognize later — so if the
real thing ever shows up, your body already knows exactly how to fight it off fast.
```

**D2b — Persona: research immunologist:**
```
You are a research immunologist writing for a peer-reviewed journal.
Explain how vaccines work.
```
**Output (excerpt):**
```
Vaccination induces adaptive immunity by exposing the host to attenuated,
inactivated, or subunit antigens, triggering both humoral (B-cell/antibody)
and cell-mediated (T-cell) responses, and establishing immunological memory
via long-lived memory B- and T-cells for accelerated secondary response...
```

**Reflection (sample):**
The default (D1) landed in the middle — accurate but somewhat generic. The teacher persona (D2a) used an analogy ("wanted poster") and completely avoided technical vocabulary, clearly matching a 15-year-old audience. The immunologist persona (D2b) used precise technical terms (humoral immunity, memory B-cells) appropriate for a journal audience, with no simplification at all. **Best match:** each persona output matched its intended audience well — this shows persona prompting is a reliable lever for controlling *vocabulary level and framing*, even when the underlying factual content stays the same.

---

## Part E — Output Format Control (Sample)

**E1 — Paragraph summary:**
```
Summarize this article in one paragraph: [article text]
```
**Output:**
```
The article discusses a new city policy to expand bike lanes across downtown,
citing reduced traffic congestion and a 12% rise in cyclist commuters...
```

**E2a — Bullet points:**
```
Summarize the same article in exactly 3 bullet points.
```
**Output:**
```
- City approves expansion of downtown bike lanes
- Cyclist commuting rose 12% following pilot program
- Officials cite reduced congestion as key motivation
```

**E2b — JSON format:**
```
Summarize the same article as a JSON object with fields:
{"headline": "", "summary": "", "key_entities": []}
```
**Output:**
```json
{
  "headline": "City Expands Downtown Bike Lanes",
  "summary": "The city approved an expansion of bike lanes downtown after a pilot program showed a 12% increase in cyclist commuters and reduced traffic congestion.",
  "key_entities": ["City Council", "Downtown District", "Bike Lane Pilot Program"]
}
```

**Reflection (sample):**
All three formats were followed correctly on the first attempt — the bullet points respected the "exactly 3" constraint, and the JSON was syntactically valid with all requested fields populated. The one thing to watch: on a retry, the JSON output occasionally wrapped the object in a markdown code fence or added a trailing explanation sentence, which would break automated parsing — so if this output feeds into code, always explicitly add "return only valid JSON, no extra text" and validate with a parser rather than assuming it's clean.

---

## Part F — Prompt Failure Analysis (Sample)

**F1 — Deliberately weak prompt:**
```
What's the best programming language?
```
**Output:**
```
[The model gives a wishy-washy answer trying to cover many languages equally,
without a clear recommendation, because "best" was never defined against any
criteria.]
```

**Diagnosis:** This is an **ambiguous instruction** failure — "best" has no defined criteria (best for what? performance, learning curve, job market, a specific project type?). The model can't fail gracefully here because there genuinely isn't a single correct answer to an underspecified question.

**F2 — Rewritten prompt:**
```
I'm a first-year computer science student who has only used Python in intro
courses. I want to build a simple web app as my next project. Recommend one
programming language to learn next, and justify your answer based on (1) ease
of transition from Python, (2) relevance to web development, (3) job market
demand for beginners.
```
**Output:**
```
JavaScript — because (1) its syntax is approachable coming from Python, (2) it's
the core language of web development (both frontend and, via Node.js, backend),
and (3) entry-level JavaScript/web roles are widely available...
```

**Reflection (sample):**
The failure category here was **ambiguity**, not a knowledge limitation or hallucination — the model had all the knowledge it needed, it just had no criteria to apply it against. The fix wasn't asking a "better" question in a vague sense — it was **adding concrete constraints and named evaluation criteria** (ease of transition, relevance, job demand), which gave the model something specific to reason against and justify. **Takeaway:** when an LLM gives a wishy-washy or overly-hedged answer, the first thing to check is whether *you* left the success criteria undefined, before assuming the model is at fault.

---

## Part G — LLM Experimentation: Parameters (Sample)

**G1 — Temperature test.** Prompt used at three settings:
```
Write a two-line opening sentence for a mystery novel.
```

| Temperature | Run 1 | Run 2 | Observation |
|---|---|---|---|
| 0.0 | "The rain had not stopped in three days when Detective Cole found the letter." | *(identical or near-identical to Run 1)* | Highly consistent, safe, predictable phrasing |
| 0.7 | "The lighthouse keeper vanished the same night the tide brought in a locked box." | "Nobody in Millbrook spoke of the house on the hill — until the night it burned." | Noticeably different each run, still coherent and usable |
| 1.2 | "Static hissed from the radio, and grandmother's clock stopped ticking, or the ticking stopped listening." | "The town's silence wore a coat of frost and secrets nobody dared to shovel." | More surprising/unusual phrasing, occasionally borders on incoherent |

**Reflection (sample):** At temperature 0, outputs were nearly identical across runs — the model consistently picked its highest-probability phrasing. At 0.7, outputs varied meaningfully while staying grammatically sound and usable — this is a good default for creative-but-controlled tasks. At 1.2, phrasing became noticeably more unusual and occasionally strained grammatically (e.g., "the ticking stopped listening" is evocative but slightly nonsensical). **Takeaway:** use temperature 0 for tasks needing reproducibility (classification, data extraction); use ~0.7 for creative writing that still needs to make sense; reserve high temperature for brainstorming where you'll filter results yourself.

**G3 — System prompt test (sample):**
System instruction: `"Always answer in exactly one sentence."`

| Question | Output | Instruction followed? |
|---|---|---|
| "What is a transformer model?" | "A transformer is a neural network architecture that uses self-attention to process all parts of an input sequence in parallel." | Yes |
| "Why do we need tokenization?" | "Tokenization breaks text into smaller units so language models can convert it into numbers they can process." | Yes |
| "What is the difference between pretraining and fine-tuning?" | "Pretraining teaches a model general language patterns from broad data, while fine-tuning specializes it on a smaller, task-specific dataset — two distinct stages." | Borderline (one long sentence with an embedded clause) |

**Reflection (sample):** The system instruction was followed reliably for simpler questions, but for the more complex comparison question, the model stretched the "one sentence" rule using a semicolon/em-dash to pack in more content rather than truly violating the format. **Takeaway:** system instructions are strong but not absolute constraints — for hard format guarantees (e.g., feeding into code), pair the instruction with a parser/validator rather than trusting the model to self-enforce perfectly on every input.

---

## Part H — Embeddings & Semantic Search (Sample)

**Sentences used:**
```
S1: "I love hiking in the mountains."
S2: "The stock market fell sharply today."
S3: "My dog loves to play fetch in the park."
S4: "Interest rates rose this quarter."
S5: "We went camping last weekend near the lake."
```

**Cosine similarity results (sample, from the notebook):**
```
Highest similarity: S1 & S5 (0.61) — both about outdoor nature activities
Second highest: S2 & S4 (0.58) — both about financial/economic topics
Lowest similarity: S1 & S2 (0.09) — hiking vs. stock market, unrelated topics
```

**Query test:** `"financial markets"` (no exact keyword overlap with any sentence)
```
Top result: S2 "The stock market fell sharply today." (similarity 0.54)
```

**Reflection (sample):** This confirms the intuition — S1 (hiking) and S5 (camping) clustered together as outdoor/nature sentences, and S2 (stock market) and S4 (interest rates) clustered together as finance sentences, even though none of these sentence pairs share exact keywords. The query test is the clearest demonstration: searching "financial markets" correctly retrieved the stock market sentence even though the word "financial" never appears in S2 — a plain keyword search (`if "financial" in sentence`) would have returned **zero results** here, because it can only match literal substrings, not meaning. **Takeaway:** this is exactly why semantic search (via embeddings) outperforms keyword search for real-world queries, where users rarely phrase things using the exact words present in the source documents — this is the foundation Week 2's RAG systems are built on.

---

## What Makes These "Good" Answers — Checklist for Your Own Submission

- [ ] Exact prompt text is shown (not paraphrased from memory)
- [ ] Output is shown in full or as a representative excerpt
- [ ] Reflection goes beyond "it worked" / "it didn't work" — explain **why**, using specific details from the output
- [ ] Where relevant, a concrete **takeaway** or rule of thumb is stated, not just an observation
- [ ] Comparisons (e.g., A1 vs A2) explicitly point out 2–3 concrete differences, not just a general impression
