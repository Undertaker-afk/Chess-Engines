import sys
import time
import random

# ==============================================================================
# ZOBRIST HASHING (Memory/Transposition Table optimization)
# ==============================================================================
PIECES = 'PNBRQKpnbrqk'
ZOBRIST_PIECES = {p: [random.getrandbits(64) for _ in range(128)] for p in PIECES}
ZOBRIST_TURN = random.getrandbits(64)
ZOBRIST_CASTLING = {c: random.getrandbits(64) for c in 'KQkq'}
ZOBRIST_EP = [random.getrandbits(64) for _ in range(128)]

def get_hash(board, turn, castling, ep_sq):
    h = 0
    for sq in range(128):
        if not (sq & 0x88):
            p = board[sq]
            if p != '.':
                h ^= ZOBRIST_PIECES[p][sq]
    if turn == 'b': h ^= ZOBRIST_TURN
    for c in castling:
        if c in ZOBRIST_CASTLING: h ^= ZOBRIST_CASTLING[c]
    if ep_sq != -1: h ^= ZOBRIST_EP[ep_sq]
    return h

# ==============================================================================
# EXPANDED PIECE-SQUARE TABLES (The "Brain" of the Engine)
# High-resolution PeSTO tables for Middlegame (MG) and Endgame (EG)
# ==============================================================================
PIECE_VALUES_MG = {'P': 82, 'N': 337, 'B': 365, 'R': 477, 'Q': 1025, 'K': 0}
PIECE_VALUES_EG = {'P': 94, 'N': 281, 'B': 297, 'R': 512, 'Q': 936, 'K': 0}

