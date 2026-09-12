# PROJECT STATUS — Storming Aurora Hackathon (Battlesnake)
*Last updated: this is the current snapshot as of our latest chat. I'll update this file every time something changes.*

---

## Overview
- **Event:** Storming Aurora Hackathon — building an autonomous Battlesnake
- **Team:** 4 people, all vibe coding (zero coding knowledge, prompting Claude)
- **Language:** Python (official starter: `BattlesnakeOfficial/starter-snake-python`)
- **Deployment target:** PythonAnywhere (free, stays warm — no cold-start risk)
- **Battlesnake account:** `turbo-69`
- **Team repo:** https://github.com/turbo-69/STORMING-AURORA-HACKATHON.git

## Tournament format (reference)
1. **Qualifying** — Standard mode, 4 snakes/board, reshuffled each round. Points: 1st=10, 2nd=6, 3rd=3, 4th=1.
2. **Bracket** — single-elimination Royale. Storm shrinks the board + deals damage outside the safe zone. Lose once, out.
3. **Grand final** — last 2 survivors, Royale rules, 19×19 board.
4. **Side event (optional)** — Constrictor bonus round, separate leaderboard.

## Open items / unconfirmed
- ❓ Whether there's a separate **team registration** form beyond individual snake registration — needs confirming with organizers.

---

## Team status by role

### 🧠 Person 1 (Bhuvan) — Logic Prompter
- **Active Branch:** `Dev/Person1/Bhuvan`
- **Status:** In progress (Opponent avoidance, food-seeking, and full-board flood-fill trap avoidance implemented)
- **Owns:** `/move` decision logic — Standard-mode survival first, then storm/Royale-aware logic
- **Latest:** Added full-board flood-fill to prevent entering pockets smaller than snake length, intelligent emergency escape, and strict safety priority over food. Next: Head-to-head collision safety against larger snakes.

### 🚀 Person 2 — Deploy & Infra Owner
- **Status:** In progress — connecting team repo to PythonAnywhere
- **Owns:** Getting the repo live on a public URL, redeploying as logic updates, keeping URL stable
- **Latest:** Given step-by-step deployment prompt for the repo above. Live URL not yet confirmed.

### 📋 Person 3 — Registration & Match-Day Ops
- **Status:** Account created
- **Owns:** Registering the snake once live, keeping registration synced with URL, match-day logistics
- **Latest:** Battlesnake account created (`turbo-69`). Waiting on Person 2's live URL before adding the snake under "My Battlesnakes."

### 🔍 Person 4 — Testing & Strategy Research
- **Status:** Not yet started / update needed
- **Owns:** Playing test matches, reporting bugs to Person 1, researching strategy
- **Latest:** *(nothing reported yet)*

---

## Next milestone
Person 2 gets the repo live on PythonAnywhere → hands URL to Person 3 → Person 3 registers the snake under "My Battlesnakes" → team runs first self-match test.
