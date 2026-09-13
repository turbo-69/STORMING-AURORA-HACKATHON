# Testing Findings & Strategy Recommendations
**From:** Person 4 (Testing & Strategy Research)
**Originally tested against:** `Dev/Person1/Bhuvan` @ `768b806` (walls, self-collision, opponent-body-collision, health-tiered food seeking)
**Updated / re-verified against:** `Dev/Person1/Bhuvan` @ `76b27b0` (adds real flood-fill space scoring + a much smarter emergency-escape fallback that biases toward the tail cell)
**Method:** Local Battlesnake CLI matches — mix of team bot vs. 3 reference opponents (unmodified official starter template) and full self-play (4 copies of current TeamBot logic).

---

## Update after `76b27b0` (flood-fill + smart escape): 2 of 3 bugs now look fixed, 1 is worse than ever

Bhuvan shipped real flood-fill trap avoidance and rewrote the zero-safe-moves fallback to score escape routes by open space and explicitly favor the vacating tail cell. Re-ran matches against this version:

- **Bug #2 (self-trap loop death): looks fixed.** No more instant turn-2/3-style self-collisions in 10+ re-run matches, and the new escape-scoring logic specifically resolves the exact `match_logs/standard_4.json` scenario (the corner-loop trap) by correctly recognizing the tail cell as the escape route.
- **Bug #1 (tail-as-obstacle): practically mitigated, not root-fixed.** The strict safety filter still marks the tail cell unsafe in `is_move_safe`, but the new emergency-escape path specifically re-considers and rewards it (`+50` score) when trapped. Good enough for now — the failure mode it used to cause no longer reproduces.
- **Bug #3 (head-to-head): still completely unfixed, and now the dominant cause of death.** Code review of the diff confirms no opponent-next-head-position logic was added. Live re-test (seed 55, self-play) makes this concrete: **3 separate head-to-head deaths in a single 41-turn match** — TeamBot died to one at turn 8, a second snake died in that same collision, and a third snake died to a separate head-to-head at turn 40. This is now clearly the single most important thing left to fix.

**Bottom line: Bug #3 (head-to-head prediction) should move to the top of the priority list, unchanged from before — but now with stronger evidence, since it's surviving as the primary killer even after the other two fixes landed.**

---

## Update after `a245c7f` (head-to-head avoidance added): big improvement, but not a full fix — and a new bug surfaced

Bhuvan implemented head-to-head avoidance almost exactly per the PRD spec (exclude an opponent's possible next-head tiles when they're equal-or-longer than us). Re-tested with a 12-match statistical batch plus an 8-match batch capturing explicit elimination causes.

**The good news:** matches now regularly run 100-280+ turns instead of dying in the first 10-70. This is a real, large improvement — the bot clearly survives normal play far better than any previous version.

**The bad news:** head-to-head deaths did NOT go to zero. Final tally from the death-cause batch (8 matches, 15 confirmed deaths):

| Cause | Count | Share |
|---|---|---|
| head-collision | 9 | 60% |
| snake-collision (opponent body) | 4 | 27% |
| snake-self-collision (own body) | 2 | 13% |

The `snake-self-collision` cases confirm Bug #4 below hits **both** opponent-body and own-body collisions — the escape fallback that causes them only checks board bounds and the immediate neck cell, nothing else.

**Why head-to-head still happens:** the fix has an explicit escape hatch in the code — *"if all moves are threatened, fall back to candidate_moves and hope opponent turns away"* — for when literally every legal move sits in some opponent's strike zone. That's a real gamble, not a guarantee, and it's exactly the situation the bot is most likely to be in when things are already going wrong (cramped board, multiple opponents nearby).

### Bug #4 (New, High severity): Emergency-escape fallback doesn't check for guaranteed-fatal cells — likely cause of the new `snake-collision` deaths

Found by reading the trapped-snake fallback code (used when `safe_moves` is empty):

```python
in_bounds_moves = []
for direction, coord in future_head_positions.items():
    if 0 <= coord["x"] < board_width and 0 <= coord["y"] < board_height:
        if coord != my_neck:
            in_bounds_moves.append(direction)
```

