# Technical Requirements Document (TRD)
## Autonomous Battlesnake Architecture & Engineering Specification
**Project:** Storming Aurora Hackathon  
**Team Account:** `turbo-69`  
**GitHub Repository:** `https://github.com/turbo-69/STORMING-AURORA-HACKATHON.git`  
**Hosting Target:** PythonAnywhere (WSGI Web App)  

---

## 1. System Architecture

Battlesnake operates as a distributed web service. The Battlesnake official game engine acts as the client/referee, and our Python application acts as an HTTP server that listens for and answers requests.

```
+------------------------------------+
|   Battlesnake Game Engine (Cloud)  |
+------------------------------------+
                 |
                 | HTTP POST /move (Every ~500ms per turn)
                 v
+-----------------------------------------------------------+
|          PythonAnywhere Cloud Hosting Infrastructure      |
|                                                           |
|  +---------------------+        +----------------------+  |
|  | Nginx / Web Router  | ---->  |   WSGI Handler       |  |
|  +---------------------+        +----------------------+  |
|                                            |              |
|                                            v              |
|                                 +----------------------+  |
|                                 | Flask App (server.py)|  |
|                                 +----------------------+  |
|                                            |              |
|                                            v              |
|                                 +----------------------+  |
|                                 | Snake Logic (main.py)|  |
|                                 | - Standard Mode      |  |
|                                 | - Royale Storm Mode  |  |
|                                 +----------------------+  |
+-----------------------------------------------------------+
```

### Component Roles in Plain English:
1. **Flask (`server.py`):** A lightweight Python web server library. Think of it as the "receptionist" that catches incoming messages from the Battlesnake referee and routes them to the right handler.
2. **Snake Logic (`main.py`):** The "brain" of the snake. It parses the game board information, calculates safe directions, runs survival heuristics, and picks the best move.
3. **PythonAnywhere (Hosting Platform):** A cloud platform where our Python app stays online 24/7. Unlike serverless hosts (such as Render or free Heroku) that "sleep" after inactivity and take 30+ seconds to wake up (causing instant timeouts), PythonAnywhere keeps our web process warm.
4. **WSGI (Web Server Gateway Interface):** The standard bridge that connects PythonAnywhere's web infrastructure to our Python Flask application.

---

## 2. API Contract (Battlesnake Engine Specification)

The Battlesnake engine sends HTTP requests formatted as JSON (structured data). Our server must respond with the exact JSON structure expected.

