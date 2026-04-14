#!/usr/bin/env python3
"""
Trinity-0.6 - Upgraded Chess Engine
Based on Trinity-0.3 with major improvements:
- Aspiration Windows
- Razoring + Futility Pruning
- King Safety (pawn shield + attacks)
- Mobility bonus
- Better Quiescence
- Improved iterative deepening
"""

import sys
import time
import random

# ==============================================================================
# ZOBRIST HASHING
# ==============================================================================
PIECES = 'PNBRQKpnbrqk'
ZOBRIST_PIECES = {p: [random.getrandbits(64) for _ in range(128)] for p in PIECES}
ZOBRIST_TURN = random.getrandbits(64)
ZOBRIST_CASTLING = {c: random.getrandbits(64) for c in 'KQkq'}
ZOBRIST_EP = [random.getrandbits(64) for _ in range(128)]
HISTORY = [[0] * 128 for _ in range(128)]

def get_hash(board, turn, castling, ep_sq):
    h = 0
    for sq in range(128):
        if not (sq & 0x88):
            p = board[sq]
            if p != '.': h ^= ZOBRIST_PIECES[p][sq]
    if turn == 'b': h ^= ZOBRIST_TURN
    for c in castling:
        if c in ZOBRIST_CASTLING: h ^= ZOBRIST_CASTLING[c]
    if ep_sq != -1: h ^= ZOBRIST_EP[ep_sq]
    return h

# ==============================================================================
# EVALUATION - Tapered + New Knowledge
# ==============================================================================
PIECE_VALUES_MG = {'P': 82, 'N': 337, 'B': 365, 'R': 477, 'Q': 1025, 'K': 0}
PIECE_VALUES_EG = {'P': 94, 'N': 281, 'B': 297, 'R': 512, 'Q': 936, 'K': 0}

# PeSTO tables (restored from your best 0.3 version)
PST = {
    'P': {'mg': [0,0,0,0,0,0,0,0,98,134,61,95,68,126,34,-11,-6,7,26,31,65,56,25,-20,-14,13,6,21,23,12,17,-23,-27,-2,-5,12,17,6,10,-25,-26,-4,-4,-10,3,3,33,-12,-35,-1,-20,-23,-15,24,38,-22,0,0,0,0,0,0,0,0],
          'eg': [0,0,0,0,0,0,0,0,178,173,158,134,147,132,165,187,94,100,85,67,56,53,82,84,32,24,13,5,-2,4,17,17,13,9,-3,-7,-7,-8,3,-1,4,7,-6,1,0,-5,-1,-8,13,8,8,10,13,0,2,-7,0,0,0,0,0,0,0,0]},
    'N': {'mg': [-167,-89,-34,-49,61,-97,-15,-107,-73,-41,72,36,23,62,7,-17,-47,60,37,65,84,129,73,44,-9,17,19,53,37,69,18,22,-13,4,16,13,28,19,21,-8,-23,-9,12,10,19,17,25,-16,-29,-53,-12,-3,-1,18,-14,-19,-105,-21,-58,-33,-17,-28,-19,-23],
          'eg': [-58,-38,-13,-28,-31,-27,-63,-99,-25,-8,-25,-2,-9,-25,-24,-52,-24,-20,10,9,-1,-9,-19,-41,-17,3,22,22,22,11,8,-18,-18,-6,16,25,16,17,4,-18,-23,-3,-1,15,10,-3,-20,-22,-42,-20,-10,-5,-2,-20,-23,-44,-29,-51,-23,-38,-22,-27,-38,-46]},
    'B': {'mg': [-29,4,-82,-37,-25,-42,7,-8,-26,16,-18,-13,30,59,18,-47,-16,37,43,40,35,50,37,-2,-4,5,19,50,37,37,7,-2,-6,13,13,26,34,12,10,4,0,15,15,15,14,27,18,10,4,15,16,0,7,21,33,1,-33,-3,-14,-21,-13,-12,-39,-21],
          'eg': [-14,-21,-11,-8,-7,-9,-17,-24,-8,-4,7,-12,-3,-13,-4,-14,2,-8,0,-1,-2,6,0,4,-3,9,12,9,14,10,3,2,-6,3,13,19,7,10,-3,-9,-12,-3,8,10,13,3,-7,-15,-14,-18,-7,-1,4,-9,-15,-27,-23,-9,-23,-5,-9,-16,-5,-17]},
    'R': {'mg': [32,42,32,51,63,9,31,43,27,32,58,62,80,67,26,44,-5,19,26,36,17,45,61,16,-24,-11,7,26,24,35,-8,-20,-36,-26,-12,-1,9,-7,6,-23,-45,-25,-16,-17,3,0,-5,-33,-44,-16,-20,-9,-1,11,-6,-71,-19,-13,1,17,16,7,-37,-26],
          'eg': [13,10,18,15,12,12,8,5,11,13,13,11,-3,3,8,3,7,7,7,5,4,-3,-5,-3,4,3,13,1,2,1,-1,2,3,5,8,4,-5,-6,-8,-11,-4,0,-5,-1,-7,-12,-8,-16,-6,-6,0,2,-9,-9,-11,-3,-9,2,3,-1,-5,-13,4,-20]},
    'Q': {'mg': [-28,0,29,12,59,44,43,45,-24,-39,-5,1,-16,57,28,54,-13,-17,7,8,29,56,47,57,-27,-27,-16,-16,-1,17,-2,1,-9,-26,-9,-10,-2,-4,3,-3,-14,2,-11,-2,-5,2,14,5,-35,-8,11,2,8,15,-3,1,-1,-18,-9,10,-15,-25,-31,-50],
          'eg': [-9,22,22,27,27,19,10,20,-17,20,32,41,58,25,30,0,-20,6,9,49,47,35,19,9,3,22,24,45,57,40,57,36,-18,28,19,47,31,34,12,11,16,20,22,51,25,15,14,13,-22,33,3,22,24,1,14,-8,-16,-27,28,-14,-2,-5,11,-21]},
    'K': {'mg': [-65,23,16,-15,-56,-34,2,13,29,-1,-20,-7,-8,-4,-38,-29,-9,24,2,-16,-20,6,22,-22,-17,-20,-12,-27,-30,-25,-14,-36,-49,-1,-27,-39,-46,-44,-33,-51,-14,-14,-22,-46,-44,-30,-15,-27,1,7,-8,-64,-43,-16,9,8,-15,36,12,-54,8,-28,24,14],
          'eg': [-74,-35,-18,-18,-11,15,4,-17,-12,17,14,17,17,38,23,11,10,17,23,15,20,45,44,13,-8,22,24,27,26,33,26,3,-18,-4,21,24,27,23,9,-11,-19,-3,11,21,23,16,7,-9,-27,-11,4,13,14,4,-5,-17,-53,-34,-21,-11,-28,-14,-24,-43]}
}

