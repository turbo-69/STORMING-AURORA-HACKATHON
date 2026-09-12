import sys
import time
import json
import urllib.request
import urllib.error

def build_test_state(turn=1, width=11, height=11, my_head=(5, 5), opp_head=(0, 0), food=((3, 3), (7, 7)), hazards=(), turns_until_shrink=25):
    shrink_interval = 25
    return {
        "game": {
            "id": "prod-test-game",
            "ruleset": {
                "name": "royale",
                "settings": {
                    "royale": {
                        "shrinkEveryNTurns": shrink_interval
                    }
                }
            }
        },
        "turn": turn,
        "board": {
            "height": height,
            "width": width,
            "food": [{"x": f[0], "y": f[1]} for f in food],
            "hazards": [{"x": h[0], "y": h[1]} for h in hazards],
            "snakes": [
                {
                    "id": "opponent-bot",
                    "name": "Rival",
                    "health": 90,
                    "body": [{"x": opp_head[0], "y": opp_head[1]}, {"x": opp_head[0], "y": opp_head[1] + 1}, {"x": opp_head[0], "y": opp_head[1] + 2}],
                    "head": {"x": opp_head[0], "y": opp_head[1]},
                    "length": 3,
                },
                {
                    "id": "my-snake",
                    "name": "turbo-69",
                    "health": 85,
                    "body": [{"x": my_head[0], "y": my_head[1]}, {"x": my_head[0] - 1, "y": my_head[1]}, {"x": my_head[0] - 2, "y": my_head[1]}],
                    "head": {"x": my_head[0], "y": my_head[1]},
                    "length": 3,
                }
            ]
        },
        "you": {
            "id": "my-snake",
            "name": "turbo-69",
            "health": 85,
            "body": [{"x": my_head[0], "y": my_head[1]}, {"x": my_head[0] - 1, "y": my_head[1]}, {"x": my_head[0] - 2, "y": my_head[1]}],
            "head": {"x": my_head[0], "y": my_head[1]},
            "length": 3,
        }
    }

def test_live_snake(base_url: str):
    base_url = base_url.rstrip("/")
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = f"https://{base_url}"

    print(f"============================================================")
    print(f"Testing Live Production Battlesnake: {base_url}")
    print(f"============================================================")

    # 1. Warmup / Info check (GET /)
    print("\n[Step 1] Checking Snake Info (GET /)...")
    start = time.perf_counter()
    try:
        req = urllib.request.Request(f"{base_url}/", headers={"User-Agent": "BattlesnakeLatencyTest/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            info_data = json.loads(resp.read().decode("utf-8"))
            info_time = (time.perf_counter() - start) * 1000
            print(f"  --> Status: {resp.status} OK | Round-Trip: {info_time:.1f}ms")
            print(f"  --> Info: {info_data}")
    except Exception as e:
        print(f"  [ERROR] Failed to connect to {base_url}/: {e}")
        return

    # 2. Game Start (POST /start)
    print("\n[Step 2] Sending Game Start (POST /start)...")
    start = time.perf_counter()
    start_payload = json.dumps(build_test_state(turn=0)).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{base_url}/start",
            data=start_payload,
            headers={"Content-Type": "application/json", "User-Agent": "BattlesnakeLatencyTest/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            start_time = (time.perf_counter() - start) * 1000
            print(f"  --> Status: {resp.status} OK | Round-Trip: {start_time:.1f}ms")
    except Exception as e:
        print(f"  [ERROR] /start failed: {e}")

    # 3. Multiple /move requests across different game phases
    print("\n[Step 3] Measuring /move Real Round-Trip Response Times...")
    test_cases = [
        ("Turn 1 (Early Open Board)", build_test_state(turn=1, my_head=(3, 5), opp_head=(8, 5))),
        ("Turn 5 (Duel Scouting)", build_test_state(turn=5, my_head=(4, 5), opp_head=(7, 5))),
        ("Turn 15 (Royale Shrink 10-turn window)", build_test_state(turn=15, my_head=(5, 5), opp_head=(8, 8))),
        ("Turn 20 (Royale Shrink 5-turn urgency)", build_test_state(turn=20, my_head=(5, 4), opp_head=(9, 9))),
        ("Turn 24 (Royale Shrink Imminent, 1-turn)", build_test_state(turn=24, my_head=(5, 5), opp_head=(2, 2))),
        ("Turn 25 (Post-Shrink Reset)", build_test_state(turn=25, my_head=(5, 5), opp_head=(6, 6))),
    ]

    timings = []
    for label, payload_dict in test_cases:
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        t0 = time.perf_counter()
        req = urllib.request.Request(
            f"{base_url}/move",
            data=payload_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "BattlesnakeLatencyTest/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                duration_ms = (time.perf_counter() - t0) * 1000
                timings.append(duration_ms)
                move_chosen = data.get("move", "?")
                status_icon = "[OK]" if duration_ms < 350 else "[WARN - HIGH LATENCY]"
                print(f"  * {label:40s} -> Move: {move_chosen:5s} | Time: {duration_ms:6.1f}ms  {status_icon}")
        except Exception as e:
            print(f"  * {label:40s} -> [FAILED] {e}")

    if timings:
        min_t = min(timings)
        max_t = max(timings)
        avg_t = sum(timings) / len(timings)
        buffer_ms = 500 - max_t

        print(f"\n============================================================")
        print(f"PRODUCTION LATENCY SUMMARY")
        print(f"============================================================")
        print(f"  * Fast / Minimum Turn:     {min_t:.1f}ms")
        print(f"  * Peak / Maximum Turn:     {max_t:.1f}ms")
        print(f"  * Average Turn Latency:    {avg_t:.1f}ms")
        print(f"  * Safety Margin Under 500ms: {buffer_ms:.1f}ms buffer")
        if max_t < 400:
            print(f"  --> VERDICT: 100% BATTLE-READY! Safely under the 500ms Battlesnake cutoff.")
        else:
            print(f"  --> VERDICT: Peak latency is close to 400-500ms. Consider monitoring closely.")
        print(f"============================================================\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter your PythonAnywhere URL (e.g. https://<username>.pythonanywhere.com): ").strip()
    test_live_snake(url)
