import os
import sys
import time
import subprocess
import threading
import urllib.request

def wait_for_server(url, timeout=10.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def run_single_match(opp_handicap="0", my_handicap="0", description="", gametype="standard", extra_flags=None, num_opponents=1):
    env = os.environ.copy()
    env["TEST_HANDICAP_OPPONENT_LENGTH"] = opp_handicap
    env["TEST_HANDICAP_MY_LENGTH"] = my_handicap
    env["PYTHONUNBUFFERED"] = "1"

    print(f"\n{'='*70}")
    print(f"=== {description} ===")
    print(f"{'='*70}")

    dummy_procs = []
    # Start dummy opponents on port 8001, 8002...
    for i in range(num_opponents):
        port = 8001 + i
        p_env = os.environ.copy()
        p_env["PORT"] = str(port)
        d_proc = subprocess.Popen(
            [sys.executable, "dummy_snake.py"],
            env=p_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        dummy_procs.append(d_proc)

    # Start main snake on port 8000
    main_proc = subprocess.Popen(
        [sys.executable, "main.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    def stream_main_output():
        for line in iter(main_proc.stdout.readline, ''):
            line_str = line.strip()
            if line_str and not line_str.startswith("127.0.0.1"):
                print(f"  [SNAKE LOG] {line_str}", flush=True)

    stream_thread = threading.Thread(target=stream_main_output, daemon=True)
    stream_thread.start()

    if not wait_for_server("http://127.0.0.1:8000/"):
        print("ERROR: main.py failed to start on port 8000")
        for dp in dummy_procs: dp.kill()
        main_proc.kill()
        return

    for i in range(num_opponents):
        port = 8001 + i
        if not wait_for_server(f"http://127.0.0.1:{port}/"):
            print(f"ERROR: dummy_snake.py failed on port {port}")
            for dp in dummy_procs: dp.kill()
            main_proc.kill()
            return

    print("All servers healthy. Launching battlesnake.exe match...\n" + "-"*60)

    # Run battlesnake.exe
    cli_cmd = [
        r".\battlesnake.exe", "play",
        "-n", "turbo-69", "-u", "http://127.0.0.1:8000",
    ]
    for i in range(num_opponents):
        port = 8001 + i
        cli_cmd.extend(["-n", f"DummyBot{i+1}", "-u", f"http://127.0.0.1:{port}"])
    cli_cmd.extend(["-g", gametype, "-W", "11", "-H", "11"])
    if extra_flags:
        cli_cmd.extend(extra_flags)

    try:
        match_result = subprocess.run(cli_cmd, capture_output=True, text=True)
        time.sleep(0.5)
        print("-"*60)
        print("Match completed. CLI Output:")
        combined = (match_result.stdout + "\n" + match_result.stderr).strip().splitlines()
        for line in combined[-10:]:
            print(f"  {line}")
    finally:
        main_proc.kill()
        for dp in dummy_procs: dp.kill()

if __name__ == "__main__":
    # Scenario 1: My snake starts noticeably shorter than opponent (3 vs 7) -> Survival Mode
    run_single_match(
        opp_handicap="4",
        my_handicap="0",
        description="SCENARIO 1: MY SNAKE STARTS NOTICEABLY SHORTER (Length 3 vs 7) -> SURVIVAL MODE ACTIVE",
        gametype="standard",
        extra_flags=["--minimumFood", "4", "--foodSpawnChance", "40"],
        num_opponents=1
    )
    time.sleep(1.0)

    # Scenario 2: My snake starts noticeably longer with margin (Length 6 vs 3) -> Dominance Mode
    run_single_match(
        opp_handicap="0",
        my_handicap="3",
        description="SCENARIO 2: MY SNAKE HAS MEANINGFUL LENGTH MARGIN (Length 6 vs 3) -> DOMINANCE MODE ACTIVE",
        gametype="standard",
        extra_flags=["--minimumFood", "4", "--foodSpawnChance", "40"],
        num_opponents=1
    )
    time.sleep(1.0)

    # Scenario 3: 3 Snakes alive, my snake is mid-pack (Length 5 vs Opp1 7 and Opp2 3) -> Opportunist Mode
    run_single_match(
        opp_handicap="4",
        my_handicap="2",
        description="SCENARIO 3: 3 SNAKES ALIVE, MID-PACK (Length 5 vs Opp1 7, Opp2 3) -> OPPORTUNIST MODE ACTIVE",
        gametype="standard",
        extra_flags=["--minimumFood", "4", "--foodSpawnChance", "40"],
        num_opponents=2
    )