# Extensive tables for positional evaluation
PST = {
    'P': {
        'mg': [
             0,   0,   0,   0,   0,   0,   0,   0,
            98, 134,  61,  95,  68, 126,  34, -11,
            -6,   7,  26,  31,  65,  56,  25, -20,
           -14,  13,   6,  21,  23,  12,  17, -23,
           -27,  -2,  -5,  12,  17,   6,  10, -25,
           -26,  -4,  -4, -10,   3,   3,  33, -12,
           -35,  -1, -20, -23, -15,  24,  38, -22,
             0,   0,   0,   0,   0,   0,   0,   0
        ],
        'eg': [
             0,   0,   0,   0,   0,   0,   0,   0,
           178, 173, 158, 134, 147, 132, 165, 187,
            94, 100,  85,  67,  56,  53,  82,  84,
            32,  24,  13,   5,  -2,   4,  17,  17,
            13,   9,  -3,  -7,  -7,  -8,   3,  -1,
             4,   7,  -6,   1,   0,  -5,  -1,  -8,
            13,   8,   8,  10,  13,   0,   2,  -7,
             0,   0,   0,   0,   0,   0,   0,   0
        ]
    },
    'N': {
        'mg': [
            -167, -89, -34, -49,  61, -97, -15, -107,
             -73, -41,  72,  36,  23,  62,   7,  -17,
             -47,  60,  37,  65,  84, 129,  73,   44,
              -9,  17,  19,  53,  37,  69,  18,   22,
             -13,   4,  16,  13,  28,  19,  21,   -8,
             -23,  -9,  12,  10,  19,  17,  25,  -16,
             -29, -53, -12,  -3,  -1,  18, -14,  -19,
            -105, -21, -58, -33, -17, -28, -19,  -23
        ],
        'eg': [
            -58, -38, -13, -28, -31, -27, -63, -99,
            -25,  -8, -25,  -2,  -9, -25, -24, -52,
            -24, -20,  10,   9,  -1,  -9, -19, -41,
            -17,   3,  22,  22,  22,  11,   8, -18,
            -18,  -6,  16,  25,  16,  17,   4, -18,
            -23,  -3,  -1,  15,  10,  -3, -20, -22,
            -42, -20, -10,  -5,  -2, -20, -23, -44,
            -29, -51, -23, -38, -22, -27, -38, -46
        ]
    },
    'B': {
        'mg': [
            -29,   4, -82, -37, -25, -42,   7,  -8,
            -26,  16, -18, -13,  30,  59,  18, -47,
            -16,  37,  43,  40,  35,  50,  37,  -2,
             -4,   5,  19,  50,  37,  37,   7,  -2,
             -6,  13,  13,  26,  34,  12,  10,   4,
              0,  15,  15,  15,  14,  27,  18,  10,
              4,  15,  16,   0,   7,  21,  33,   1,
            -33,  -3, -14, -21, -13, -12, -39, -21
        ],
        'eg': [
            -23,  -9, -23,  -5,  -9, -16,  -5, -17,
            -14, -18,  -7,  -1,   4,  -9, -15, -27,
            -12,  -3,   8,  10,  13,   3,  -7, -15,
             -6,   3,  13,  19,   7,  10,  -3,  -9,
             -3,   9,  12,   9,  14,  10,   3,   2,
              2,  -8,   0,  -1,  -2,   6,   0,   4,
             -8,  -4,   7, -12,  -3, -13,  -4, -14,
            -14, -21, -11,  -8,  -7,  -9, -17, -24
        ]
    },
    'R': {
        'mg': [
             32,  42,  32,  51,  63,   9,  31,  43,
             27,  32,  58,  62,  80,  67,  26,  44,
             -5,  19,  26,  36,  17,  45,  61,  16,
            -24, -11,   7,  26,  24,  35,  -8, -20,
            -36, -26, -12,  -1,   9,  -7,   6, -23,
            -45, -25, -16, -17,   3,   0,  -5, -33,
            -44, -16, -20,  -9,  -1,  11,  -6, -71,
            -19, -13,   1,  17,  16,   7, -37, -26
        ],
        'eg': [
            13,  10,  18,  15,  12,  12,   8,   5,
            11,  13,  13,  11,  -3,   3,   8,   3,
             7,   7,   7,   5,   4,  -3,  -5,  -3,
             4,   3,  13,   1,   2,   1,  -1,   2,
             3,   5,   8,   4,  -5,  -6,  -8, -11,
            -4,   0,  -5,  -1,  -7, -12,  -8, -16,
            -6,  -6,   0,   2,  -9,  -9, -11,  -3,
            -9,   2,   3,  -1,  -5, -13,   4, -20
        ]
    },
    'Q': {
        'mg': [
            -28,   0,  29,  12,  59,  44,  43,  45,
            -24, -39,  -5,   1, -16,  57,  28,  54,
            -13, -17,   7,   8,  29,  56,  47,  57,
            -27, -27, -16, -16,  -1,  17,  -2,   1,
             -9, -26,  -9, -10,  -2,  -4,   3,  -3,
            -14,   2, -11,  -2,  -5,   2,  14,   5,
            -35,  -8,  11,   2,   8,  15,  -3,   1,
             -1, -18,  -9,  10, -15, -25, -31, -50
        ],
        'eg': [
             -9,  22,  22,  27,  27,  19,  10,  20,
            -17,  20,  32,  41,  58,  25,  30,   0,
            -20,   6,   9,  49,  47,  35,  19,   9,
              3,  22,  24,  45,  57,  40,  57,  36,
            -18,  28,  19,  47,  31,  34,  12,  11,
             16,  20,  22,  51,  25,  15,  14,  13,
            -22,  33,   3,  22,  24,   1,  14,  -8,
            -16, -27,  28, -14,  -2,  -5,  11, -21
        ]
    },
    'K': {
        'mg': [
            -65,  23,  16, -15, -56, -34,   2,  13,
             29,  -1, -20,  -7,  -8,  -4, -38, -29,
             -9,  24,   2, -16, -20,   6,  22, -22,
            -17, -20, -12, -27, -30, -25, -14, -36,
            -49,  -1, -27, -39, -46, -44, -33, -51,
            -14, -14, -22, -46, -44, -30, -15, -27,
              1,   7,  -8, -64, -43, -16,   9,   8,
            -15,  36,  12, -54,   8, -28,  24,  14
        ],
        'eg': [
            -74, -35, -18, -18, -11,  15,   4, -17,
            -12,  17,  14,  17,  17,  38,  23,  11,
             10,  17,  23,  15,  20,  45,  44,  13,
             -8,  22,  24,  27,  26,  33,  26,   3,
            -18,  -4,  21,  24,  27,  23,   9, -11,
            -19,  -3,  11,  21,  23,  16,   7,  -9,
            -27, -11,   4,  13,  14,   4,  -5, -17,
            -53, -34, -21, -11, -28, -14, -24, -43
        ]
    }
}

# 0x88 PST Mapping
PST_MG_0x88 = {p: [0]*128 for p in PIECE_VALUES_MG.keys()}
PST_EG_0x88 = {p: [0]*128 for p in PIECE_VALUES_EG.keys()}

