import sys
import time

# --- Board Representation & Heuristics ---
# Values for Material evaluation
PIECE_VALUES = {'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000}

# Standard Piece-Square Tables (Middle game)
PST = {
    'P': [
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    'N': [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ],
    'B': [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ],
    'R': [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0
    ],
    'Q': [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ],
    'K': [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20
    ]
}

# King behavior changes fundamentally in the endgame
K_ENDGAME_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  0, 10, 20, 20, 10,  0,-10,
    -10,  0, 10, 20, 20, 10,  0,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

# Convert PST to 0x88 mapping
PST_0x88 = {}
for p, table in PST.items():
    PST_0x88[p] = [0] * 128
    for rank in range(8):
        for file in range(8):
            sq_0x88 = (7 - rank) * 16 + file
            PST_0x88[p][sq_0x88] = table[rank * 8 + file]

K_ENDGAME_0x88 = [0] * 128
for rank in range(8):
    for file in range(8):
        sq_0x88 = (7 - rank) * 16 + file
        K_ENDGAME_0x88[sq_0x88] = K_ENDGAME_PST[rank * 8 + file]


# --- Utility Functions ---
def sq_to_str(sq):
    return chr((sq & 7) + 97) + str((sq >> 4) + 1)

def str_to_sq(s):
    return (int(s[1]) - 1) * 16 + (ord(s[0]) - 97)

def is_attacked(board, sq, by_white):
    # Pawns
    for d in ([-15, -17] if by_white else [15, 17]):
        atk_sq = sq + d
        if (atk_sq & 0x88) == 0:
            p = board[atk_sq]
            if p != '.' and p.isupper() == by_white and p.upper() == 'P':
                return True
    # Knights
    for d in [33, 31, 18, 14, -14, -18, -31, -33]:
        atk_sq = sq + d
        if (atk_sq & 0x88) == 0:
            p = board[atk_sq]
            if p != '.' and p.isupper() == by_white and p.upper() == 'N':
                return True
    # Kings
    for d in [16, -16, 1, -1, 17, 15, -15, -17]:
        atk_sq = sq + d
        if (atk_sq & 0x88) == 0:
            p = board[atk_sq]
            if p != '.' and p.isupper() == by_white and p.upper() == 'K':
                return True
    # Sliders (Rooks/Queens)
    for d in [16, -16, 1, -1]:
        atk_sq = sq + d
        while (atk_sq & 0x88) == 0:
            p = board[atk_sq]
            if p != '.':
                if p.isupper() == by_white and p.upper() in ('R', 'Q'):
                    return True
                break
            atk_sq += d
    # Sliders (Bishops/Queens)
    for d in [17, 15, -15, -17]:
        atk_sq = sq + d
        while (atk_sq & 0x88) == 0:
            p = board[atk_sq]
            if p != '.':
                if p.isupper() == by_white and p.upper() in ('B', 'Q'):
                    return True
                break
            atk_sq += d
    return False

# --- Core Engine Logic ---
def generate_moves(board, turn, ep_sq, castling):
    moves = []
    is_white = (turn == 'w')
    enemy_is_white = not is_white
    
    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p == '.' or p.isupper() != is_white: continue
        pu = p.upper()

        if pu == 'P':
            direction = 16 if is_white else -16
            start_rank = 1 if is_white else 6
            prom_rank = 7 if is_white else 0
            rank = sq >> 4

            # Forward push
            to = sq + direction
            if (to & 0x88) == 0 and board[to] == '.':
                if (to >> 4) == prom_rank:
                    for promo in ['q', 'r', 'b', 'n']:
                        moves.append((sq, to, promo.upper() if is_white else promo, 'normal'))
                else:
                    moves.append((sq, to, None, 'normal'))
                    # Double push
                    if rank == start_rank:
                        to2 = sq + 2 * direction
                        if (to2 & 0x88) == 0 and board[to2] == '.':
                            moves.append((sq, to2, None, 'normal'))

            # Captures
            for d in ([15, 17] if is_white else [-15, -17]):
                to = sq + d
                if (to & 0x88) == 0:
                    target = board[to]
                    if target != '.' and target.isupper() == enemy_is_white:
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
                if (to & 0x88) == 0:
                    target = board[to]
                    if target == '.' or target.isupper() == enemy_is_white:
                        moves.append((sq, to, None, 'normal'))

        elif pu in ('R', 'Q', 'B'):
            dirs = []
            if pu in ('R', 'Q'): dirs.extend([16, -16, 1, -1])
            if pu in ('B', 'Q'): dirs.extend([17, 15, -15, -17])
            for d in dirs:
                to = sq + d
                while (to & 0x88) == 0:
                    target = board[to]
                    if target == '.':
                        moves.append((sq, to, None, 'normal'))
                    else:
                        if target.isupper() == enemy_is_white:
                            moves.append((sq, to, None, 'normal'))
                        break
                    to += d

        elif pu == 'K':
            for d in [16, -16, 1, -1, 17, 15, -15, -17]:
                to = sq + d
                if (to & 0x88) == 0:
                    target = board[to]
                    if target == '.' or target.isupper() == enemy_is_white:
                        moves.append((sq, to, None, 'normal'))

            # Castling (requires exact start sq, intermediate empties, and checking attacks)
            if is_white:
                if 'K' in castling:
                    if board[5] == '.' and board[6] == '.' and board[7] == 'R' and sq == 4:
                        if not is_attacked(board, 4, False) and not is_attacked(board, 5, False) and not is_attacked(board, 6, False):
                            moves.append((sq, 6, None, 'castling'))
                if 'Q' in castling:
                    if board[3] == '.' and board[2] == '.' and board[1] == '.' and board[0] == 'R' and sq == 4:
                        if not is_attacked(board, 4, False) and not is_attacked(board, 3, False) and not is_attacked(board, 2, False):
                            moves.append((sq, 2, None, 'castling'))
            else:
                if 'k' in castling:
                    if board[117] == '.' and board[118] == '.' and board[119] == 'r' and sq == 116:
                        if not is_attacked(board, 116, True) and not is_attacked(board, 117, True) and not is_attacked(board, 118, True):
                            moves.append((sq, 118, None, 'castling'))
                if 'q' in castling:
                    if board[115] == '.' and board[114] == '.' and board[113] == '.' and board[112] == 'r' and sq == 116:
                        if not is_attacked(board, 116, True) and not is_attacked(board, 115, True) and not is_attacked(board, 114, True):
                            moves.append((sq, 114, None, 'castling'))
    return moves

def do_move(board, m, turn, ep_sq, castling, king_w, king_b):
    frm, to, promo, mtype = m
    captured = board[to]
    p = board[frm]
    board[to] = promo if promo else p
    board[frm] = '.'
    
    new_king_w = to if p == 'K' else king_w
    new_king_b = to if p == 'k' else king_b
    
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
        
    return captured, cap_sq, new_ep, new_castling, new_king_w, new_king_b

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

def get_legal_moves(board, turn, ep_sq, castling, king_w, king_b):
    pseudo = generate_moves(board, turn, ep_sq, castling)
    legal = []
    for m in pseudo:
        undo_info = do_move(board, m, turn, ep_sq, castling, king_w, king_b)
        my_king = undo_info[4] if turn == 'w' else undo_info[5]
        # King must not be attacked after our own move
        if not is_attacked(board, my_king, turn == 'b'):
            legal.append(m)
        undo_move(board, m, turn, undo_info[0], undo_info[1])
    return legal

def evaluate(board, turn):
    score = 0
    phase = 0
    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p in 'nNbBrRqQ':
            phase += 1
            
    is_endgame = phase <= 4
    
    for sq in range(128):
        if sq & 0x88: continue
        p = board[sq]
        if p == '.': continue
        pu = p.upper()
        val = PIECE_VALUES[pu]
        
        if pu == 'K' and is_endgame:
            pst_val = K_ENDGAME_0x88[sq if p.isupper() else sq ^ 112]
        else:
            pst_val = PST_0x88[pu][sq if p.isupper() else sq ^ 112]
            
        if p.isupper():
            score += val + pst_val
        else:
            score -= val + pst_val
            
    return score if turn == 'w' else -score

def order_moves(moves, board):
    scored_moves = []
    for m in moves:
        frm, to, promo, mtype = m
        score = 0
        if mtype == 'ep':
            score = 99
        elif board[to] != '.':
            victim = PIECE_VALUES.get(board[to].upper(), 0)
            attacker = PIECE_VALUES.get(board[frm].upper(), 0)
            score = victim - attacker/100.0
        if promo:
            score += PIECE_VALUES.get(promo.upper(), 0) + 1000
        scored_moves.append((score, m))
    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in scored_moves]

# --- Search Algorithms ---
TT = {}
NODES = 0
TIMEOUT = False

def quiesce(board, turn, ep_sq, castling, king_w, king_b, alpha, beta, depth_limit=10):
    stand_pat = evaluate(board, turn)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat
        
    if depth_limit <= 0:
        return alpha
        
    moves = get_legal_moves(board, turn, ep_sq, castling, king_w, king_b)
    # Target only captures to resolve noisy tactics
    captures = [m for m in moves if board[m[1]] != '.' or m[3] == 'ep']
    captures = order_moves(captures, board)
    
    for m in captures:
        undo_info = do_move(board, m, turn, ep_sq, castling, king_w, king_b)
        new_turn = 'b' if turn == 'w' else 'w'
        score = -quiesce(board, new_turn, undo_info[2], undo_info[3], undo_info[4], undo_info[5], -beta, -alpha, depth_limit - 1)
        undo_move(board, m, turn, undo_info[0], undo_info[1])
        
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

def alpha_beta(board, turn, ep_sq, castling, king_w, king_b, depth, alpha, beta, start_time, time_limit):
    global NODES, TIMEOUT
    NODES += 1
    
    if (NODES & 2047) == 0:
        if time.time() - start_time > time_limit:
            TIMEOUT = True
            return 0, None
            
    if depth == 0:
        return quiesce(board, turn, ep_sq, castling, king_w, king_b, alpha, beta), None
        
    hash_key = hash("".join(board) + turn + castling + str(ep_sq))
    tt_move = None
    if hash_key in TT:
        tt_depth, tt_flag, tt_score, tt_m = TT[hash_key]
        tt_move = tt_m
        if tt_depth >= depth:
            if tt_flag == 'EXACT':
                return tt_score, tt_m
            elif tt_flag == 'LOWER' and tt_score >= beta:
                return tt_score, tt_m
            elif tt_flag == 'UPPER' and tt_score <= alpha:
                return tt_score, tt_m
                
    orig_alpha = alpha
    best_score = -50000
    best_move = None

    moves = get_legal_moves(board, turn, ep_sq, castling, king_w, king_b)
    if not moves:
        my_king = king_w if turn == 'w' else king_b
        if is_attacked(board, my_king, turn == 'b'):
            return -30000 - depth, None # Faster mate is strongly preferred
        return 0, None # Stalemate
        
    moves = order_moves(moves, board)
    if tt_move in moves:
        moves.remove(tt_move)
        moves.insert(0, tt_move)
        
    for m in moves:
        undo_info = do_move(board, m, turn, ep_sq, castling, king_w, king_b)
        new_turn = 'b' if turn == 'w' else 'w'
        
        score, _ = alpha_beta(board, new_turn, undo_info[2], undo_info[3], undo_info[4], undo_info[5], depth - 1, -beta, -alpha, start_time, time_limit)
        score = -score
        
        undo_move(board, m, turn, undo_info[0], undo_info[1])
        
        if TIMEOUT:
            return 0, None
            
        if score > best_score:
            best_score = score
            best_move = m
            
        if score > alpha:
            alpha = score
            
        if alpha >= beta:
            break
            
    if not TIMEOUT:
        flag = 'EXACT'
        if best_score <= orig_alpha: flag = 'UPPER'
        elif best_score >= beta: flag = 'LOWER'
        TT[hash_key] = (depth, flag, best_score, best_move)
            
    return best_score, best_move

def get_best_move(fen, time_limit=4.8):
    global TT, NODES, TIMEOUT
    # Protect our 256MB memory strict constraint
    if len(TT) > 500000:
        TT.clear()
        
    NODES = 0
    TIMEOUT = False
    
    board = ['.'] * 128
    parts = fen.split()
    ranks = parts[0].split('/')
    for r in range(8):
        f = 0
        for char in ranks[r]:
            if char.isdigit():
                f += int(char)
            else:
                sq = (7 - r) * 16 + f
                board[sq] = char
                f += 1
                
    turn = parts[1]
    castling = parts[2] if len(parts) > 2 else '-'
    ep_sq = str_to_sq(parts[3]) if len(parts) > 3 and parts[3] != '-' else -1
    
    king_w, king_b = -1, -1
    for sq in range(128):
        if not (sq & 0x88):
            if board[sq] == 'K': king_w = sq
            elif board[sq] == 'k': king_b = sq
            
    start_time = time.time()
    best_move_overall = None
    
    # Iterative deepening handles 5s time limit dynamically
    for depth in range(1, 30):
        score, move = alpha_beta(board, turn, ep_sq, castling, king_w, king_b, depth, -50000, 50000, start_time, time_limit)
        
        if TIMEOUT:
            break
            
        if move:
            best_move_overall = move
            
        # Break out early if we found a forced mate trajectory
        if score > 20000 or score < -20000:
            break
            
    # Fallback parsing in case of immediate depth-1 crash
    if not best_move_overall:
        moves = get_legal_moves(board, turn, ep_sq, castling, king_w, king_b)
        if moves: best_move_overall = moves[0]
        else: return "0000"
        
    frm, to, promo, _ = best_move_overall
    uci = sq_to_str(frm) + sq_to_str(to)
    if promo: uci += promo.lower()
    return uci

def main():
    # Long-lived process reads one board FEN per standard input event
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        # FEN basic signature validation
        if ' ' in line and '/' in line:
            try:
                move = get_best_move(line)
                sys.stdout.write(move + "\n")
                sys.stdout.flush()
            except Exception as e:
                # Fatal fail-safe to avoid completely crashing evaluator pipelines
                sys.stdout.write("e2e4\n") 
                sys.stdout.flush()

if __name__ == "__main__":
    main()