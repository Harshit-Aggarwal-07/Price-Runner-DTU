# LLM-3 Handoff Prompt — Developer Experience & Evaluator Impression Architect

> **Copy-paste this entire document into your third LLM session.**

---

## Your Role

You are a **Senior Product Engineer & DX Architect** performing an independent architecture analysis for a grocery price comparison web app. You must:

1. Run your own **multi-agent internal debate** with at least 3 contrasting agents
2. Produce independent architecture recommendations
3. Focus on **developer experience, code clarity, evaluator impression, and the design note quality**
4. Think about what makes this submission **stand out** in a pool of campus applicants

**IMPORTANT:** Do NOT assume anything. Reason from first principles. Two other LLMs are doing the same analysis with different lenses (one focused on reliability/scalability, one on full architecture) — your outputs will be merged later.

---

## The Assignment (Verbatim from PDF)

### Problem
Every hostel resident at DTU has had this exact argument at 11 PM: "Is this cheaper on Blinkit or Instamart?" Right now, answering that means opening two apps, searching twice, and squinting at prices while your snacks (hopefully) stay in stock.

**Build a tiny web app that settles the argument in one search.**

A user types an item — say, "Maggi" or "Amul butter" — and the app shows matching listings and prices from both **Blinkit** and **Instamart**, for delivery to **DTU**. That's it. No logins, no mobile app, no reverse-engineering anything — everything you need is sitting right there on the desktop websites.

> "We're not grading you on how polished the UI looks. We're grading you on how you think: how you scope a real, messy problem, the calls you make when the data doesn't line up cleanly, and how clearly you can explain those calls to someone else."

### What to Build
- Search for a grocery/food item
- See matching listings and prices from both Blinkit and Instamart
- Get results relevant to delivery at DTU
- Any language, framework, or AI coding tool is fair game

### What to Submit
1. **Code (zipped)** — with README for fresh machine setup
2. **One-page design note** covering:
   - Overall architecture + why chosen over alternatives
   - How the app decides a Blinkit listing is "the same product" as an Instamart listing — and where that logic breaks down
   - What would change for many locations or many more users
3. **1-minute screen recording** of the app working E2E

### Ground Rules
- Keep request volume to sites reasonable
- Don't deploy/share outside assignment
- No login flows, no native mobile, no reverse-engineering required

---

## Context from Requirements Interview

- **Deployment:** Local only (localhost). Evaluators see video + code zip.
- **Environment:** Python 3.12.5, Node.js 22.14.0, npm 10.9.2, Playwright installed
- **Ambition:** Phased — core first (best possible), then extras, then above-and-beyond. Always production-grade, modular, HLD/LLD principles.
- **DTU Location:** Lat 28.7501, Lng 77.1177 (Shahbad Daulatpur, Delhi 110042)
- **Customer-first thinking** is a priority
- **This is for a CarDekho Group OA (Online Assessment)**
- **User's tech level:** Has touched both Python and JS but isn't deeply expert in either

---

## Your Specific Tasks

### Task 1: Multi-Agent Internal Debate
Create at least 3 internal agents with contrasting perspectives:
- **Evaluator Simulator** — thinks like a CarDekho hiring manager reading 50 submissions. What makes one stand out? What's a red flag?
- **DX Advocate** — focuses on code readability, README quality, setup simplicity, maintainability
- **Product Thinker** — focuses on user experience, what a DTU student actually wants at 11 PM

Run the debate on:
1. **Tech Stack** — What's most impressive yet maintainable for a campus applicant? What signals "I know what I'm doing"?
2. **Data Extraction** — Which approach tells the best story in the design note?
3. **Product Matching** — How to explain the matching logic in a way that shows genuine problem-solving (not just "I used fuzzy matching")?
4. **Code Organization** — What folder structure, naming, and patterns make an evaluator think "this person writes production code"?
5. **Design Note Strategy** — How to structure the one-page note for maximum impact?
6. **The "Extras" Question** — What small extras would impress vs. what would look like padding?

### Task 2: Architecture Recommendation
Produce a clear architecture recommendation with:
- System diagram (text-based, mermaid, or ASCII)
- Component breakdown with clear separation of concerns
- Emphasis on code organization and readability
- Key trade-offs framed as an evaluator would want to see them

### Task 3: Design Note Blueprint
Create a blueprint for the one-page design note:
- Recommended structure (sections, flow)
- Key phrases and framings that signal maturity
- What to emphasize vs. what to keep brief
- How to handle the "where does matching break down" question with honesty that impresses rather than undermines

### Task 4: Differentiation Analysis
For a campus OA:
- What do 80% of submissions probably look like?
- What would put this in the top 5%?
- What's the difference between a "good" and an "exceptional" submission?
- What are the anti-patterns (things that look impressive but evaluators see through)?

### Task 5: "Extras" Prioritization
Rank potential extras by impression-per-effort ratio:
- Price history tracking
- Savings calculator
- Smart product matching with confidence scores
- Unit price normalization (₹/g, ₹/ml)
- Search suggestions/autocomplete
- Category browsing
- Dark mode / polished UI
- Animated comparison view
- Export comparison results
- Others you think of

---

## Output Format

Structure your response as a single markdown document with these sections:
1. **Agent Profiles** (who debated)
2. **Debate Transcript** (key arguments, rebuttals, agreements)
3. **Architecture Recommendation** (final, with diagram)
4. **Design Note Blueprint** (structure + key framings)
5. **Differentiation Analysis** (what makes top 5%)
6. **Extras Prioritization** (ranked table with effort/impression scores)
7. **Anti-Patterns to Avoid**
8. **Dissenting Opinions** (where agents disagreed)

---

## Critical Reminder
- You're optimizing for **evaluator impression** — what makes a CarDekho hiring manager say "let's interview this person"
- The evaluator is reading the **design note most closely** — code is secondary
- **Honesty > Perfection** — admitting where your matching breaks down is a FEATURE, not a bug
- Think about what a **customer** (DTU student at 11 PM) actually needs
- The assignment explicitly says they're "not grading on how polished the UI looks" — so don't over-invest in UI, but don't make it ugly either
- Consider that the user isn't deeply expert in either Python or JS — the architecture should be **explainable** by them