def initialize_psts():
    for p in PST:
        for sq in range(64):
            rank, file = sq // 8, sq % 8
            sq0x88 = (7 - rank) * 16 + file
            PST_MG_0x88[p][sq0x88] = PST[p]['mg'][sq]
            PST_EG_0x88[p][sq0x88] = PST[p]['eg'][sq]

initialize_psts()

# ==============================================================================
# SEARCH STATE & CONFIG
# ==============================================================================
TT = {}
HISTORY = [[0] * 128 for _ in range(128)]
KILLERS = [[None, None] for _ in range(256)]
NODES = 0
START_TIME = 0
TIME_LIMIT = 4.80 # Leave buffer for overhead
TIMEOUT = False

def clear_search_data():
    global HISTORY, KILLERS, NODES
    # Transposition Table management: clear if too large for memory
    if len(TT) > 800000:
        TT.clear()
    HISTORY = [[0] * 128 for _ in range(128)]
    KILLERS = [[None, None] for _ in range(256)]
    NODES = 0

# ==============================================================================
# MOVE GENERATION & BOARD LOGIC
# ==============================================================================
def sq_to_str(sq):
    return chr((sq & 7) + ord('a')) + str((sq >> 4) + 1)

def str_to_sq(s):
    return (int(s[1]) - 1) * 16 + (ord(s[0]) - ord('a'))

def is_attacked(board, sq, attacker_is_white):
    # Pawns
    p_offsets = [-15, -17] if attacker_is_white else [15, 17]
    for d in p_offsets:
        atk = sq + d
        if not (atk & 0x88) and board[atk] == ('P' if attacker_is_white else 'p'):
            return True
    # Knights
    for d in [33, 31, 18, 14, -14, -18, -31, -33]:
        atk = sq + d
        if not (atk & 0x88) and board[atk] == ('N' if attacker_is_white else 'n'):
            return True
    # King
    for d in [16, -16, 1, -1, 17, 15, -15, -17]:
        atk = sq + d
        if not (atk & 0x88) and board[atk] == ('K' if attacker_is_white else 'k'):
            return True
    # Sliders
    # Rooks/Queens
    for d in [16, -16, 1, -1]:
        atk = sq + d
        while not (atk & 0x88):
            p = board[atk]
            if p != '.':
                if p == ('R' if attacker_is_white else 'r') or p == ('Q' if attacker_is_white else 'q'):
                    return True
                break
            atk += d
    # Bishops/Queens
    for d in [17, 15, -15, -17]:
        atk = sq + d
        while not (atk & 0x88):
            p = board[atk]
            if p != '.':
                if p == ('B' if attacker_is_white else 'b') or p == ('Q' if attacker_is_white else 'q'):
                    return True
                break
            atk += d
    return False

