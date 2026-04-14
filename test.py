import subprocess
import sys
import time
import glob
import queue
import threading
import chess

fens = [
    'rnbqkbnr/pppppppp/8/8/4P3/2N5/PPPP1PPP/R1BQKBNR b KQkq - 1 1',
    'rnbqkb1r/pppppppp/5n2/8/8/2N2N2/PPPPPPPP/R1BQKB1R w KQkq - 2 2',
    'r1bqkbnr/pppppppp/2n5/8/8/5N2/PPPPPPPP/RNBQKB1R w KQkq - 1 2',
]
MOVE_TIMEOUT = 12.0
engines = sorted(glob.glob('Trinity-*.py'))
print('Found', len(engines), 'engines')


def read_with_timeout(proc, timeout_sec):
    q = queue.Queue(maxsize=1)
    def _r():
        try:
            q.put(proc.stdout.readline(), timeout=0.01)
        except Exception:
            pass
    t = threading.Thread(target=_r, daemon=True)
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        return None
    try:
        return q.get_nowait()
    except queue.Empty:
        return ''

for e in engines:
    p = subprocess.Popen([sys.executable, e], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    ok = 0
    bad = 0
    times = []
    issues = []
    try:
        for fen in fens:
            b = chess.Board(fen)
            t0 = time.time()
            p.stdin.write(fen + '\n')
            p.stdin.flush()
            raw = read_with_timeout(p, MOVE_TIMEOUT)
            dt = time.time() - t0
            times.append(dt)
            if raw is None:
                bad += 1
                issues.append(('TIMEOUT', dt))
                break
            mv = raw.strip()
            legal = False
            try:
                m = chess.Move.from_uci(mv)
                legal = m in b.legal_moves
            except Exception:
                legal = False
            if legal:
                ok += 1
            else:
                bad += 1
                issues.append((mv if mv else 'EMPTY', dt))
    finally:
        try:
            p.terminate()
        except Exception:
            pass
        try:
            p.wait(timeout=1)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
        try:
            err = p.stderr.read().strip()
        except Exception:
            err = ''

    avg_t = sum(times)/len(times) if times else 0.0
    print(f'{e}: ok={ok} bad={bad} avg={avg_t:.3f}s')
    for issue, dt in issues:
        print(f'  issue={issue!r} time={dt:.3f}s')
    if err:
        print('  stderr_last:', err.splitlines()[-1][:220])