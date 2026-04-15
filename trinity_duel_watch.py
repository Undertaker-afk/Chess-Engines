#!/usr/bin/env python3
"""
Interactive Trinity duel watcher.

- Finds all Trinity-*.py engines in the current directory.
- Lets you select two engines by number.
- Runs games continuously and prints a live board after each move.
- Alternates colors each game for fairness.
"""

import os
import sys
import time
import queue
import subprocess
import threading
import chess
import urllib.request
import json


MOVE_TIMEOUT_SEC = 30.0
FRAME_DELAY_SEC = 0.08
API_EVAL_DEPTH = 12
API_THINKING_TIME = 50


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def natural_key(name):
    chunk = []
    buf = ""
    is_digit = False
    for ch in name:
        if ch.isdigit():
            if not is_digit and buf:
                chunk.append(buf)
                buf = ""
            is_digit = True
            buf += ch
        else:
            if is_digit and buf:
                chunk.append(int(buf))
                buf = ""
            is_digit = False
            buf += ch
    if buf:
        chunk.append(int(buf) if is_digit else buf)
    return chunk


class EngineRunner:
    def __init__(self, script_file):
        self.script_file = script_file
        self.name = script_file[:-3]
        self.proc = None

    def start(self):
        if self.proc is None:
            self.proc = subprocess.Popen(
                [sys.executable, self.script_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

    def get_move(self, fen, timeout_sec=MOVE_TIMEOUT_SEC):
        if self.proc is None:
            return "0000"

        try:
            self.proc.stdin.write(fen + "\n")
            self.proc.stdin.flush()
        except Exception:
            return "0000"

        q = queue.Queue(maxsize=1)

        def read_line():
            try:
                q.put(self.proc.stdout.readline(), timeout=0.01)
            except Exception:
                pass

        t = threading.Thread(target=read_line, daemon=True)
        t.start()
        t.join(timeout_sec)

        if t.is_alive():
            return "0000"

        try:
            line = q.get_nowait()
        except queue.Empty:
            return "0000"

        move = line.strip()
        return move if move else "0000"

    def stop(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            self.proc = None


def print_picker(engines):
    print("Available Trinity engines:\n")
    for idx, file_name in enumerate(engines, start=1):
        print(f"{idx:2}. {file_name}")
    print()


def choose_engine(engines, prompt, forbidden=None):
    forbidden = forbidden or set()
    while True:
        raw = input(prompt).strip()
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        idx = int(raw)
        if idx < 1 or idx > len(engines):
            print("Choice out of range.")
            continue
        if idx in forbidden:
            print("Pick a different engine.")
            continue
        return idx


def append_action(action_log, message):
    ts = time.strftime("%H:%M:%S")
    action_log.append(f"[{ts}] {message}")


def fetch_api_eval(fen):
    """Fetch evaluation from chess-api.com asynchronously."""
    try:
        payload = json.dumps({
            "fen": fen,
            "depth": API_EVAL_DEPTH,
            "maxThinkingTime": API_THINKING_TIME,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://chess-api.com/v1",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def format_eval_info(info):
    """Format API response into a human-readable evaluation line."""
    if not info:
        return "Eval: waiting..."
    eval_val = info.get("eval", 0)
    win_chance = info.get("winChance", 50)
    mate = info.get("mate")
    san = info.get("san", "")
    depth = info.get("depth", "?")

    if mate is not None:
        mate_sign = "+" if mate > 0 else ""
        return f"Mate in {abs(mate)} | {san} | Depth {depth}"

    cp = eval_val
    sign = "+" if cp > 0 else ""
    bar_len = 30
    white_pct = max(0, min(100, win_chance))
    black_pct = 100 - white_pct
    white_bars = int(bar_len * white_pct / 100)
    black_bars = bar_len - white_bars
    bar = "\u2588" * white_bars + "\u2591" * black_bars
    return f"Eval: {sign}{cp:.2f} | Win: {white_pct:.1f}%W / {black_pct:.1f}%B | [{bar}] | {san} | Depth {depth}"


def render_live(board, game_no, white_name, black_name, result_text, score, action_log, eval_info=None):
    clear_screen()
    print("LIVE TRINITY DUEL")
    print("=" * 80)
    print(f"Game: {game_no}")
    print(f"White: {white_name}")
    print(f"Black: {black_name}")
    print(f"Session score  {score[white_name]} - {score[black_name]}")
    print(f"Status: {result_text}")
    print(f"Turn: {'White' if board.turn else 'Black'} to move")
    print(format_eval_info(eval_info))
    print("=" * 80)
    print(board)
    print("=" * 80)
    print("ACTION LOG")
    print("-" * 80)
    for line in action_log:
        print(line)
    print("-" * 80)
    print("Press Ctrl+C to stop.")


def play_one_game(white, black, game_no, score, action_log):
    board = chess.Board()
    status = "running"
    eval_info = None
    append_action(action_log, f"Game {game_no} start: {white.name} (White) vs {black.name} (Black)")

    while not board.is_game_over():
        current = white if board.turn else black
        uci = current.get_move(board.fen())

        if uci == "0000":
            status = f"forfeit: {current.name} timeout/empty move"
            result = "0-1" if board.turn else "1-0"
            append_action(action_log, f"Game {game_no}: {status}")
            break

        try:
            board.push_uci(uci)
            status = f"move: {current.name} played {uci}"
            append_action(action_log, f"Game {game_no}: {current.name} -> {uci}")
        except Exception:
            status = f"forfeit: {current.name} invalid move {uci}"
            result = "0-1" if board.turn else "1-0"
            append_action(action_log, f"Game {game_no}: {status}")
            break

        # Launch async API eval for the new position
        fen = board.fen()
        def fetch_and_store():
            nonlocal eval_info
            eval_info = fetch_api_eval(fen)
        eval_thread = threading.Thread(target=fetch_and_store, daemon=True)
        eval_thread.start()

        render_live(board, game_no, white.name, black.name, status, score, action_log, eval_info)
        time.sleep(FRAME_DELAY_SEC)
    else:
        result = board.result()
        status = f"game over: {result}"
        append_action(action_log, f"Game {game_no} finished: {result}")

    if result == "1-0":
        score[white.name] += 1.0
    elif result == "0-1":
        score[black.name] += 1.0
    else:
        score[white.name] += 0.5
        score[black.name] += 0.5

    render_live(board, game_no, white.name, black.name, status, score, action_log, eval_info)
    return result, status


def main():
    engine_files = [f for f in os.listdir(".") if f.startswith("Trinity-") and f.endswith(".py")]
    engine_files.sort(key=natural_key)

    if len(engine_files) < 2:
        print("Need at least two Trinity-*.py engines in this folder.")
        return

    print_picker(engine_files)
    white_idx = choose_engine(engine_files, "Select engine 1 (number): ")
    black_idx = choose_engine(engine_files, "Select engine 2 (number): ", forbidden={white_idx})

    first = EngineRunner(engine_files[white_idx - 1])
    second = EngineRunner(engine_files[black_idx - 1])
    first.start()
    second.start()

    score = {first.name: 0.0, second.name: 0.0}
    action_log = []
    append_action(action_log, f"Session start: {first.name} vs {second.name}")

    print("\nStarting continuous duel. Press Ctrl+C to stop.\n")
    time.sleep(1.0)

    game_no = 1
    try:
        while True:
            if game_no % 2 == 1:
                white, black = first, second
            else:
                white, black = second, first

            play_one_game(white, black, game_no, score, action_log)
            game_no += 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped by user.")
        print(f"Final score: {first.name} {score[first.name]} - {score[second.name]} {second.name}")
    finally:
        first.stop()
        second.stop()


if __name__ == "__main__":
    main()