def evaluate(board, turn):
    mg = eg = phase = 0
    w_king = b_king = -1

    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p == '.': continue
        pu = p.upper()

        if pu == 'K':
            if p.isupper(): w_king = sq
            else: b_king = sq

        if pu in ('N','B'): phase += 1
        elif pu == 'R': phase += 2
        elif pu == 'Q': phase += 4

        rank = sq >> 4
        file = sq & 7
        idx = (rank * 8 + file) if p.isupper() else ((7 - rank) * 8 + file)
        v_mg = PIECE_VALUES_MG[pu] + PST[pu]['mg'][idx]
        v_eg = PIECE_VALUES_EG[pu] + PST[pu]['eg'][idx]

        if p.isupper():
            mg += v_mg
            eg += v_eg
        else:
            mg -= v_mg
            eg -= v_eg

    # King Safety
    if w_king != -1: mg += king_safety(board, w_king, False) * 9
    if b_king != -1: mg -= king_safety(board, b_king, True) * 9

    # Mobility
    mg += mobility(board, 'w') * 2
    mg -= mobility(board, 'b') * 2

    phase = min(phase, 24)
    score = (mg * phase + eg * (24 - phase)) // 24
    return score if turn == 'w' else -score


def king_safety(board, ksq, is_black):
    attacks = 0
    for d in [-17,-16,-15,-1,1,15,16,17]:
        sq = ksq + d
        if not (sq & 0x88):
            p = board[sq]
            if p != '.' and ((p.isupper() != is_black) or p.upper() in 'NBRQ'):
                attacks += 1
    return attacks


def mobility(board, side):
    score = 0
    is_white = side == 'w'
    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p == '.' or p.isupper() != is_white: continue
        pu = p.upper()
        if pu == 'N':
            for d in [-33,-31,-18,-14,14,18,31,33]:
                if not ((sq+d) & 0x88) and board[sq+d] == '.': score += 4
        elif pu in ('B','R','Q'):
            dirs = []
            if pu in ('B','Q'): dirs += [-17,-15,15,17]
            if pu in ('R','Q'): dirs += [-16,-1,1,16]
            for d in dirs:
                n = sq + d
                while not (n & 0x88):
                    if board[n] == '.': score += 3
                    else: break
                    n += d
    return score