This only filters out board edges and the immediate neck cell. It does **not** check `all_obstacles` (every opponent's body, or our own body beyond the neck). So when genuinely cornered, this path can select a direction that walks directly into a guaranteed-fatal body collision — scored no differently from a merely risky option, since the tail-seeking bonus only rewards landing on the tail, it doesn't penalize landing on a body segment.

**Fix (illustrative):** filter `in_bounds_moves` against `all_obstacles` the same way `is_move_safe` already does, before scoring by space/tail-bonus. Only fall back further (to the current bounds+neck-only logic) if that leaves zero options at all.

**The pattern across every round of testing, restated:** the bot's normal decision path (safety → flood-fill → head-to-head → food) has gotten genuinely solid — that's real, measurable progress. But every fix so far has strengthened the *normal* path while leaving the *emergency fallback* (triggered when normal logic runs out of good options) comparatively unguarded. That fallback is where essentially all remaining deaths are concentrated, just for a different specific reason each generation (first tail conservatism, now a missing obstacle check).

**Updated priority recommendation:**
1. Fix Bug #4 (add `all_obstacles` filtering to the escape fallback) — cheap, should eliminate the `snake-collision` deaths specifically.
2. Then revisit the head-to-head "hope they turn away" branch — right now it's pure chance; even a simple tiebreak (prefer the option that's fatal against fewer opponents, or that leaves more space after a hypothetical collision) would beat hoping.
3. ~~Royale/storm logic (PRD Level 4) is still completely untested~~ — **now implemented, see below.**

---

## Update after `95db196` (Royale hazard avoidance + center navigation): implemented, but health-depletion deaths are real, not just a stress-test artifact

Bhuvan implemented full hazard-state logic (in-storm / near-storm / safely-outside), BFS-based walkable food pathing, and starvation edge cases (eating food inside a hazard tile when critically low). Solid, well-structured implementation on read-through. Note: this diff does **not** touch the emergency-escape fallback, so Bug #4 above is still separately unaddressed.

### Bug #5 (New, High severity): Snakes still die directly to storm damage / starvation, even under default hazard settings

First test used an aggressive forced-storm setting (`--shrinkEveryNTurns 8`, vs. the CLI default of 25) to stress-test quickly — and TeamBot died with `Eliminated: hazard, Turn: 44` (health hit 0 from storm damage), plus a separate `out-of-health` death at turn 72. To rule out "this only happens because I forced an unrealistically fast storm," re-ran 3 more matches at **default** shrink rate:

| Match | Hazard/starvation deaths |
|---|---|
| Run 1 | none (only head-collision, snake-collision) |
| Run 2 | Self1 `hazard` @ turn 92, Self2 `hazard` @ turn 75 |
| Run 3 | Self3 `out-of-health` @ turn 120, TeamBot `out-of-health` @ turn 102 |

**4 of 9 total deaths across these 3 default-settings matches (44%) were caused by health depletion.** This confirms it's a real bug, not an artifact of my aggressive test settings. The escape-to-safety logic exists and runs, but isn't reliably getting snakes out before health runs out — likely because escape decisions are evaluated one turn at a time without accounting for how many turns of hazard damage still lie between the current position and actual safety, so a snake can be "correctly" moving toward safety every single turn and still not make it in time.

**Also worth flagging:** the team's own PRD lists the exact hazard damage-per-turn and shrink rate as *open questions* ("Action: Person 3 to verify with organizers"). Until that's confirmed, we're tuning/testing against a guess. If the real event uses faster shrink or higher damage than our assumptions, this bug gets worse, not better.

**Priority recommendation, updated:**
1. Bug #4 (escape fallback obstacle check) — still the cheapest, highest-confidence fix.
2. Bug #5 (hazard/starvation deaths) — needs the escape logic to reason about *time-to-safety* (turns of hazard damage remaining vs. turns needed to reach a safe cell), not just direction. This is a bigger fix than Bug #4.
3. Head-to-head "hope" fallback — still worth a tiebreak improvement, lower urgency than #4/#5 given current death-share.
4. Confirm actual tournament hazard settings with organizers (already flagged as an open PRD question) — testing is currently a best guess.

---

## Important caveat before the numbers

The 3 reference opponents used here are **weaker than our own bot** — they don't even avoid walls or their own bodies. A win rate against them is not evidence of tournament readiness; real opponents (including other hackathon teams using Claude/ChatGPT) will be more competent. Treat every loss below as a real bug — it lost to a bot with no strategy at all — but treat every *win* as a weak signal only. We need tougher test opponents before trusting our win rate (see "Next steps").

