# Product Requirements Document (PRD)
## Autonomous Battlesnake — Storming Aurora Hackathon

**Team Name / Account:** `turbo-69`  
**Team Composition:** 4 members (Vibe coding / Zero coding experience)  
**Target Repository:** `turbo-69/STORMING-AURORA-HACKATHON`  
**Hosting Platform:** PythonAnywhere  

---

## 1. Problem Statement & Goals

### 1.1 The Challenge
We need to build, deploy, and operate an autonomous, web-hosted Battlesnake that competes against other student and developer teams in the **Storming Aurora Hackathon**.

### 1.2 What "Winning" Looks Like for Us
As a team of beginner "vibe coders," winning means:
1. **Flawless Reliability:** Our snake never times out (answers every turn in under 500ms) and never dies to simple mistakes (never hits a wall or runs into its own body).
2. **Qualifying Success:** In Stage 1 (Standard 4-snake boards), outlasting chaotic opponents by playing defensive survival to finish 1st or 2nd consistently, racking up enough points to reach the single-elimination bracket.
3. **Bracket Competitiveness:** In Stage 2 (Royale mode), actively recognizing the closing storm hazards and centering inside the safe zone to out-survive opponents.

---

## 2. Target Behavior Requirements

Our snake's brain (`/move`) must follow clear behavioral rules, ranked from highest priority (survival) to tactical optimization:

```
Priority 1: Don't Kill Yourself (Walls & Own Body)
     ↓
Priority 2: Don't Let Others Kill You (Enemy Bodies & Head-to-Head)
     ↓
Priority 3: Don't Get Trapped (Avoid Small Pockets / Dead Ends)
     ↓
Priority 4: Survive the Storm (Stay Out of Royale Hazards)
     ↓
Priority 5: Eat to Survive and Dominate (Seek Food Intelligently)
```

### 2.1 Level 1: Foundational Survival (Must-Have)
- **Wall Avoidance:** Never choose a direction that moves off the board boundary (`0` to `width-1`, `0` to `height-1`).
- **Self-Avoidance:** Never choose a direction that collides with any part of our own snake's body.
- **Immediate Reversal Prevention:** Never attempt to move backward into the neck.

### 2.2 Level 2: Multi-Snake Collision Avoidance (Qualifying Mode)
- **Opponent Body Avoidance:** Treat all opponent body segments as solid, fatal obstacles.
- **Head-to-Head Hazard Prediction:**
  - In Battlesnake, colliding head-to-head kills the shorter snake (or both if equal length).
  - The snake must calculate where adjacent rival heads can move next.
  - If a rival snake is **equal to or longer than us**, treat their potential next-move tiles as deadly obstacles.
  - If we are **strictly longer**, we can deliberately take head-to-head confrontations to eliminate them.

### 2.3 Level 3: Space & Trap Awareness (Flood Fill)
- **Avoid Dead Ends:** Before picking a move, estimate the amount of open space in that direction. If a corridor has fewer open tiles than our snake's length, do not enter it unless forced.

### 2.4 Level 4: Royale / Storm Awareness (Bracket Stage)
- **Hazard Evasion:** The game engine provides a list of `hazards` (storm tiles). Treat hazard tiles as dangerous and avoid them if a safe board tile is available.
- **Zone Centering:** When the storm begins encroaching, calculate moves that gravitate towards the center of the board.
- **Emergency Sacrifice:** If every path is blocked except a hazard tile, take the hazard (15 damage) rather than an instant-kill wall or snake collision.

### 2.5 Level 5: Smart Food Seeking
- **Low-Health Urgency:** When health drops below `40`, food seeking becomes top priority.
- **Growth Strategy:** When health is safe (`> 70`), only eat nearby food if it maintains safe-space pathing, or to stay longer than the second-longest snake on the board.

---

## 3. Success Metrics

| Metric | Target Goal | Why It Matters |
| :--- | :--- | :--- |
| **Response Latency** | `< 250ms` (Limit is 500ms) | Moves over 500ms result in automatic game disqualification/death. |
| **Server Uptime** | `100%` during matches | If PythonAnywhere drops or sleeps, our snake dies on Turn 1. |
| **Self-Death Rate** | `0%` | We should never die from hitting walls or our own body. |
| **Qualifying Performance** | Top 2 in ≥ 75% of qualifying matches | Consistency and survival earn high placement points (10 or 6 pts). |
| **Bracket Advancement** | Reach Bracket Stage (Top 16 / Top 8) | Demonstrates full end-to-end execution of our game plan. |

---

## 4. Out-of-Scope (Explicitly NOT Building)

To prevent overwhelm and ensure team focus, the following are strictly out of scope:
1. **Constrictor Side Event:** Constrictor mode fills the board permanently with snake bodies without food. We will not build specialized logic for this optional bonus round.
2. **Machine Learning / Neural Networks:** We will use deterministic, rule-based heuristics. AI models add latency and unpredictable debugging overhead.
3. **Custom Frontends or Dashboards:** We rely entirely on the official Battlesnake visualizer and PythonAnywhere web logs.
4. **Paid Infrastructure:** Everything must run within the free tier of PythonAnywhere and GitHub.

---

## 5. Constraints

1. **Team Experience:** Zero traditional software engineering experience. All code modifications are prompt-engineered through AI assistants. Logic must remain clean, modular, and readable.
2. **Latency Deadline:** The Battlesnake engine enforces a strict **500ms HTTP timeout** per turn. All calculations (pathfinding, space counting) must execute in `< 100ms` of Python CPU time.
3. **Free-Tier Hosting (PythonAnywhere):**
   - Free accounts provide 1 web worker.
   - External outbound web requests are restricted (not an issue since Battlesnake sends inbound requests).
   - The app must remain lightweight so it does not exhaust daily CPU allowances.

---

## 6. Assumptions & Open Questions

### Assumptions
- PythonAnywhere free tier web app remains warm and responsive during tournament play.
- Battlesnake API version 1 is standard across all tournament stages.
- Royale mode provides storm tiles in the standard `game_state["board"]["hazards"]` JSON payload.

### Open Questions
- ❓ **Team Registration vs. Snake Registration:** Does the hackathon require a Google Form / Discord team registration, or is adding the snake URL in Battlesnake sufficient? *(Action: Person 3 to verify with organizers)*.
- ❓ **Hazard Damage Value:** What is the exact damage per turn inside the hazard zone for this event? (Standard is 14–15 damage/turn).
- ❓ **Board Sizes:** Will qualifying be standard `11x11`, and are all bracket matches `19x19`?