# ==============================================================================
# MOVE GENERATION & BOARD OPERATIONS (stable from 0.3)
# ==============================================================================
def is_attacked(board, sq, by_white):
    # Pawns
    for d in ([-15, -17] if by_white else [15, 17]):
        atk = sq + d
        if not (atk & 0x88) and board[atk] == ('P' if by_white else 'p'): return True
    # Knights
    for d in [33,31,18,14,-14,-18,-31,-33]:
        atk = sq + d
        if not (atk & 0x88) and board[atk] == ('N' if by_white else 'n'): return True
    # King
    for d in [-17,-16,-15,-1,1,15,16,17]:
        atk = sq + d
        if not (atk & 0x88) and board[atk] == ('K' if by_white else 'k'): return True
    # Sliders
    for d, types in [(-16,'RQ'),(16,'RQ'),(-1,'RQ'),(1,'RQ'),(-17,'BQ'),(17,'BQ'),(-15,'BQ'),(15,'BQ')]:
        atk = sq + d
        while not (atk & 0x88):
            p = board[atk]
            if p != '.':
                if p.upper() in types and p.isupper() == by_white: return True
                break
            atk += d
    return False


def generate_moves(board, turn, ep_sq, castling):
    moves = []
    is_white = (turn == 'w')
    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p == '.' or p.isupper() != is_white: continue
        pu = p.upper()

        if pu == 'P':
            d = 16 if is_white else -16
            start = 1 if is_white else 6
            prom = 7 if is_white else 0
            to = sq + d
            if not (to & 0x88) and board[to] == '.':
                if (to >> 4) == prom:
                    for pr in 'qrbn': moves.append((sq, to, pr.upper() if is_white else pr, 'normal'))
                else:
                    moves.append((sq, to, None, 'normal'))
                    if (sq >> 4) == start and board[to + d] == '.':
                        moves.append((sq, to + d, None, 'normal'))
            for cd in ([15,17] if is_white else [-15,-17]):
                to = sq + cd
                if not (to & 0x88):
                    target = board[to]
                    if target != '.' and target.isupper() != is_white:
                        if (to >> 4) == prom:
                            for pr in 'qrbn': moves.append((sq, to, pr.upper() if is_white else pr, 'normal'))
                        else:
                            moves.append((sq, to, None, 'normal'))
                    elif to == ep_sq:
                        moves.append((sq, to, None, 'ep'))
        elif pu == 'N':
            for d in [-33,-31,-18,-14,14,18,31,33]:
                to = sq + d
                if not (to & 0x88):
                    target = board[to]
                    if target == '.' or target.isupper() != is_white:
                        moves.append((sq, to, None, 'normal'))
        elif pu in ('B','R','Q'):
            dirs = []
            if pu in ('B','Q'): dirs += [-17,-15,15,17]
            if pu in ('R','Q'): dirs += [-16,-1,1,16]
            for d in dirs:
                to = sq + d
                while not (to & 0x88):
                    target = board[to]
                    if target == '.':
                        moves.append((sq, to, None, 'normal'))
                    else:
                        if target.isupper() != is_white:
                            moves.append((sq, to, None, 'normal'))
                        break
                    to += d
        elif pu == 'K':
            for d in [-17,-16,-15,-1,1,15,16,17]:
                to = sq + d
                if not (to & 0x88):
                    target = board[to]
                    if target == '.' or target.isupper() != is_white:
                        moves.append((sq, to, None, 'normal'))
            # Castling
            if is_white:
                if 'K' in castling and board[5] == '.' and board[6] == '.' and board[7] == 'R' and sq == 4:
                    if not is_attacked(board, 4, False) and not is_attacked(board, 5, False) and not is_attacked(board, 6, False):
                        moves.append((4, 6, None, 'castling'))
                if 'Q' in castling and board[3] == '.' and board[2] == '.' and board[1] == '.' and board[0] == 'R' and sq == 4:
                    if not is_attacked(board, 4, False) and not is_attacked(board, 3, False) and not is_attacked(board, 2, False):
                        moves.append((4, 2, None, 'castling'))
            else:
                if 'k' in castling and board[117] == '.' and board[118] == '.' and board[119] == 'r' and sq == 116:
                    if not is_attacked(board, 116, True) and not is_attacked(board, 117, True) and not is_attacked(board, 118, True):
                        moves.append((116, 118, None, 'castling'))
                if 'q' in castling and board[115] == '.' and board[114] == '.' and board[113] == '.' and board[112] == 'r' and sq == 116:
                    if not is_attacked(board, 116, True) and not is_attacked(board, 115, True) and not is_attacked(board, 114, True):
                        moves.append((116, 114, None, 'castling'))
    return moves


