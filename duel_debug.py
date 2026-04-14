#!/usr/bin/env python3
"""
Deterministic duel diagnostics for Trinity engines.

Runs a validated head-to-head session and reports exactly why each game ends:
- normal result
- timeout
- empty move
- bad UCI
- illegal move
"""

import argparse
import queue
import subprocess
import sys
import threading
import time

import chess


def read_move(proc, fen, timeout_sec):
    try:
        proc.stdin.write(fen + "\n")
        proc.stdin.flush()
    except Exception:
        return None, "write_fail"

    q = queue.Queue(maxsize=1)

    def _read_line():
        try:
            q.put(proc.stdout.readline(), timeout=0.01)
        except Exception:
            pass

    t = threading.Thread(target=_read_line, daemon=True)
    t.start()
    t.join(timeout_sec)

    if t.is_alive():
        return None, "timeout"

    try:
        return q.get_nowait().strip(), "ok"
    except queue.Empty:
        return "", "ok"


def run_game(game_no, white_name, black_name, white_proc, black_proc, max_plies, timeout_sec):
    board = chess.Board()

    for _ in range(max_plies):
        proc = white_proc if board.turn else black_proc
        mover = white_name if board.turn else black_name
        mv, status = read_move(proc, board.fen(), timeout_sec)

        if status != "ok":
            loser = "white" if board.turn else "black"
            return {
                "game": game_no,
                "white": white_name,
                "black": black_name,
                "reason": f"forfeit:{loser}:{status}",
                "plies": board.ply(),
            }

        if not mv or mv == "0000":
            loser = "white" if board.turn else "black"
            return {
                "game": game_no,
                "white": white_name,
                "black": black_name,
                "reason": f"forfeit:{loser}:empty",
                "plies": board.ply(),
            }

        try:
            move_obj = chess.Move.from_uci(mv)
        except Exception:
            loser = "white" if board.turn else "black"
            return {
                "game": game_no,
                "white": white_name,
                "black": black_name,
                "reason": f"forfeit:{loser}:bad_uci:{mv}",
                "plies": board.ply(),
            }

        if move_obj not in board.legal_moves:
            loser = "white" if board.turn else "black"
            return {
                "game": game_no,
                "white": white_name,
                "black": black_name,
                "reason": f"forfeit:{loser}:illegal:{mv}",
                "plies": board.ply(),
            }

        board.push(move_obj)

        if board.is_game_over():
            return {
                "game": game_no,
                "white": white_name,
                "black": black_name,
                "reason": f"normal:{board.result()}",
                "plies": board.ply(),
            }

    return {
        "game": game_no,
        "white": white_name,
        "black": black_name,
        "reason": "stopped:max_plies",
        "plies": board.ply(),
    }


def stop_proc(proc):
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=1)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Validated duel diagnostics for Trinity engines")
    parser.add_argument("--engine-a", default="Trinity-0.7.py", help="Engine A script path")
    parser.add_argument("--engine-b", default="Trinity-0.1.py", help="Engine B script path")
    parser.add_argument("--games", type=int, default=4, help="Number of games to run")
    parser.add_argument("--max-plies", type=int, default=100, help="Ply cap per game")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-move timeout in seconds")
    args = parser.parse_args()

    a_name = args.engine_a[:-3] if args.engine_a.endswith(".py") else args.engine_a
    b_name = args.engine_b[:-3] if args.engine_b.endswith(".py") else args.engine_b

    proc_a = subprocess.Popen(
        [sys.executable, args.engine_a],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    proc_b = subprocess.Popen(
        [sys.executable, args.engine_b],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    print(f"Running {args.games} games: {a_name} vs {b_name}")
    print(f"Settings: timeout={args.timeout}s max_plies={args.max_plies}")

    results = []
    try:
        for game_no in range(1, args.games + 1):
            if game_no % 2 == 1:
                white_name, black_name = a_name, b_name
                white_proc, black_proc = proc_a, proc_b
            else:
                white_name, black_name = b_name, a_name
                white_proc, black_proc = proc_b, proc_a

            start = time.time()
            info = run_game(
                game_no,
                white_name,
                black_name,
                white_proc,
                black_proc,
                args.max_plies,
                args.timeout,
            )
            info["seconds"] = round(time.time() - start, 3)
            results.append(info)
            print(
                f"game {info['game']}: W={info['white']} B={info['black']} "
                f"reason={info['reason']} plies={info['plies']} t={info['seconds']}s"
            )
    finally:
        stop_proc(proc_a)
        stop_proc(proc_b)

    stderr_a = ""
    stderr_b = ""
    try:
        stderr_a = proc_a.stderr.read().strip()
    except Exception:
        pass
    try:
        stderr_b = proc_b.stderr.read().strip()
    except Exception:
        pass

    print("\nSummary:")
    by_reason = {}
    for r in results:
        by_reason[r["reason"]] = by_reason.get(r["reason"], 0) + 1
    for reason, count in sorted(by_reason.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {count}x {reason}")

    if stderr_a:
        print("\nEngine A stderr (last line):")
        print(stderr_a.splitlines()[-1])
    if stderr_b:
        print("\nEngine B stderr (last line):")
        print(stderr_b.splitlines()[-1])


if __name__ == "__main__":
    main()