def get_legal_moves(board, turn, ep_sq, castling):
    moves = []
    is_white = (turn == 'w')
    
    # Pre-calculate king position
    king_char = 'K' if is_white else 'k'
    king_sq = -1
    for s in range(128):
        if not (s & 0x88) and board[s] == king_char:
            king_sq = s
            break

    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p == '.' or p.isupper() != is_white: continue
        
        pu = p.upper()
        
        # Pawn Logic
        if pu == 'P':
            d = 16 if is_white else -16
            start_rank = 1 if is_white else 6
            prom_rank = 7 if is_white else 0
            
            # Forward
            to = sq + d
            if not (to & 0x88) and board[to] == '.':
                if (to >> 4) == prom_rank:
                    for promo in 'QRBN' if is_white else 'qrbn':
                        moves.append((sq, to, promo, 'n'))
                else:
                    moves.append((sq, to, None, 'n'))
                    if (sq >> 4) == start_rank:
                        to2 = sq + 2 * d
                        if board[to2] == '.':
                            moves.append((sq, to2, None, 'n'))
            
            # Captures
            for cd in [d-1, d+1]:
                if not (cd & 0x88):
                    to = sq + cd
                    if not (to & 0x88):
                        target = board[to]
                        if target != '.' and target.isupper() != is_white:
                            if (to >> 4) == prom_rank:
                                for promo in 'QRBN' if is_white else 'qrbn':
                                    moves.append((sq, to, promo, 'n'))
                            else:
                                moves.append((sq, to, None, 'n'))
                        elif to == ep_sq:
                            moves.append((sq, to, None, 'e'))

        # Sliding Pieces
        elif pu in 'RBQ':
            dirs = []
            if pu in 'RQ': dirs.extend([16, -16, 1, -1])
            if pu in 'BQ': dirs.extend([17, 15, -15, -17])
            for d in dirs:
                to = sq + d
                while not (to & 0x88):
                    target = board[to]
                    if target == '.':
                        moves.append((sq, to, None, 'n'))
                    else:
                        if target.isupper() != is_white:
                            moves.append((sq, to, None, 'n'))
                        break
                    to += d
                    
        # Knight
        elif pu == 'N':
            for d in [33, 31, 18, 14, -14, -18, -31, -33]:
                to = sq + d
                if not (to & 0x88):
                    target = board[to]
                    if target == '.' or target.isupper() != is_white:
                        moves.append((sq, to, None, 'n'))
                        
        # King
        elif pu == 'K':
            for d in [1, -1, 16, -16, 17, 15, -15, -17]:
                to = sq + d
                if not (to & 0x88):
                    target = board[to]
                    if target == '.' or target.isupper() != is_white:
                        moves.append((sq, to, None, 'n'))
            
            # Castling
            if is_white:
                if 'K' in castling and board[5] == '.' and board[6] == '.' and board[7] == 'R':
                    if not is_attacked(board, 4, False) and not is_attacked(board, 5, False) and not is_attacked(board, 6, False):
                        moves.append((4, 6, None, 'c'))
                if 'Q' in castling and board[3] == '.' and board[2] == '.' and board[1] == '.' and board[0] == 'R':
                    if not is_attacked(board, 4, False) and not is_attacked(board, 3, False) and not is_attacked(board, 2, False):
                        moves.append((4, 2, None, 'c'))
            else:
                if 'k' in castling and board[117] == '.' and board[118] == '.' and board[119] == 'r':
                    if not is_attacked(board, 116, True) and not is_attacked(board, 117, True) and not is_attacked(board, 118, True):
                        moves.append((116, 118, None, 'c'))
                if 'q' in castling and board[115] == '.' and board[114] == '.' and board[113] == '.' and board[112] == 'r':
                    if not is_attacked(board, 116, True) and not is_attacked(board, 115, True) and not is_attacked(board, 114, True):
                        moves.append((116, 114, None, 'c'))
                        
    # Filter for legality
    legal_moves = []
    for m in moves:
        f, t, pr, tp = m
        # Manual apply
        captured = board[t]
        p_at_f = board[f]
        board[t] = pr if pr else p_at_f
        board[f] = '.'
        cap_sq = -1
        if tp == 'e':
            cap_sq = t - 16 if is_white else t + 16
            captured = board[cap_sq]
            board[cap_sq] = '.'
        
        k_pos = t if p_at_f.upper() == 'K' else king_sq
        if not is_attacked(board, k_pos, not is_white):
            legal_moves.append(m)
            
        # Undo
        board[f] = p_at_f
        board[t] = captured if tp != 'e' else '.'
        if tp == 'e': board[cap_sq] = captured
        
    return legal_moves

def apply_move(board, m, turn, castling):
    f, t, pr, tp = m
    p = board[f]
    captured = board[t]
    board[t] = pr if pr else p
    board[f] = '.'
    
    cap_sq = -1
    if tp == 'e':
        cap_sq = t - 16 if turn == 'w' else t + 16
        captured = board[cap_sq]
        board[cap_sq] = '.'
    elif tp == 'c':
        if t == 6: board[5] = 'R'; board[7] = '.'
        elif t == 2: board[3] = 'R'; board[0] = '.'
        elif t == 118: board[117] = 'r'; board[119] = '.'
        elif t == 114: board[115] = 'r'; board[112] = '.'
        
    new_ep = -1
    if p.upper() == 'P' and abs(f - t) == 32:
        new_ep = f + 16 if turn == 'w' else f - 16
        
    new_cas = list(castling)
    if 'K' in new_cas and (f == 4 or f == 7 or t == 7): new_cas = [c for c in new_cas if c != 'K']
    if 'Q' in new_cas and (f == 4 or f == 0 or t == 0): new_cas = [c for c in new_cas if c != 'Q']
    if 'k' in new_cas and (f == 116 or f == 119 or t == 119): new_cas = [c for c in new_cas if c != 'k']
    if 'q' in new_cas and (f == 116 or f == 112 or t == 112): new_cas = [c for c in new_cas if c != 'q']
    new_cas_str = "".join(new_cas) if new_cas else "-"
    
    return captured, cap_sq, new_ep, new_cas_str