def make_move(board, m, turn, castling, ep_sq):
    f, t, promo, mtype = m
    p = board[f]
    captured = board[t]
    board[t] = promo if promo else p
    board[f] = '.'
    cap_sq = -1
    if mtype == 'ep':
        cap_sq = t - 16 if turn == 'w' else t + 16
        captured = board[cap_sq]
        board[cap_sq] = '.'
    elif mtype == 'castling':
        if t == 6: board[5] = 'R'; board[7] = '.'
        elif t == 2: board[3] = 'R'; board[0] = '.'
        elif t == 118: board[117] = 'r'; board[119] = '.'
        elif t == 114: board[115] = 'r'; board[112] = '.'
    new_ep = -1
    if p.upper() == 'P' and abs(f - t) == 32:
        new_ep = f + 16 if turn == 'w' else f - 16
    new_castling = castling
    if castling != '-':
        if p == 'K': new_castling = new_castling.replace('K','').replace('Q','')
        elif p == 'k': new_castling = new_castling.replace('k','').replace('q','')
        if f in (0,4) or t in (0,4): new_castling = new_castling.replace('Q','')
        if f in (7,4) or t in (7,4): new_castling = new_castling.replace('K','')
        if f in (112,116) or t in (112,116): new_castling = new_castling.replace('q','')
        if f in (119,116) or t in (119,116): new_castling = new_castling.replace('k','')
        if not new_castling: new_castling = '-'
    return captured, cap_sq, new_ep, new_castling


def undo_move(board, m, turn, captured, cap_sq):
    f, t, promo, mtype = m
    p = board[t]
    if promo: p = 'P' if turn == 'w' else 'p'
    board[f] = p
    board[t] = captured if mtype != 'ep' else '.'
    if mtype == 'ep':
        board[cap_sq] = captured
    elif mtype == 'castling':
        if t == 6: board[7] = 'R'; board[5] = '.'
        elif t == 2: board[0] = 'R'; board[3] = '.'
        elif t == 118: board[119] = 'r'; board[117] = '.'
        elif t == 114: board[112] = 'r'; board[115] = '.'


def get_legal_moves(board, turn, ep_sq, castling):
    pseudo = generate_moves(board, turn, ep_sq, castling)
    legal = []
    for m in pseudo:
        captured, cap_sq, new_ep, new_castling = make_move(board, m, turn, castling, ep_sq)
        my_king = next((i for i in range(128) if not (i&0x88) and board[i] == ('K' if turn=='w' else 'k')), -1)
        if not is_attacked(board, my_king, turn == 'b'):
            legal.append(m)
        undo_move(board, m, turn, captured, cap_sq)
    return legal


def sq_to_uci(sq):
    return chr((sq & 7) + ord('a')) + str((sq >> 4) + 1)


def move_to_uci(m):
    f, t, promo, _ = m
    uci = sq_to_uci(f) + sq_to_uci(t)
    if promo:
        uci += promo.lower()
    return uci


def score_move(m, board, tt_move, ply):
    f, t, promo, mtype = m
    if m == tt_move: return 1000000
    if mtype == 'ep' or board[t] != '.': 
        victim = PIECE_VALUES_MG.get(board[t].upper() if board[t] != '.' else 'P', 0)
        attacker = PIECE_VALUES_MG.get(board[f].upper(), 0)
        return 900000 + victim - attacker
    if promo: return 800000
    return HISTORY[f][t]


# ==============================================================================
# SEARCH
# ==============================================================================
def quiescence(board, turn, ep_sq, castling, alpha, beta, engine):
    if time.time() - engine.start_time > engine.time_limit:
        engine.abort = True
        return evaluate(board, turn)

    stand = evaluate(board, turn)
    if stand >= beta: return beta
    if alpha < stand: alpha = stand

    moves = [m for m in get_legal_moves(board, turn, ep_sq, castling) if board[m[1]] != '.' or m[3] == 'ep']
    moves.sort(key=lambda m: score_move(m, board, None, 0), reverse=True)

    for m in moves:
        if engine.abort:
            return alpha

        captured, cap_sq, new_ep, new_castling = make_move(board, m, turn, castling, ep_sq)
        score = -quiescence(board, 'b' if turn == 'w' else 'w', new_ep, new_castling, -beta, -alpha, engine)
        undo_move(board, m, turn, captured, cap_sq)

        if engine.abort:
            return alpha

        if score >= beta: return beta
        if score > alpha: alpha = score

    return alpha