**Score so far:** Standard 6-3 (before writing this up), Royale 4-0 (but see caveat on Royale below — not a meaningful test yet).

---

## Bug #1 (High severity): Tail treated as a permanent obstacle causes false "no safe moves"

**Where:** `main.py`, the self-collision check (`if future_coord in my_body`) — `my_body` includes the tail segment, which is always excluded from `is_move_safe` even though it will vacate next turn (unless the snake just ate).

**Why it matters:** This is the root cause behind two of the three confirmed losses below. It doesn't just remove one option — it can remove the *only* correct option, forcing the emergency `"down"` fallback, which is not actually safe.

**Fix (illustrative, not applied — Bhuvan's file):**
```python
my_body = game_state["you"]["body"]
just_ate = game_state["you"]["health"] == 100  # or track via /start + turn deltas
tail = my_body[-1]
obstacle_body = my_body[:-1] if not just_ate else my_body
# use obstacle_body instead of my_body in the collision check
```
Simplest safe heuristic: exclude the tail cell from the obstacle set *unless* `health == 100` (just ate) — good enough for hackathon time, not perfectly accurate on double-stacked tails but that's a rare edge case not worth chasing today.

---

## Bug #2 (High severity): Self-trap death — snake curls into a closed loop, then the "safe" fallback kills it

**Evidence:** `match_logs/standard_4.json`, seed 4, turn 16→17.

TeamBot's body: `head(0,10), (0,9), (1,9), (1,10)` — a closed 2×2 loop in the top-left corner.

| Move | Result |
|---|---|
| up | wall (y=11 out of bounds) |
| left | wall (x=-1 out of bounds) |
| down | own neck (0,9) — real collision |
| right | own **tail** (1,10) — would actually vacate this turn, but Bug #1 marks it unsafe anyway |

Result: zero computed safe moves → fallback `return {"move": "down"}` → walks into its own neck → dead.

**Root cause:** No space/trap-awareness (PRD Level 3 — flood-fill) when the food-seeking logic chose a path. Bug #1 turned what should have been one real escape route into a false dead end.

**Fix:** Two independent things needed, both already on the roadmap:
1. Fix Bug #1 (tail exclusion) — would have let this specific match survive.
2. Add flood-fill space scoring so food-seeking never chases a path that curls the snake into a pocket smaller than its own length in the first place — this is a general fix, not just a patch for this one seed.

---

## Bug #3 (High severity): Head-to-head collisions — happened twice independently

**Evidence:**
- `match_logs/standard_5.json`, seed 5, turn 16→17: TeamBot's only computed-safe move (again, because of Bug #1) was directly adjacent to Opp1's head. Both died simultaneously.
- Live rerun, seed 99, turn 8: engine explicitly logs `TeamBot: Eliminated: head-collision, Turn: 8` and `Opp3: Eliminated: head-collision, Turn: 8` — both snakes walked into the same cell.

**Root cause:** PRD Level 2.2 (head-to-head prediction) is not implemented. The current opponent-avoidance only treats an opponent's *current* body as an obstacle — it never looks at where an opponent's head could move next turn.

**Fix (illustrative):**
```python
danger_cells = set()
for opp in game_state["board"]["snakes"]:
    if opp["id"] == game_state["you"]["id"]:
        continue
    opp_head = opp["body"][0]
    opp_len = opp["length"]
    if opp_len >= game_state["you"]["length"]:
        # their possible next-move tiles are dangerous to us
        for dx, dy in [(0,1),(0,-1),(-1,0),(1,0)]:
            danger_cells.add((opp_head["x"]+dx, opp_head["y"]+dy))
# then exclude danger_cells from is_move_safe, same as wall/body checks
```
This is Bug #3's real fix, but note: two of the three matches above wouldn't have needed it if Bug #1 (tail) were fixed first, since the snake would have had a second, non-adjacent option available. **Fix Bug #1 first — it's a 4-line change and reduces the blast radius of both Bug #2 and Bug #3 immediately.**

---

## 3-snake matches: also not a meaningful test (flag, not a bug)

Ran 5 additional 3-snake Standard matches (seeds 7, 12, 15, 21, 33): TeamBot won all 5. But every single match ended with both reference opponents wall-crashing on their own, usually within the first 5 turns — TeamBot never had to demonstrate real decision-making. With fewer snakes on the board there's simply less collision pressure, so this environment under-tests exactly the failure modes (head-to-head, self-trapping) that the 4-snake matches above actually caught. **5-0 here is not meaningfully better news than the 4-snake results — it's a weaker test, not a stronger one.**

## Royale mode: not actually tested yet (flag, not a bug)

4/4 wins, but 3 of 4 matches ended in under 15 turns — the storm barely closed in before the game was already decided by opponent self-destruction. This tells us almost nothing about how TeamBot behaves once hazards actually appear and shrink the board. Level 4 (storm/hazard awareness) is also simply not implemented yet. **Do not read the 4-0 record as "Royale is fine."**

---

## Strategy recommendations, in priority order

This maps directly onto the PRD's own priority list (survival > opponent-safety > trap-avoidance > storm > food), re-ordered slightly based on what the evidence above actually shows is costing us games right now:

1. **Fix Bug #1 (tail-as-obstacle) first.** Smallest change, highest immediate impact — directly implicated in both confirmed self-inflicted-adjacent losses. Do this before anything else below.
2. **Implement head-to-head prediction (Bug #3 fix).** Directly caused 2 of 3 confirmed deaths, reproduced independently twice. This is the single highest-value feature left on the PRD list given the evidence.
3. **Implement flood-fill space scoring (PRD Level 3).** Fixes the self-trap class of death (Bug #2) generally, not just the one seed we caught — and it's a prerequisite for making food-seeking safe as the snake gets longer (a long snake chasing food into a short corridor is the same failure mode, just harder to trigger by chance).
4. **Then, and only then, build + specifically stress-test Royale/storm logic (PRD Level 4).** We currently have zero real signal on how the bot behaves under actual storm pressure. Needs deliberate test matches with `--shrinkEveryNTurns` set low so the storm closes in fast, not the default long games that end before hazards matter.

**Why this order and not the PRD's original 1-2-3-4-5 straight through:** the PRD already put opponent-safety above trap-avoidance above storm, which this data confirms is right — I'm just inserting the near-free tail fix at the very front since it's cheap and cuts the severity of two other bugs at once.

---

## Self-play run (4 copies of current TeamBot logic vs. itself)

Ran 8 more matches with all 4 snakes running the exact same code (`768b806`) instead of the weak pristine opponents. Result: 2 draws (all snakes died the same turn), 6 decisive wins split across different copies — as expected, since they're identical bots, "who wins" is just noise. The value here isn't the score, it's watching identical bots produce the same failure classes already found above:
- **A 4th independent head-to-head death** (a self-play copy at turn 19 in a live replay) — same bug as #3, now seen against both weak and equal-skill opponents.
- **Two more wall-collision deaths in the same live replay** (turns 93 and 103), which contradicts the existing explicit wall-boundary check in `main.py` — almost certainly the same root cause as Bug #2 (zero-safe-moves fallback returning an unsafe `"down"`), not a new bug.

**Known limitation of self-play (noted in the PRD/strategy already):** identical bots share identical blind spots, so this doesn't tell us anything a smarter *different* opponent might expose. It's still useful for confirming a bug reproduces against more than one specific weak opponent, which is what we used it for here.

## ⚠️ Correction: match seeds are not actually reproducible

I originally wrote below that we could re-run seeds 4/5/99 later to verify fixes. That's wrong — confirmed by re-running CLI seed 7 twice and getting completely different outcomes (a 25-turn draw the first time, a 104-turn TeamBot win the second). The CLI's `-r` seed only controls the game engine's food-spawn randomness — it does **not** seed each bot's own `random.choice()` calls, which run independently and unseeded inside each Flask process. So identical CLI seed ≠ identical match when the bot itself makes random choices (e.g. the "well-fed, pick randomly among safe moves" branch in the food-seeking logic).

**Implication:** we can't use seed replay to verify a specific bug is fixed. Once fixes land, verification needs to be statistical (run N matches, check the failure class stops appearing) rather than "replay this one seed and check."

## Next steps (Person 4 / testing)

- Build 1-2 *stronger, distinct* reference opponents (e.g. a simple food-chaser, a simple space-maximizer) — self-play confirmed bugs but doesn't substitute for testing against different strategies.
- Once head-to-head + flood-fill land, run a fresh batch of matches (not seed replays — see correction above) and confirm the failure classes found here (head-to-head deaths, fallback-into-wall deaths) drop to zero across the batch.
- Design a forced-storm Royale test (low `--shrinkEveryNTurns`) once Level 4 work starts.