def undo_move(board, m, turn, captured, cap_sq):
    f, t, pr, tp = m
    p = board[t]
    if pr: p = 'P' if turn == 'w' else 'p'
    board[f] = p
    board[t] = captured if tp != 'e' else '.'
    if tp == 'e':
        board[cap_sq] = captured
    elif tp == 'c':
        if t == 6: board[7] = 'R'; board[5] = '.'
        elif t == 2: board[0] = 'R'; board[3] = '.'
        elif t == 118: board[119] = 'r'; board[117] = '.'
        elif t == 114: board[112] = 'r'; board[115] = '.'

# ==============================================================================
# EVALUATION (Heuristics & Knowledge)
# ==============================================================================
def evaluate(board, turn):
    mg, eg = 0, 0
    phase = 0
    
    # Bishop pair detectors
    w_bishops, b_bishops = 0, 0
    
    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p == '.': continue
        
        pu = p.upper()
        # Phase calculation
        if pu == 'N' or pu == 'B': phase += 1
        elif pu == 'R': phase += 2
        elif pu == 'Q': phase += 4
        
        # Mirror index for black pieces
        idx = sq if p.isupper() else sq ^ 112
        
        val_mg = PIECE_VALUES_MG[pu] + PST_MG_0x88[pu][idx]
        val_eg = PIECE_VALUES_EG[pu] + PST_EG_0x88[pu][idx]
        
        if p.isupper():
            mg += val_mg
            eg += val_eg
            if pu == 'B': w_bishops += 1
        else:
            mg -= val_mg
            eg -= val_eg
            if pu == 'B': b_bishops += 1
            
    # Bishop pair bonus
    if w_bishops >= 2: mg += 30; eg += 50
    if b_bishops >= 2: mg -= 30; eg -= 50
    
    # Tapered eval
    phase = min(phase, 24)
    score = (mg * phase + eg * (24 - phase)) // 24
    return score if turn == 'w' else -score

# ==============================================================================
# SEARCH (The Engine Core)
# ==============================================================================
def order_moves(moves, board, ply, tt_move):
    scored = []
    for m in moves:
        f, t, pr, tp = m
        score = 0
        if m == tt_move:
            score = 1000000
        elif board[t] != '.' or tp == 'e':
            # MVV-LVA
            vic = PIECE_VALUES_MG.get(board[t].upper() if board[t] != '.' else 'P', 0)
            atk = PIECE_VALUES_MG.get(board[f].upper(), 0)
            score = 900000 + vic - (atk // 10)
        elif pr:
            score = 800000 + PIECE_VALUES_MG.get(pr.upper(), 0)
        elif m == KILLERS[ply][0]:
            score = 700000
        elif m == KILLERS[ply][1]:
            score = 600000
        else:
            score = HISTORY[f][t]
            
        scored.append((score, m))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored]

def quiesce(board, turn, alpha, beta, ply):
    global NODES, TIMEOUT
    NODES += 1
    if (NODES & 1023) == 0 and time.time() - START_TIME > TIME_LIMIT:
        TIMEOUT = True
        return 0

    stand_pat = evaluate(board, turn)
    if stand_pat >= beta: return beta
    if stand_pat > alpha: alpha = stand_pat
    
    moves = get_legal_moves(board, turn, -1, '-')
    captures = [m for m in moves if board[m[1]] != '.' or m[3] == 'e']
    captures = order_moves(captures, board, ply, None)
    
    for m in captures:
        cap, csq, nep, ncas = apply_move(board, m, turn, '-')
        res = -quiesce(board, 'b' if turn == 'w' else 'w', -beta, -alpha, ply + 1)
        undo_move(board, m, turn, cap, csq)
        
        if res >= beta: return beta
        if res > alpha: alpha = res
    return alpha