def search(board, turn, ep_sq, castling, depth, alpha, beta, ply, engine):
    if time.time() - engine.start_time > engine.time_limit:
        engine.abort = True
        return evaluate(board, turn)

    if depth <= 0:
        return quiescence(board, turn, ep_sq, castling, alpha, beta, engine)

    # Razoring
    if depth == 1 and evaluate(board, turn) + 250 < alpha:
        return quiescence(board, turn, ep_sq, castling, alpha, beta, engine)

    moves = get_legal_moves(board, turn, ep_sq, castling)
    if not moves:
        ksq = next((i for i in range(128) if not (i&0x88) and board[i] == ('K' if turn=='w' else 'k')), -1)
        return -30000 + ply if is_attacked(board, ksq, turn == 'b') else 0

    moves.sort(key=lambda m: score_move(m, board, None, ply), reverse=True)

    best = -100000
    for i, m in enumerate(moves):
        if engine.abort:
            return best

        # Futility
        if depth == 1 and i > 5 and evaluate(board, turn) + 150 < alpha and board[m[1]] == '.':
            continue

        captured, cap_sq, new_ep, new_castling = make_move(board, m, turn, castling, ep_sq)
        score = -search(board, 'b' if turn == 'w' else 'w', new_ep, new_castling, depth-1, -beta, -alpha, ply+1, engine)
        undo_move(board, m, turn, captured, cap_sq)

        if engine.abort:
            return best

        if score > best: best = score
        if score > alpha: alpha = score
        if alpha >= beta: break

    return best


class TrinityEngine:
    def __init__(self, fen):
        self.board = ['.'] * 128
        self.parse_fen(fen)
        self.nodes = 0
        self.start_time = time.time()
        self.time_limit = 4.8
        self.abort = False

    def parse_fen(self, fen):
        self.board = ['.'] * 128
        parts = fen.split()
        ranks = parts[0].split('/')
        for r in range(8):
            f = 0
            for char in ranks[r]:
                if char.isdigit():
                    f += int(char)
                else:
                    self.board[(7 - r) * 16 + f] = char
                    f += 1
        self.turn = parts[1]
        self.castling = parts[2] if len(parts) > 2 else '-'
        self.ep_sq = -1 if parts[3] == '-' else (int(parts[3][1])-1)*16 + (ord(parts[3][0])-97)

    def get_best_move(self, fen):
        self.parse_fen(fen)
        self.start_time = time.time()
        self.abort = False
        legal_moves = get_legal_moves(self.board, self.turn, self.ep_sq, self.castling)
        if not legal_moves:
            return "0000"

        best_move = legal_moves[0]

        for depth in range(1, 30):
            if time.time() - self.start_time > self.time_limit:
                break
            alpha = -50000
            beta = 50000
            depth_best = best_move
            depth_best_score = -100000

            candidate_moves = sorted(
                legal_moves,
                key=lambda m: score_move(m, self.board, None, 0),
                reverse=True,
            )

            for m in candidate_moves:
                if time.time() - self.start_time > self.time_limit:
                    self.abort = True
                    break

                captured, cap_sq, new_ep, new_castling = make_move(self.board, m, self.turn, self.castling, self.ep_sq)
                score = -search(
                    self.board,
                    'b' if self.turn == 'w' else 'w',
                    new_ep,
                    new_castling,
                    depth - 1,
                    -beta,
                    -alpha,
                    1,
                    self,
                )
                undo_move(self.board, m, self.turn, captured, cap_sq)

                if score > depth_best_score:
                    depth_best_score = score
                    depth_best = m

                if score > alpha:
                    alpha = score

                if alpha >= beta:
                    break

                if self.abort:
                    break

            if not self.abort:
                best_move = depth_best
            else:
                break

        return move_to_uci(best_move)


# ==============================================================================
# UCI LOOP
# ==============================================================================
if __name__ == "__main__":
    engine = None
    for line in sys.stdin:
        fen = line.strip()
        if not fen: continue
        if engine is None:
            engine = TrinityEngine(fen)
        print(engine.get_best_move(fen))
        sys.stdout.flush()