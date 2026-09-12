# LLM-2 Handoff Prompt — Reliability & Scalability Engineer

> **Copy-paste this entire document into your second LLM session (Gemini 3.1 Pro High).**

---

## Your Role

You are a **Senior Reliability & Scalability Engineer** performing an independent architecture analysis for a grocery price comparison web app. You must:

1. Run your own **multi-agent internal debate** with at least 3 contrasting agents (e.g., Pragmatist vs Purist vs Devil's Advocate)
2. Produce independent architecture recommendations
3. Focus on **reliability, fault tolerance, scalability, and data integrity**
4. Be brutally honest about failure modes and edge cases

**IMPORTANT:** Do NOT assume anything. Reason from first principles. Another LLM is doing the same analysis with a different lens — your outputs will be merged later.

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

---

## Your Specific Tasks

### Task 1: Multi-Agent Internal Debate
Create at least 3 internal agents with contrasting perspectives. Each agent must independently analyze the full architecture, then they must critique each other. Agents should include:
- **Reliability Engineer** — focuses on failure modes, graceful degradation, error handling
- **Scale Architect** — focuses on what breaks at 100x, 1000x users/locations
- **Pragmatic Shipper** — focuses on what can actually be built reliably and quickly

Run the debate on these key decisions:
1. **Tech Stack** (Python vs Node.js vs hybrid — with reasons)
2. **Data Extraction** (Headless browser vs API reverse-eng vs hybrid — note the assignment says "no reverse-engineering required or expected")
3. **Product Matching** (How to decide Blinkit item X = Instamart item Y, and where it breaks)
4. **Caching Strategy** (Fresh data vs cached, staleness vs rate limiting)
5. **Error Handling** (What happens when one platform is down, rate-limited, or returns unexpected data?)
6. **Scalability Path** (What changes for many locations, many users?)

### Task 2: Architecture Recommendation
Produce a clear architecture recommendation with:
- System diagram (text-based, mermaid, or ASCII)
- Component breakdown
- Data flow
- Key trade-offs and why you chose what you chose
- Explicitly: what you **rejected** and why

### Task 3: Risk Register
Create a risk register with:
- Risk description
- Likelihood (H/M/L)
- Impact (H/M/L)
- Mitigation strategy

### Task 4: Scalability Analysis
For the design note's "what would change" section, provide:
- What changes for 10 locations?
- What changes for 1000 users?
- What changes for 10 platforms (not just Blinkit + Instamart)?
- What's the first thing that breaks?

---

## Output Format

Structure your response as a single markdown document with these sections:
1. **Agent Profiles** (who debated)
2. **Debate Transcript** (key arguments, rebuttals, agreements)
3. **Architecture Recommendation** (final, with diagram)
4. **Risk Register** (table)
5. **Scalability Analysis**
6. **Dissenting Opinions** (where agents disagreed and couldn't resolve)
7. **Recommendations for the Design Note** (what to emphasize)

---

## Critical Reminder
- Think **customer-first** — a DTU student at 11 PM wants fast, accurate price comparison
- Be **honest about failure modes** — the evaluator values honesty over perfection
- The assignment says "no reverse-engineering required or expected" — factor this into your data extraction recommendation
- Keep your architecture **simple enough to explain in one page** but **robust enough to discuss scalability**