def search(board, turn, ep_sq, castling, depth, alpha, beta, ply, can_null=True):
    global NODES, TIMEOUT
    NODES += 1
    if (NODES & 1023) == 0 and time.time() - START_TIME > TIME_LIMIT:
        TIMEOUT = True
        return 0, None
        
    if depth <= 0:
        return quiesce(board, turn, alpha, beta, ply), None

    # Zobrist / TT Lookup
    h = get_hash(board, turn, castling, ep_sq)
    tt_move = None
    if h in TT:
        entry_d, entry_f, entry_v, entry_m = TT[h]
        if entry_d >= depth:
            if entry_f == 'E': return entry_v, entry_m
            if entry_f == 'L' and entry_v >= beta: return entry_v, entry_m
            if entry_f == 'U' and entry_v <= alpha: return entry_v, entry_m
        tt_move = entry_m

    # Null Move Pruning
    if can_null and depth >= 3:
        # Check if we have pieces (not just pawns) to avoid zugzwang
        has_pieces = False
        for s in range(128):
            if not (s & 0x88) and board[s].isupper() == (turn == 'w') and board[s].upper() in 'NBRQ':
                has_pieces = True; break
        if has_pieces:
            score, _ = search(board, 'b' if turn == 'w' else 'w', -1, castling, depth - 3, -beta, -beta + 1, ply + 1, False)
            if -score >= beta:
                return beta, None

    # Internal Iterative Deepening
    if tt_move is None and depth >= 5:
        _, tt_move = search(board, turn, ep_sq, castling, depth - 2, alpha, beta, ply, False)

    moves = get_legal_moves(board, turn, ep_sq, castling)
    if not moves:
        k_char = 'K' if turn == 'w' else 'k'
        k_sq = -1
        for s in range(128):
            if not (s & 0x88) and board[s] == k_char: k_sq = s; break
        if is_attacked(board, k_sq, turn == 'b'):
            return -30000 + ply, None
        return 0, None

    moves = order_moves(moves, board, ply, tt_move)
    best_m = None
    best_v = -50000
    orig_alpha = alpha
    
    for i, m in enumerate(moves):
        cap, csq, nep, ncas = apply_move(board, m, turn, castling)
        
        # PVS + LMR
        if i == 0:
            val, _ = search(board, 'b' if turn == 'w' else 'w', nep, ncas, depth - 1, -beta, -alpha, ply + 1)
            val = -val
        else:
            # LMR
            reduction = 0
            if depth >= 3 and i >= 4 and cap == '.' and m[3] != 'e':
                reduction = 1
            
            val, _ = search(board, 'b' if turn == 'w' else 'w', nep, ncas, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1)
            val = -val
            if val > alpha and reduction > 0:
                val, _ = search(board, 'b' if turn == 'w' else 'w', nep, ncas, depth - 1, -alpha - 1, -alpha, ply + 1)
                val = -val
            if val > alpha:
                val, _ = search(board, 'b' if turn == 'w' else 'w', nep, ncas, depth - 1, -beta, -alpha, ply + 1)
                val = -val
        
        undo_move(board, m, turn, cap, csq)
        if TIMEOUT: return 0, None
        
        if val > best_v:
            best_v = val
            best_m = m
            if val > alpha:
                alpha = val
                if alpha >= beta:
                    # History / Killers
                    if cap == '.' and m[3] != 'e':
                        HISTORY[m[0]][m[1]] += depth * depth
                        if KILLERS[ply][0] != m:
                            KILLERS[ply][1] = KILLERS[ply][0]
                            KILLERS[ply][0] = m
                    break
                    
    # TT Store
    if not TIMEOUT:
        flag = 'E'
        if best_v <= orig_alpha: flag = 'U'
        elif best_v >= beta: flag = 'L'
        TT[h] = (depth, flag, best_v, best_m)
        
    return best_v, best_m

def get_best_move(fen):
    global START_TIME, TIMEOUT
    clear_search_data()
    START_TIME = time.time()
    TIMEOUT = False
    
    # Parse FEN
    board = ['.'] * 128
    parts = fen.split()
    rks = parts[0].split('/')
    for r in range(8):
        f = 0
        for char in rks[r]:
            if char.isdigit(): f += int(char)
            else:
                board[(7 - r) * 16 + f] = char
                f += 1
    turn = parts[1]
    castling = parts[2]
    ep_sq = str_to_sq(parts[3]) if parts[3] != '-' else -1
    
    best_move_final = None
    # Iterative Deepening
    for d in range(1, 100):
        val, m = search(board, turn, ep_sq, castling, d, -50000, 50000, 0)
        if TIMEOUT: break
        if m: best_move_final = m
        if val > 20000 or val < -20000: break # Found mate
        
    if best_move_final:
        f, t, pr, tp = best_move_final
        res = sq_to_str(f) + sq_to_str(t)
        if pr: res += pr.lower()
        return res
    return "0000"

# ==============================================================================
# ENTRY POINT
# ==============================================================================
def main():
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        # Assume input is a FEN
        if line.count('/') >= 7:
            try:
                move = get_best_move(line)
                sys.stdout.write(move + "\n")
                sys.stdout.flush()
            except Exception:
                # Emergency move
                sys.stdout.write("e2e4\n")
                sys.stdout.flush()

if __name__ == "__main__":
    main()