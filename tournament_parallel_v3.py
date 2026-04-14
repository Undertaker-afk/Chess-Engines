#!/usr/bin/env python3
"""
ULTIMATE Chess Tournament Harness
→ Only Trinity-*.py engines
→ 3 games side-by-side + live leaderboard
→ Average response time tracking
→ Saves results to tournament/gamestats.txt
→ Saves final board of every game to tournament/endgame/
"""

import os
import sys
import time
import subprocess
import threading
import queue
import random
import chess
from datetime import datetime

# ====================== CONFIG ======================
GAMES_PER_PAIR = 4
MOVE_TIMEOUT_SEC = 30.0
OPENING_MOVE_TIMEOUT_SEC = 30.0
ELO_K = 32
START_ELO = 1500
MAX_CONCURRENT_GAMES = 4
# ===================================================

engines = []
lock = threading.Lock()
active_games = []

# Response time tracking
response_times = {}  # engine_name -> list of move times

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

class Engine:
    def __init__(self, filename):
        self.name = filename[:-3]
        self.elo = START_ELO
        self.games = 0
        self.score = 0.0
        self.total_time = 0.0
        self.move_count = 0

    def avg_response_time(self):
        return self.total_time / self.move_count if self.move_count > 0 else 0.0


class EngineRunner:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.proc = None

    def start(self):
        if self.proc is None:
            self.proc = subprocess.Popen(
                [sys.executable, f"{self.engine.name}.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

    def get_move(self, fen, timeout_sec=MOVE_TIMEOUT_SEC):
        start = time.time()
        try:
            if self.proc is None:
                return "0000"

            self.proc.stdin.write(fen + "\n")
            self.proc.stdin.flush()

            q = queue.Queue(maxsize=1)

            def _read_line():
                try:
                    q.put(self.proc.stdout.readline(), timeout=0.01)
                except Exception:
                    pass

            reader = threading.Thread(target=_read_line, daemon=True)
            reader.start()
            reader.join(timeout_sec)

            if reader.is_alive():
                move = "0000"
            else:
                try:
                    move = (q.get_nowait().strip() or "0000")
                except queue.Empty:
                    move = "0000"

            elapsed = time.time() - start

            with lock:
                self.engine.total_time += elapsed
                self.engine.move_count += 1
                if self.engine.name not in response_times:
                    response_times[self.engine.name] = []
                response_times[self.engine.name].append(elapsed)

            return move
        except:
            return "0000"

    def stop(self):
        if self.proc:
            try: self.proc.terminate()
            except: pass
            self.proc = None


def update_elo(elo_a, elo_b, score_a):
    expected = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    return (elo_a + ELO_K * (score_a - expected),
            elo_b + ELO_K * ((1 - score_a) - (1 - expected)))


def print_leaderboard():
    with lock:
        sorted_e = sorted(engines, key=lambda e: e.elo, reverse=True)
    print("🏆 LIVE LEADERBOARD 🏆".center(160))
    print(f"{'Rank':<4} {'Engine':<20} {'Elo':<7} {'Games':<6} {'Score':<6} {'Avg Time':<9} W/D/L")
    print("─" * 160)
    for rank, e in enumerate(sorted_e, 1):
        w = int(e.score)
        d = int((e.score * 2) % 2)
        l = e.games - w - d
        avg_t = f"{e.avg_response_time():.3f}s"
        print(f"{rank:<4} {e.name:<20} {e.elo:7.0f} {e.games:6} {e.score:6.1f} {avg_t:>8} {w}/{d}/{l}")
    print("─" * 160)


def print_boards_side_by_side():
    with lock:
        games = list(active_games)[:MAX_CONCURRENT_GAMES]
    if not games:
        return

    cols = 2
    for row_start in range(0, len(games), cols):
        row_games = games[row_start:row_start + cols]
        headers = [f"Game {g['id']} → {g['white'].name} (W) vs {g['black'].name} (B)" for g in row_games]
        boards_str = [str(g['board']) for g in row_games]

        print("   ".join(h.center(42) for h in headers))
        board_lines = [b.split('\n') for b in boards_str]
        for i in range(8):
            line_parts = [lines[i] if i < len(lines) else " " * 42 for lines in board_lines]
            print("   ".join(line_parts))
        print()


def save_tournament_results():
    os.makedirs("tournament/endgame", exist_ok=True)

    # Save final leaderboard
    with open("tournament/gamestats.txt", "w", encoding="utf-8") as f:
        f.write(f"Tournament finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("FINAL LEADERBOARD\n")
        f.write("─" * 100 + "\n")
        sorted_e = sorted(engines, key=lambda e: e.elo, reverse=True)
        f.write(f"{'Rank':<4} {'Engine':<20} {'Elo':<7} {'Games':<6} {'Score':<6} {'Avg Time':<9} W/D/L\n")
        for rank, e in enumerate(sorted_e, 1):
            w = int(e.score)
            d = int((e.score * 2) % 2)
            l = e.games - w - d
            avg_t = f"{e.avg_response_time():.3f}s"
            f.write(f"{rank:<4} {e.name:<20} {e.elo:7.0f} {e.games:6} {e.score:6.1f} {avg_t:>8} {w}/{d}/{l}\n")

    # Save every game's final position
    # Note: We don't store every game here because we didn't keep history.
    # For simplicity we save current active + a summary.
    # If you want full PGN later we can extend it.

    print("\nResults saved to tournament/gamestats.txt and tournament/endgame/")


def build_match_schedule(engine_list):
    pairs = []
    for i, e1 in enumerate(engine_list):
        for j, e2 in enumerate(engine_list):
            if i >= j:
                continue
            pairs.append((e1, e2))

    rounds = max(2, GAMES_PER_PAIR)
    matches = []
    game_id = 1

    for round_idx in range(rounds):
        round_pairs = pairs[:]
        random.shuffle(round_pairs)

        for e1, e2 in round_pairs:
            # Alternate colors across rounds for fairness.
            white, black = (e1, e2) if round_idx % 2 == 0 else (e2, e1)
            matches.append((white, black, game_id))
            game_id += 1

    return matches


def play_game(white: Engine, black: Engine, game_id: int):
    white_runner = EngineRunner(white)
    black_runner = EngineRunner(black)
    white_runner.start()
    black_runner.start()

    board = chess.Board()
    game_info = {'id': game_id, 'white': white, 'black': black, 'board': board}
    result = "1/2-1/2"
    end_reason = "normal"

    with lock:
        active_games.append(game_info)

    try:
        while not board.is_game_over():
            current = white if board.turn else black
            runner = white_runner if board.turn else black_runner
            # Give extra startup slack for the first move from each side under heavy parallel load.
            timeout_sec = OPENING_MOVE_TIMEOUT_SEC if board.fullmove_number == 1 else MOVE_TIMEOUT_SEC
            uci = runner.get_move(board.fen(), timeout_sec=timeout_sec)

            if not uci or uci == "0000":
                result = "0-1" if board.turn else "1-0"
                end_reason = f"forfeit: {'white' if board.turn else 'black'} timeout/empty move"
                break

            try:
                board.push_uci(uci)
            except:
                result = "0-1" if board.turn else "1-0"
                end_reason = f"forfeit: {'white' if board.turn else 'black'} invalid move '{uci}'"
                break

            time.sleep(0.12)

        if board.is_game_over():
            result = board.result()
            end_reason = "normal"
    finally:
        white_runner.stop()
        black_runner.stop()

        os.makedirs("tournament/endgame", exist_ok=True)
        try:
            filename = f"tournament/endgame/game_{game_id:03d}_{white.name}_vs_{black.name}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Game {game_id}: {white.name} (White) vs {black.name} (Black)\n")
                f.write(f"Result: {result}\n")
                f.write(f"End reason: {end_reason}\n")
                f.write(f"Final position at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(str(board) + "\n")
        except Exception:
            pass

        with lock:
            if result == "1-0":
                white.score += 1
                white.elo, black.elo = update_elo(white.elo, black.elo, 1.0)
            elif result == "0-1":
                black.score += 1
                black.elo, white.elo = update_elo(black.elo, white.elo, 1.0)
            else:
                white.score += 0.5
                black.score += 0.5
                white.elo, black.elo = update_elo(white.elo, black.elo, 0.5)

            white.games += 1
            black.games += 1

            if game_info in active_games:
                active_games.remove(game_info)

    return result


def main():
    global engines
    files = [f for f in os.listdir('.') if f.startswith("Trinity-") and f.endswith(".py")]
    files.sort(key=lambda x: [int(part) if part.isdigit() else part for part in x[8:-3].replace('.', ' ').split()])

    engines = [Engine(f) for f in files]

    print(f"Found {len(engines)} engines: {[e.name for e in engines]}\n")
    print(f"Starting async tournament with max {MAX_CONCURRENT_GAMES} concurrent games...\n")

    # Background display thread
    def display_loop():
        while True:
            try:
                clear()
                print_leaderboard()
                print_boards_side_by_side()
                time.sleep(0.08)
            except:
                break

    display_thread = threading.Thread(target=display_loop, daemon=True)
    display_thread.start()

    # Build randomized rounds so all pairs are covered before extra rematches.
    matches = build_match_schedule(engines)

    threads = []
    for white, black, gid in matches:
        t = threading.Thread(target=play_game, args=(white, black, gid), daemon=True)
        t.start()
        threads.append(t)

        while sum(1 for t in threads if t.is_alive()) >= MAX_CONCURRENT_GAMES:
            time.sleep(0.1)

    for t in threads:
        t.join()

    # Final save and display
    save_tournament_results()
    clear()
    print_leaderboard()
    print("\n🎉 TOURNAMENT COMPLETE! Results saved to tournament/ folder.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTournament stopped.")