### 2.1 `GET /` — Snake Customization (Info)
* **When called:** When registering or inspecting the snake on [play.battlesnake.com](https://play.battlesnake.com).
* **Payload Received:** None.
* **Payload Returned:** JSON metadata defining the snake's appearance:
  ```json
  {
    "apiversion": "1",
    "author": "turbo-69",
    "color": "#FF4500",
    "head": "fang",
    "tail": "bolt"
  }
  ```

### 2.2 `POST /start` — Game Initialization
* **When called:** Once at the start of every game (Turn 0).
* **Payload Received:** Full `game_state` object containing board rules, dimensions, initial snake positions, and game ID.
* **Payload Returned:** String `"ok"` (HTTP 200).
* **Action:** Reset any temporary in-memory trackers or game timers.

### 2.3 `POST /move` — Turn-by-Turn Decision Engine
* **When called:** On every turn of the game.
* **Hard SLA:** Response must be returned in **< 500ms**.
* **Payload Received:** Detailed `game_state` JSON (summary below):
  ```json
  {
    "game": { "id": "...", "ruleset": { "name": "standard" } },
    "turn": 42,
    "board": {
      "height": 11,
      "width": 11,
      "food": [{ "x": 5, "y": 5 }],
      "hazards": [{ "x": 0, "y": 0 }],
      "snakes": [
        {
          "id": "opponent-1",
          "name": "Viper",
          "health": 90,
          "body": [{ "x": 1, "y": 2 }, { "x": 1, "y": 3 }],
          "head": { "x": 1, "y": 2 },
          "length": 2
        }
      ]
    },
    "you": {
      "id": "our-snake-id",
      "name": "turbo-69",
      "health": 85,
      "body": [{ "x": 3, "y": 3 }, { "x": 3, "y": 2 }, { "x": 3, "y": 1 }],
      "head": { "x": 3, "y": 3 },
      "length": 3
    }
  }
  ```
* **Payload Returned:**
  ```json
  { "move": "up" }
  ```
  *(Valid values: `"up"`, `"down"`, `"left"`, `"right"`)*

### 2.4 `POST /end` — Post-Game Summary
* **When called:** Immediately after game completion.
* **Payload Received:** Final `game_state`.
* **Payload Returned:** String `"ok"` (HTTP 200).

---

## 3. Core Logic Requirements

Our `/move` algorithm operates in two behavioral modes, automatically selected based on the game ruleset:
- **Standard Mode:** Qualifying rounds (4 snakes, 11x11 board, food survival).
- **Royale Mode:** Bracket and finals (Storm shrinking the board, hazard damage, up to 19x19 board).

### 3.1 Mode Detection
```python
is_royale = game_state.get("game", {}).get("ruleset", {}).get("name") == "royale"
```

---

### 3.2 Standard-Mode Survival Logic (The 5 Rules)

#### Rule 1: Immediate Reverse Elimination
- Never move into the neck segment (`you.body[1]`).

#### Rule 2: Wall / Board Boundary Avoidance
- Target coordinates `(x, y)` must satisfy:
  $$0 \le x < \text{board.width} \quad \text{and} \quad 0 \le y < \text{board.height}$$
- Any move violating this is eliminated immediately.

#### Rule 3: Self & Opponent Body Collision Prevention
- All body segments of all snakes on the board (including our own) are marked as lethal obstacles.
- **Exception (Tail chasing):** If a snake did not just eat food, its tail tile will move forward on the next turn. However, for baseline reliability, we treat all body segments as solid.

#### Rule 4: Head-to-Head Prediction (Multiplayer Safety)
- For every opponent snake:
  - Calculate all 4 tiles adjacent to the opponent's head where they could move next turn.
  - If `opponent.length >= you.length`: **Mark those adjacent tiles as unsafe.** Colliding head-to-head against an equal or larger snake results in our death.
  - If `you.length > opponent.length`: Those tiles are safe for us (we can eliminate them if they move there).

#### Rule 5: Food Seeking & Trap Avoidance
- **When health < 40:** Calculate Manhattan distance ($|x_1 - x_2| + |y_1 - y_2|$) to all food items and prioritize the closest food.
- **When health ≥ 40:** Prioritize safety, open space, and area control rather than blindly chasing food.
- **Space Evaluation (Mini Flood-Fill):** Count accessible neighbor tiles. Avoid moving into corridors or dead ends whose total area is smaller than our snake length.

---

### 3.3 Royale / Storm-Mode Logic

In Royale mode, the game engine shrinks the safe zone by generating **Hazards** (storm tiles in `game_state["board"]["hazards"]`).

#### Rule 1: Hazard Score Penalty
- Every move is scored. Moving onto a safe board tile gets a high score (`100`); moving onto a hazard tile receives a severe penalty (`-80`).
- **Emergency Exemption:** If all safe tiles lead to instant death (walls or snakes), a hazard tile is chosen instead. Hazard damage (typically 14-15 HP) is better than instant elimination.

#### Rule 2: Safe-Zone Centering
- When storm tiles appear, calculate the center coordinate of the board:
  $$x_{\text{center}} = \lfloor \text{board.width} / 2 \rfloor, \quad y_{\text{center}} = \lfloor \text{board.height} / 2 \rfloor$$
- Favor safe moves that decrease Manhattan distance to the center, keeping our snake ahead of the encroaching storm.

#### Rule 3: Health Buffer Management
- In Royale mode, increase the hunger threshold from `40` to `65`. Staying high on health provides a cushion to absorb storm ticks when maneuvering around enemies.

---

## 4. Deployment Requirements (PythonAnywhere)

To ensure high availability and zero setup confusion for Person 2 (Deploy Owner):

### 4.1 Repository Structure
```
d:\Seds hackathon/
├── main.py            # Decision logic & helper functions
├── server.py          # Flask HTTP routes & server runner
├── requirements.txt   # Dependencies (Flask==2.3.2)
├── wsgi.py            # Entrypoint for PythonAnywhere web app
├── PRD.md             # Product requirements
├── TRD.md             # Technical requirements (this document)
└── PROJECT_STATUS.md  # Live team status & roadmap
```

### 4.2 PythonAnywhere Web App Configuration
1. **Create Web App:** In PythonAnywhere Web tab, select **Manual Configuration** with **Python 3.11**.
2. **Virtualenv / Packages:** Install dependencies in a Bash console:
   ```bash
   pip3.11 install -r requirements.txt
   ```
3. **WSGI File (`/var/www/<username>_pythonanywhere_com_wsgi.py`):**
   ```python
   import sys
   import os

   path = '/home/<username>/STORMING-AURORA-HACKATHON'
   if path not in sys.path:
       sys.path.append(path)

   from server import run_server
   from main import info, start, move, end
   from flask import Flask

   # Expose the Flask application object for WSGI
   from server import app as application
   ```
   *(We will ensure `server.py` cleanly exports `app` directly for WSGI compatibility).*

4. **URL Stability:**
   The public URL is permanently fixed at: `https://<username>.pythonanywhere.com`. Person 3 registers this exact URL on the Battlesnake dashboard once.

---

## 5. Performance Constraints & Latency Budget

* **Hard Game Limit:** 500ms per move.
* **Our Target SLA:** **< 200ms round-trip**, with internal computation taking **< 50ms**.

| Operation Stage | Allocated Time | Notes |
| :--- | :--- | :--- |
| Network Ingress (Battlesnake -> PythonAnywhere) | ~40-70ms | Internet latency |
| Flask Request Parsing (JSON decode) | ~5ms | Instant in Python |
| Decision Engine Computation (`main.py`) | **< 30ms** | Pure arithmetic & list operations |
| Flask Response Encoding & Network Egress | ~40-70ms | Internet latency |
| **Total Round-Trip Time** | **~120-180ms** | Safe margin (300ms buffer before timeout) |

---

## 6. Testing Approach

1. **Automated Unit Tests (`test_snake.py`):**
   - Run locally before every git commit to verify corner avoidance, self-collision prevention, opponent avoidance, and hazard weighting.
2. **Self-Match Testing on Battlesnake:**
   - Person 4 creates a private game on [play.battlesnake.com](https://play.battlesnake.com) pitting our snake against 3 default starter snakes.
   - Verify that our snake survives until opponents kill themselves or until end-game 1v1.
3. **Royale Simulation:**
   - Create a test game with the "Royale" ruleset selected to verify that the snake does not linger in the storm edges.

---

## 7. Known Risks & Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Cold Starts** | Snake times out on Turn 1 | Using PythonAnywhere instead of free Render/Heroku prevents cold boots. |
| **Redeploy Desync** | PythonAnywhere serving stale code during a match | Person 2 must click the green **"Reload"** button on the Web tab after every `git pull`. |
| **CPU Throttling** | Heavy loops exceed 500ms under CPU quota | Keep pathfinding simple (Manhattan distance + small flood-fill depth). Avoid exhaustive A* searches. |
| **Head-to-Head Equal Tie** | Both snakes die | Treat equal-length opponent heads as dangerous obstacles rather than 50/50 gambles. |
| **Royale Storm Panic** | Snake trapped between enemy and storm | Prefer taking 15 storm damage over instant death against a snake body. |
