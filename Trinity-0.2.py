import sys
import time

# ==============================================================================
# EVALUATION & HEURISTICS (Tapered Eval)
# ==============================================================================

# Base material values for Middlegame (MG) and Endgame (EG)
PIECE_VALUES_MG = {'P': 82, 'N': 337, 'B': 365, 'R': 477, 'Q': 1025, 'K': 0}
PIECE_VALUES_EG = {'P': 94, 'N': 281, 'B': 297, 'R': 512, 'Q': 936, 'K': 0}

# Advanced Piece-Square Tables (PeSTO-inspired)
# 8x8 tables, mapped to 0x88 below
MG_PST = {
    'P': [
          0,   0,   0,   0,   0,   0,   0,   0,
         98, 134,  61,  95,  68, 126,  34, -11,
         -6,   7,  26,  31,  65,  56,  25, -20,
        -14,  13,   6,  21,  23,  12,  17, -23,
        -27,  -2,  -5,  12,  17,   6,  10, -25,
        -26,  -4,  -4, -10,   3,   3,  33, -12,
        -35,  -1, -20, -23, -15,  24,  38, -22,
          0,   0,   0,   0,   0,   0,   0,   0
    ],
    'N': [
        -167, -89, -34, -49,  61, -97, -15, -107,
         -73, -41,  72,  36,  23,  62,   7,  -17,
         -47,  60,  37,  65,  84, 129,  73,   44,
          -9,  17,  19,  53,  37,  69,  18,   22,
         -13,   4,  16,  13,  28,  19,  21,   -8,
         -23,  -9,  12,  10,  19,  17,  25,  -16,
         -29, -53, -12,  -3,  -1,  18, -14,  -19,
        -105, -21, -58, -33, -17, -28, -19,  -23
    ],
    'B': [
        -29,   4, -82, -37, -25, -42,   7,  -8,
        -26,  16, -18, -13,  30,  59,  18, -47,
        -16,  37,  43,  40,  35,  50,  37,  -2,
         -4,   5,  19,  50,  37,  37,   7,  -2,
         -6,  13,  13,  26,  34,  12,  10,   4,
          0,  15,  15,  15,  14,  27,  18,  10,
          4,  15,  16,   0,   7,  21,  33,   1,
        -33,  -3, -14, -21, -13, -12, -39, -21
    ],
    'R': [
         32,  42,  32,  51,  63,  9,  31,  43,
         27,  32,  58,  62,  80, 67,  26,  44,
         -5,  19,  26,  36,  17, 45,  61,  16,
        -24, -11,   7,  26,  24, 35,  -8, -20,
        -36, -26, -12,  -1,   9, -7,   6, -23,
        -45, -25, -16, -17,   3,  0,  -5, -33,
        -44, -16, -20,  -9,  -1, 11,  -6, -71,
        -19, -13,   1,  17,  16,  7, -37, -26
    ],
    'Q': [
        -28,   0,  29,  12,  59,  44,  43,  45,
        -24, -39,  -5,   1, -16,  57,  28,  54,
        -13, -17,   7,   8,  29,  56,  47,  57,
        -27, -27, -16, -16,  -1,  17,  -2,   1,
         -9, -26,  -9, -10,  -2,  -4,   3,  -3,
        -14,   2, -11,  -2,  -5,   2,  14,   5,
        -35,  -8,  11,   2,   8,  15,  -3,   1,
         -1, -18,  -9,  10, -15, -25, -31, -50
    ],
    'K': [
        -65,  23,  16, -15, -56, -34,   2,  13,
         29,  -1, -20,  -7,  -8,  -4, -38, -29,
         -9,  24,   2, -16, -20,   6,  22, -22,
        -17, -20, -12, -27, -30, -25, -14, -36,
        -49,  -1, -27, -39, -46, -44, -33, -51,
        -14, -14, -22, -46, -44, -30, -15, -27,
          1,   7,  -8, -64, -43, -16,   9,   8,
        -15,  36,  12, -54,   8, -28,  24,  14
    ]
}

EG_PST = {
    'P': [
          0,   0,   0,   0,   0,   0,   0,   0,
        178, 173, 158, 134, 147, 132, 165, 187,
         94, 100,  85,  67,  56,  53,  82,  84,
         32,  24,  13,   5,  -2,   4,  17,  17,
         13,   9,  -3,  -7,  -7,  -8,   3,  -1,
          4,   7,  -6,   1,   0,  -5,  -1,  -8,
         13,   8,   8,  10,  13,   0,   2,  -7,
          0,   0,   0,   0,   0,   0,   0,   0
    ],
    'N': [
        -58, -38, -13, -28, -31, -27, -63, -99,
        -25,  -8, -25,  -2,  -9, -25, -24, -52,
        -24, -20,  10,   9,  -1,  -9, -19, -41,
        -17,   3,  22,  22,  22,  11,   8, -18,
        -18,  -6,  16,  25,  16,  17,   4, -18,
        -23,  -3,  -1,  15,  10,  -3, -20, -22,
        -42, -20, -10,  -5,  -2, -20, -23, -44,
        -29, -51, -23, -38, -22, -27, -38, -46
    ],
    'B': [
        -14, -21, -11,  -8,  -7,  -9, -17, -24,
         -8,  -4,   7, -12,  -3, -13,  -4, -14,
          2,  -8,   0,  -1,  -2,   6,   0,   4,
         -3,   9,  12,   9,  14,  10,   3,   2,
         -6,   3,  13,  19,   7,  10,  -3,  -9,
        -12,  -3,   8,  10,  13,   3,  -7, -15,
        -14, -18,  -7,  -1,   4,  -9, -15, -27,
        -23,  -9, -23,  -5,  -9, -16,  -5, -17
    ],
    'R': [
         13,  10,  18,  15,  12,  12,   8,   5,
         11,  13,  13,  11,  -3,   3,   8,   3,
          7,   7,   7,   5,   4,  -3,  -5,  -3,
          4,   3,  13,   1,   2,   1,  -1,   2,
          3,   5,   8,   4,  -5,  -6,  -8, -11,
         -4,   0,  -5,  -1,  -7, -12,  -8, -16,
         -6,  -6,   0,   2,  -9,  -9, -11,  -3,
         -9,   2,   3,  -1,  -5, -13,   4, -20
    ],
    'Q': [
         -9,  22,  22,  27,  27,  19,  10,  20,
        -17,  20,  32,  41,  58,  25,  30,   0,
        -20,   6,   9,  49,  47,  35,  19,   9,
          3,  22,  24,  45,  57,  40,  57,  36,
        -18,  28,  19,  47,  31,  34,  12,  11,
         16,  20,  22,  51,  25,  15,  14,  13,
        -22,  33,   3,  22,  24,   1,  14,  -8,
        -16, -27,  28, -14,  -2,  -5,  11, -21
    ],
    'K': [
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

# Convert PSTs to 0x88 structure dynamically
PST_MG_0x88 = {p: [0]*128 for p in PIECE_VALUES_MG.keys()}
PST_EG_0x88 = {p: [0]*128 for p in PIECE_VALUES_EG.keys()}

for p in PIECE_VALUES_MG.keys():
    for sq in range(64):
        rank, file = sq // 8, sq % 8
        sq_0x88 = (7 - rank) * 16 + file # White from bottom
        PST_MG_0x88[p][sq_0x88] = MG_PST[p][sq]
        PST_EG_0x88[p][sq_0x88] = EG_PST[p][sq]

# ==============================================================================
# SEARCH GLOBALS & TIME MANAGEMENT
# ==============================================================================
TT = {}           # Transposition Table
HISTORY = []      # History Heuristic table
KILLERS = []      # Killer Heuristic table
NODES = 0
TIMEOUT = False
START_TIME = 0
TIME_LIMIT = 4.85

def reset_search_structures():
    global HISTORY, KILLERS
    # Protect memory
    if len(TT) > 1000000:
        TT.clear()
    HISTORY = [[0] * 128 for _ in range(128)]
    KILLERS = [[None, None] for _ in range(128)]

# ==============================================================================
# UTILITIES & BOARD OPERATIONS
# ==============================================================================
def sq_to_str(sq):
    return chr((sq & 7) + 97) + str((sq >> 4) + 1)

def str_to_sq(s):
    return (int(s[1]) - 1) * 16 + (ord(s[0]) - 97)

def is_attacked(board, sq, by_white):
    # Pawns
    for d in ([-15, -17] if by_white else [15, 17]):
        atk = sq + d
        if not (atk & 0x88):
            p = board[atk]
            if p == ('P' if by_white else 'p'): return True
    # Knights
    for d in [33, 31, 18, 14, -14, -18, -31, -33]:
        atk = sq + d
        if not (atk & 0x88):
            p = board[atk]
            if p == ('N' if by_white else 'n'): return True
    # Kings
    for d in [16, -16, 1, -1, 17, 15, -15, -17]:
        atk = sq + d
        if not (atk & 0x88):
            p = board[atk]
            if p == ('K' if by_white else 'k'): return True
    # Sliders (Rooks/Queens)
    for d in [16, -16, 1, -1]:
        atk = sq + d
        while not (atk & 0x88):
            p = board[atk]
            if p != '.':
                if p == ('R' if by_white else 'r') or p == ('Q' if by_white else 'q'): return True
                break
            atk += d
    # Sliders (Bishops/Queens)
    for d in [17, 15, -15, -17]:
        atk = sq + d
        while not (atk & 0x88):
            p = board[atk]
            if p != '.':
                if p == ('B' if by_white else 'b') or p == ('Q' if by_white else 'q'): return True
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
            start_rank = 1 if is_white else 6
            prom_rank = 7 if is_white else 0
            rank = sq >> 4

            to = sq + d
            if not (to & 0x88) and board[to] == '.':
                if (to >> 4) == prom_rank:
                    for promo in ['q', 'r', 'b', 'n']:
                        moves.append((sq, to, promo.upper() if is_white else promo, 'normal'))
                else:
                    moves.append((sq, to, None, 'normal'))
                    if rank == start_rank:
                        to2 = sq + 2 * d
                        if not (to2 & 0x88) and board[to2] == '.':
                            moves.append((sq, to2, None, 'normal'))

            for cap_d in ([15, 17] if is_white else [-15, -17]):
                to = sq + cap_d
                if not (to & 0x88):
                    target = board[to]
                    if target != '.' and target.isupper() != is_white:
                        if (to >> 4) == prom_rank:
                            for promo in ['q', 'r', 'b', 'n']:
                                moves.append((sq, to, promo.upper() if is_white else promo, 'normal'))
                        else:
                            moves.append((sq, to, None, 'normal'))
                    elif to == ep_sq:
                        moves.append((sq, to, None, 'ep'))

        elif pu == 'N':
            for d in [33, 31, 18, 14, -14, -18, -31, -33]:
                to = sq + d
                if not (to & 0x88):
                    target = board[to]
                    if target == '.' or target.isupper() != is_white:
                        moves.append((sq, to, None, 'normal'))

        elif pu in ('R', 'Q', 'B'):
            dirs = []
            if pu in ('R', 'Q'): dirs.extend([16, -16, 1, -1])
            if pu in ('B', 'Q'): dirs.extend([17, 15, -15, -17])
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
            for d in [16, -16, 1, -1, 17, 15, -15, -17]:
                to = sq + d
                if not (to & 0x88):
                    target = board[to]
                    if target == '.' or target.isupper() != is_white:
                        moves.append((sq, to, None, 'normal'))

            if is_white:
                if 'K' in castling and board[5] == '.' and board[6] == '.' and board[7] == 'R' and sq == 4:
                    if not is_attacked(board, 4, False) and not is_attacked(board, 5, False) and not is_attacked(board, 6, False):
                        moves.append((sq, 6, None, 'castling'))
                if 'Q' in castling and board[3] == '.' and board[2] == '.' and board[1] == '.' and board[0] == 'R' and sq == 4:
                    if not is_attacked(board, 4, False) and not is_attacked(board, 3, False) and not is_attacked(board, 2, False):
                        moves.append((sq, 2, None, 'castling'))
            else:
                if 'k' in castling and board[117] == '.' and board[118] == '.' and board[119] == 'r' and sq == 116:
                    if not is_attacked(board, 116, True) and not is_attacked(board, 117, True) and not is_attacked(board, 118, True):
                        moves.append((sq, 118, None, 'castling'))
                if 'q' in castling and board[115] == '.' and board[114] == '.' and board[113] == '.' and board[112] == 'r' and sq == 116:
                    if not is_attacked(board, 116, True) and not is_attacked(board, 115, True) and not is_attacked(board, 114, True):
                        moves.append((sq, 114, None, 'castling'))
    return moves

def do_move(board, m, turn, castling):
    frm, to, promo, mtype = m
    captured = board[to]
    p = board[frm]
    board[to] = promo if promo else p
    board[frm] = '.'
    
    cap_sq = -1
    if mtype == 'ep':
        cap_sq = to - 16 if turn == 'w' else to + 16
        captured = board[cap_sq]
        board[cap_sq] = '.'
    elif mtype == 'castling':
        if to == 6: board[5] = 'R'; board[7] = '.'
        elif to == 2: board[3] = 'R'; board[0] = '.'
        elif to == 118: board[117] = 'r'; board[119] = '.'
        elif to == 114: board[115] = 'r'; board[112] = '.'
        
    new_ep = -1
    if p.upper() == 'P' and abs(frm - to) == 32:
        new_ep = frm + 16 if turn == 'w' else frm - 16
        
    new_castling = castling
    if castling != '-':
        if p == 'K': new_castling = new_castling.replace('K', '').replace('Q', '')
        elif p == 'k': new_castling = new_castling.replace('k', '').replace('q', '')
        if frm == 0 or to == 0: new_castling = new_castling.replace('Q', '')
        if frm == 7 or to == 7: new_castling = new_castling.replace('K', '')
        if frm == 112 or to == 112: new_castling = new_castling.replace('q', '')
        if frm == 119 or to == 119: new_castling = new_castling.replace('k', '')
        if not new_castling: new_castling = '-'
        
    return captured, cap_sq, new_ep, new_castling

def undo_move(board, m, turn, captured, cap_sq):
    frm, to, promo, mtype = m
    p = board[to]
    if promo: p = 'P' if turn == 'w' else 'p'
    board[frm] = p
    board[to] = captured if mtype != 'ep' else '.'
    if mtype == 'ep':
        board[cap_sq] = captured
    elif mtype == 'castling':
        if to == 6: board[7] = 'R'; board[5] = '.'
        elif to == 2: board[0] = 'R'; board[3] = '.'
        elif to == 118: board[119] = 'r'; board[117] = '.'
        elif to == 114: board[112] = 'r'; board[115] = '.'

# ==============================================================================
# EVALUATION & MOVE ORDERING
# ==============================================================================
def evaluate(board, turn):
    mg_score = 0
    eg_score = 0
    phase = 0
    
    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p == '.': continue
        
        pu = p.upper()
        if pu == 'N': phase += 1
        elif pu == 'B': phase += 1
        elif pu == 'R': phase += 2
        elif pu == 'Q': phase += 4
        
        # Mirror index for Black
        idx = sq if p.isupper() else sq ^ 112
        
        mg = PIECE_VALUES_MG[pu] + PST_MG_0x88[pu][idx]
        eg = PIECE_VALUES_EG[pu] + PST_EG_0x88[pu][idx]
        
        if p.isupper():
            mg_score += mg
            eg_score += eg
        else:
            mg_score -= mg
            eg_score -= eg
            
    phase = min(phase, 24)
    score = (mg_score * phase + eg_score * (24 - phase)) // 24
    return score if turn == 'w' else -score

def order_moves(moves, board, ply, tt_move):
    scored_moves = []
    for m in moves:
        frm, to, promo, mtype = m
        score = 0
        if m == tt_move:
            score = 10000000
        elif mtype == 'ep':
            score = 90000
        elif board[to] != '.':
            victim = PIECE_VALUES_MG.get(board[to].upper(), 0)
            attacker = PIECE_VALUES_MG.get(board[frm].upper(), 0)
            score = 80000 + victim - attacker/100.0
        elif promo:
            score = 70000 + PIECE_VALUES_MG.get(promo.upper(), 0)
        else:
            if m == KILLERS[ply][0]: score = 60000
            elif m == KILLERS[ply][1]: score = 50000
            else: score = HISTORY[frm][to]
        scored_moves.append((score, m))
    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in scored_moves]

# ==============================================================================
# SEARCH ALGORITHM (PVS, NMP, LMR)
# ==============================================================================
def quiesce(board, turn, alpha, beta, ply):
    global NODES, TIMEOUT
    NODES += 1
    if (NODES & 1023) == 0 and time.time() - START_TIME > TIME_LIMIT:
        TIMEOUT = True
        return 0

    stand_pat = evaluate(board, turn)
    if stand_pat >= beta: return beta
    if alpha < stand_pat: alpha = stand_pat
        
    moves = generate_moves(board, turn, -1, '-')
    captures = [m for m in moves if board[m[1]] != '.' or m[3] == 'ep']
    
    # Filter pseudo-legal captures down to legal
    legal_captures = []
    my_king_char = 'K' if turn == 'w' else 'k'
    king_sq = board.index(my_king_char)
    for m in captures:
        cap, cap_sq, _, _ = do_move(board, m, turn, '-')
        ksq = m[1] if m[0] == king_sq else king_sq
        if not is_attacked(board, ksq, turn == 'b'):
            legal_captures.append(m)
        undo_move(board, m, turn, cap, cap_sq)
        
    legal_captures = order_moves(legal_captures, board, ply, None)
    
    for m in legal_captures:
        cap, cap_sq, _, _ = do_move(board, m, turn, '-')
        score = -quiesce(board, 'b' if turn == 'w' else 'w', -beta, -alpha, ply + 1)
        undo_move(board, m, turn, cap, cap_sq)
        
        if score >= beta: return beta
        if score > alpha: alpha = score
    return alpha

def alpha_beta(board, turn, ep_sq, castling, depth, alpha, beta, ply, do_null=True):
    global NODES, TIMEOUT
    NODES += 1
    
    if (NODES & 1023) == 0 and time.time() - START_TIME > TIME_LIMIT:
        TIMEOUT = True
        return 0, None
        
    if depth <= 0:
        return quiesce(board, turn, alpha, beta, ply), None
        
    my_king_char = 'K' if turn == 'w' else 'k'
    king_sq = board.index(my_king_char)
    in_check = is_attacked(board, king_sq, turn == 'b')
    
    if in_check:
        depth += 1 # Check Extension

    hash_key = hash(tuple(board) + (turn, castling, ep_sq))
    tt_move = None
    if hash_key in TT:
        tt_depth, tt_flag, tt_score, tt_m = TT[hash_key]
        tt_move = tt_m
        if tt_depth >= depth:
            if tt_flag == 'EXACT': return tt_score, tt_m
            elif tt_flag == 'LOWER' and tt_score >= beta: return tt_score, tt_m
            elif tt_flag == 'UPPER' and tt_score <= alpha: return tt_score, tt_m

    # Null Move Pruning (NMP)
    if do_null and not in_check and depth >= 3 and ply > 0:
        # Quick phase check (don't null move in deep endgame)
        if sum(1 for sq in range(128) if not (sq & 0x88) and board[sq].upper() in 'NBRQ') > 2:
            score, _ = alpha_beta(board, 'b' if turn == 'w' else 'w', -1, castling, depth - 1 - 2, -beta, -beta + 1, ply + 1, False)
            score = -score
            if score >= beta:
                return beta, None

    pseudo_moves = generate_moves(board, turn, ep_sq, castling)
    moves = []
    for m in pseudo_moves:
        cap, cap_sq, _, _ = do_move(board, m, turn, castling)
        ksq = m[1] if m[0] == king_sq else king_sq
        if not is_attacked(board, ksq, turn == 'b'):
            moves.append(m)
        undo_move(board, m, turn, cap, cap_sq)

    if not moves:
        if in_check: return -30000 + ply, None
        return 0, None # Stalemate
        
    moves = order_moves(moves, board, ply, tt_move)
    orig_alpha = alpha
    best_score = -50000
    best_move = None
    moves_searched = 0

    for m in moves:
        cap, cap_sq, n_ep, n_cas = do_move(board, m, turn, castling)
        n_turn = 'b' if turn == 'w' else 'w'
        is_capture_or_promo = (cap != '.' or m[3] == 'ep' or m[2] is not None)
        
        # Principal Variation Search (PVS) with Late Move Reductions (LMR)
        if moves_searched == 0:
            score, _ = alpha_beta(board, n_turn, n_ep, n_cas, depth - 1, -beta, -alpha, ply + 1)
        else:
            # LMR
            if moves_searched >= 4 and depth >= 3 and not is_capture_or_promo and not in_check:
                score, _ = alpha_beta(board, n_turn, n_ep, n_cas, depth - 2, -alpha - 1, -alpha, ply + 1)
            else:
                score = -alpha - 1 # force full search

            # PVS full window
            if score > -alpha - 1:
                score, _ = alpha_beta(board, n_turn, n_ep, n_cas, depth - 1, -alpha - 1, -alpha, ply + 1)
                if -alpha > score > -beta:
                    score, _ = alpha_beta(board, n_turn, n_ep, n_cas, depth - 1, -beta, score, ply + 1)
                    
        score = -score
        undo_move(board, m, turn, cap, cap_sq)
        moves_searched += 1
        
        if TIMEOUT: return 0, None
            
        if score > best_score:
            best_score = score
            best_move = m
            
        if score > alpha:
            alpha = score
            
        if alpha >= beta:
            if not is_capture_or_promo:
                HISTORY[m[0]][m[1]] += depth * depth
                if KILLERS[ply][0] != m:
                    KILLERS[ply][1] = KILLERS[ply][0]
                    KILLERS[ply][0] = m
            break
            
    if not TIMEOUT:
        flag = 'EXACT'
        if best_score <= orig_alpha: flag = 'UPPER'
        elif best_score >= beta: flag = 'LOWER'
        TT[hash_key] = (depth, flag, best_score, best_move)
            
    return best_score, best_move

def get_best_move(fen):
    global START_TIME, TIMEOUT, NODES
    reset_search_structures()
    START_TIME = time.time()
    TIMEOUT = False
    NODES = 0
    
    board = ['.'] * 128
    parts = fen.split()
    ranks = parts[0].split('/')
    for r in range(8):
        f = 0
        for char in ranks[r]:
            if char.isdigit(): f += int(char)
            else:
                board[(7 - r) * 16 + f] = char
                f += 1
                
    turn = parts[1]
    castling = parts[2] if len(parts) > 2 else '-'
    ep_sq = str_to_sq(parts[3]) if len(parts) > 3 and parts[3] != '-' else -1
    
    best_move_overall = None
    for depth in range(1, 64):
        score, move = alpha_beta(board, turn, ep_sq, castling, depth, -50000, 50000, 0)
        if TIMEOUT: break
        if move: best_move_overall = move
        if score > 20000 or score < -20000: break # Forced mate
            
    if not best_move_overall:
        # Extremely fast panic fallback
        for sq in range(128):
            if sq & 0x88: continue
            if board[sq].isupper() == (turn == 'w') and board[sq] != '.':
                mvs = generate_moves(board, turn, ep_sq, castling)
                for m in mvs:
                    cap, cap_sq, _, _ = do_move(board, m, turn, castling)
                    ksq = board.index('K' if turn == 'w' else 'k')
                    if not is_attacked(board, ksq, turn == 'b'):
                        undo_move(board, m, turn, cap, cap_sq)
                        best_move_overall = m
                        break
                    undo_move(board, m, turn, cap, cap_sq)
                if best_move_overall: break
        if not best_move_overall: return "0000"
        
    frm, to, promo, _ = best_move_overall
    uci = sq_to_str(frm) + sq_to_str(to)
    if promo: uci += promo.lower()
    return uci

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        if ' ' in line and '/' in line:
            try:
                move = get_best_move(line)
                sys.stdout.write(move + "\n")
                sys.stdout.flush()
            except Exception:
                sys.stdout.write("e2e4\n") 
                sys.stdout.flush()

if __name__ == "__main__":
    main()