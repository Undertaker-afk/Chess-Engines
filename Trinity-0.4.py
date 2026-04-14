# Titan
import sys
import time
import random

# ==============================================================================
# TITAN CHESS ENGINE - REFINED ARCHITECTURE
# ==============================================================================

# Global Constants
EMPTY, PIECES = 0, " PNBRQKpnbrqk"
W_PAWN, W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN, W_KING = 1, 2, 3, 4, 5, 6
B_PAWN, B_KNIGHT, B_BISHOP, B_ROOK, B_QUEEN, B_KING = 7, 8, 9, 10, 11, 12

# 0x88 board representation helper
# Ranks 0-7, Files 0-7. 0x88 check: (sq & 0x88) != 0
SQ_A1, SQ_H1, SQ_A8, SQ_H8 = 0, 7, 112, 119

# ==============================================================================
# HIGH-DENSITY EVALUATION TABLES (PeSTO Inspired)
# Values represent (Middlegame, Endgame) tuples to allow tapered evaluation.
# ==============================================================================

# Material Values
MG_VAL = [0, 82, 337, 365, 477, 1025,  0, 82, 337, 365, 477, 1025, 0]
EG_VAL = [0, 94, 281, 297, 512,  936,  0, 94, 281, 297, 512,  936, 0]

# Piece-Square Tables (0x88 format)
# We store 128 integers per piece type to avoid index transformation during search.
PST_MG = [[0] * 128 for _ in range(13)]
PST_EG = [[0] * 128 for _ in range(13)]

# Raw 8x8 tables to be expanded
RAW_PST = {
    W_PAWN: [
        [ 0,   0,   0,   0,   0,   0,   0,   0],
        [98, 134,  61,  95,  68, 126,  34, -11],
        [-6,   7,  26,  31,  65,  56,  25, -20],
        [-14,  13,   6,  21,  23,  12,  17, -23],
        [-27,  -2,  -5,  12,  17,   6,  10, -25],
        [-26,  -4,  -4, -10,   3,   3,  33, -12],
        [-35,  -1, -20, -23, -15,  24,  38, -22],
        [ 0,   0,   0,   0,   0,   0,   0,   0]
    ],
    W_KNIGHT: [
        [-167, -89, -34, -49,  61, -97, -15, -107],
        [-73, -41,  72,  36,  23,  62,   7,  -17],
        [-47,  60,  37,  65,  84, 129,  73,   44],
        [ -9,  17,  19,  53,  37,  69,  18,   22],
        [-13,   4,  16,  13,  28,  19,  21,   -8],
        [-23,  -9,  12,  10,  19,  17,  25,  -16],
        [-29, -53, -12,  -3,  -1,  18, -14,  -19],
        [-105, -21, -58, -33, -17, -28, -19,  -23]
    ],
    W_BISHOP: [
        [-29,   4, -82, -37, -25, -42,   7,  -8],
        [-26,  16, -18, -13,  30,  59,  18, -47],
        [-16,  37,  43,  40,  35,  50,  37,  -2],
        [ -4,   5,  19,  50,  37,  37,   7,  -2],
        [ -6,  13,  13,  26,  34,  12,  10,   4],
        [  0,  15,  15,  15,  14,  27,  18,  10],
        [  4,  15,  16,   0,   7,  21,  33,   1],
        [-33,  -3, -14, -21, -13, -12, -39, -21]
    ],
    W_ROOK: [
        [ 32,  42,  32,  51,  63,   9,  31,  43],
        [ 27,  32,  58,  62,  80,  67,  26,  44],
        [ -5,  19,  26,  36,  17,  45,  61,  16],
        [-24, -11,   7,  26,  24,  35,  -8, -20],
        [-36, -26, -12,  -1,   9,  -7,   6, -23],
        [-45, -25, -16, -17,   3,   0,  -5, -33],
        [-44, -16, -20,  -9,  -1,  11,  -6, -71],
        [-19, -13,   1,  17,  16,   7, -37, -26]
    ],
    W_QUEEN: [
        [-28,   0,  29,  12,  59,  44,  43,  45],
        [-24, -39,  -5,   1, -16,  57,  28,  54],
        [-13, -17,   7,   8,  29,  56,  47,  57],
        [-27, -27, -16, -16,  -1,  17,  -2,   1],
        [ -9, -26,  -9, -10,  -2,  -4,   3,  -3],
        [-14,   2, -11,  -2,  -5,   2,  14,   5],
        [-35,  -8,  11,   2,   8,  15,  -3,   1],
        [ -1, -18,  -9,  10, -15, -25, -31, -50]
    ],
    W_KING: [
        [-65,  23,  16, -15, -56, -34,   2,  13],
        [ 29,  -1, -20,  -7,  -8,  -4, -38, -29],
        [ -9,  24,   2, -16, -20,   6,  22, -22],
        [-17, -20, -12, -27, -30, -25, -14, -36],
        [-49,  -1, -27, -39, -46, -44, -33, -51],
        [-14, -14, -22, -46, -44, -30, -15, -27],
        [  1,   7,  -8, -64, -43, -16,   9,   8],
        [-15,  36,  12, -54,   8, -28,  24,  14]
    ]
}

# Endgame tables often differ wildly (Kings become attackers)
RAW_PST_EG = {
    W_PAWN: [
        [ 0,   0,   0,   0,   0,   0,   0,   0],
        [178, 173, 158, 134, 147, 132, 165, 187],
        [94, 100,  85,  67,  56,  53,  82,  84],
        [32,  24,  13,   5,  -2,   4,  17,  17],
        [13,   9,  -3,  -7,  -7,  -8,   3,  -1],
        [ 4,   7,  -6,   1,   0,  -5,  -1,  -8],
        [13,   8,   8,  10,  13,   0,   2,  -7],
        [ 0,   0,   0,   0,   0,   0,   0,   0]
    ],
    W_KNIGHT: [
        [-58, -38, -13, -28, -31, -27, -63, -99],
        [-25,  -8, -25,  -2,  -9, -25, -24, -52],
        [-24, -20,  10,   9,  -1,  -9, -19, -41],
        [-17,   3,  22,  22,  22,  11,   8, -18],
        [-18,  -6,  16,  25,  16,  17,   4, -18],
        [-23,  -3,  -1,  15,  10,  -3, -20, -22],
        [-42, -20, -10,  -5,  -2, -20, -23, -44],
        [-29, -51, -23, -38, -22, -27, -38, -46]
    ],
    W_BISHOP: [
        [-23,  -9, -23,  -5,  -9, -16,  -5, -17],
        [-14, -18,  -7,  -1,   4,  -9, -15, -27],
        [-12,  -3,   8,  10,  13,   3,  -7, -15],
        [ -6,   3,  13,  19,   7,  10,  -3,  -9],
        [ -3,   9,  12,   9,  14,  10,   3,   2],
        [  2,  -8,   0,  -1,  -2,   6,   0,   4],
        [ -8,  -4,   7, -12,  -3, -13,  -4, -14],
        [-14, -21, -11,  -8,  -7,  -9, -17, -24]
    ],
    W_ROOK: [
        [ 13,  10,  18,  15,  12,  12,   8,   5],
        [ 11,  13,  13,  11,  -3,   3,   8,   3],
        [  7,   7,   7,   5,   4,  -3,  -5,  -3],
        [  4,   3,  13,   1,   2,   1,  -1,   2],
        [  3,   5,   8,   4,  -5,  -6,  -8, -11],
        [ -4,   0,  -5,  -1,  -7, -12,  -8, -16],
        [ -6,  -6,   0,   2,  -9,  -9, -11,  -3],
        [ -9,   2,   3,  -1,  -5, -13,   4, -20]
    ],
    W_QUEEN: [
        [ -9,  22,  22,  27,  27,  19,  10,  20],
        [-17,  20,  32,  41,  58,  25,  30,   0],
        [-20,   6,   9,  49,  47,  35,  19,   9],
        [  3,  22,  24,  45,  57,  40,  57,  36],
        [-18,  28,  19,  47,  31,  34,  12,  11],
        [ 16,  20,  22,  51,  25,  15,  14,  13],
        [-22,  33,   3,  22,  24,   1,  14,  -8],
        [-16, -27,  28, -14,  -2,  -5,  11, -21]
    ],
    W_KING: [
        [-74, -35, -18, -18, -11,  15,   4, -17],
        [-12,  17,  14,  17,  17,  38,  23,  11],
        [ 10,  17,  23,  15,  20,  45,  44,  13],
        [ -8,  22,  24,  27,  26,  33,  26,   3],
        [-18,  -4,  21,  24,  27,  23,   9, -11],
        [-19,  -3,  11,  21,  23,  16,   7,  -9],
        [-27, -11,   4,  13,  14,   4,  -5, -17],
        [-53, -34, -21, -11, -28, -14, -24, -43]
    ]
}

def init_tables():
    for p, table in RAW_PST.items():
        eg_table = RAW_PST_EG[p]
        for r in range(8):
            for f in range(8):
                sq = (7-r) * 16 + f
                PST_MG[p][sq] = table[r][f]
                PST_EG[p][sq] = eg_table[r][f]
                # Mirror for Black
                sq_b = r * 16 + f
                PST_MG[p+6][sq_b] = -table[r][f]
                PST_EG[p+6][sq_b] = -eg_table[r][f]

init_tables()

# ==============================================================================
# ZOBRIST HASHING (State persistence)
# ==============================================================================
ZOBRIST_PIECE = [[random.getrandbits(64) for _ in range(128)] for _ in range(13)]
ZOBRIST_SIDE = random.getrandbits(64)
ZOBRIST_CASTLE = [random.getrandbits(64) for _ in range(16)]
ZOBRIST_EP = [random.getrandbits(64) for _ in range(128)]

def compute_hash(board, side, castle, ep):
    h = 0
    for i in range(128):
        if not (i & 0x88) and board[i] != EMPTY:
            h ^= ZOBRIST_PIECE[board[i]][i]
    if side == 'b': h ^= ZOBRIST_SIDE
    h ^= ZOBRIST_CASTLE[castle]
    if ep != -1: h ^= ZOBRIST_EP[ep]
    return h

# ==============================================================================
# TRANSPOSITION TABLE & SEARCH CACHE
# ==============================================================================
TT = {} # {hash: (depth, flag, value, best_move)}
TT_EXACT, TT_ALPHA, TT_BETA = 0, 1, 2

# Move ordering heuristics
HISTORY = [[0] * 128 for _ in range(128)]
KILLERS = [[None, None] for _ in range(128)]

# ==============================================================================
# ENGINE LOGIC
# ==============================================================================

class TitanEngine:
    def __init__(self, fen):
        self.board = [EMPTY] * 128
        self.parse_fen(fen)
        self.nodes = 0
        self.start_time = time.time()
        self.time_limit = 4.85
        self.abort = False

    def parse_fen(self, fen):
        parts = fen.split()
        r, f = 7, 0
        for char in parts[0]:
            if char == '/': r, f = r - 1, 0
            elif char.isdigit(): f += int(char)
            else:
                p_idx = PIECES.find(char)
                self.board[r * 16 + f] = p_idx
                f += 1
        self.side = parts[1]
        self.castle = 0
        if 'K' in parts[2]: self.castle |= 1
        if 'Q' in parts[2]: self.castle |= 2
        if 'k' in parts[2]: self.castle |= 4
        if 'q' in parts[2]: self.castle |= 8
        self.ep = -1 if parts[3] == '-' else (int(parts[3][1])-1)*16 + (ord(parts[3][0])-97)
        self.hash = compute_hash(self.board, self.side, self.castle, self.ep)

    def is_attacked(self, sq, side):
        # Pawn attacks
        if side == 'w':
            if not ((sq-17) & 0x88) and self.board[sq-17] == W_PAWN: return True
            if not ((sq-15) & 0x88) and self.board[sq-15] == W_PAWN: return True
        else:
            if not ((sq+17) & 0x88) and self.board[sq+17] == B_PAWN: return True
            if not ((sq+15) & 0x88) and self.board[sq+15] == B_PAWN: return True
        
        # Knight attacks
        for d in [-33, -31, -18, -14, 14, 18, 31, 33]:
            n_sq = sq + d
            if not (n_sq & 0x88) and self.board[n_sq] == (W_KNIGHT if side == 'w' else B_KNIGHT):
                return True
        
        # Slider attacks (Rook, Bishop, Queen)
        dirs = [(-16, 'RQ'), (16, 'RQ'), (-1, 'RQ'), (1, 'RQ'), 
                (-17, 'BQ'), (17, 'BQ'), (-15, 'BQ'), (15, 'BQ')]
        for d, types in dirs:
            c_sq = sq + d
            while not (c_sq & 0x88):
                p = self.board[c_sq]
                if p != EMPTY:
                    p_char = PIECES[p].upper()
                    if p_char in types and (p <= 6 if side == 'w' else p > 6):
                        return True
                    break
                c_sq += d
        
        # King attacks
        for d in [-17, -16, -15, -1, 1, 15, 16, 17]:
            k_sq = sq + d
            if not (k_sq & 0x88) and self.board[k_sq] == (W_KING if side == 'w' else B_KING):
                return True
        return False

    def get_moves(self, captures_only=False):
        moves = []
        is_w = self.side == 'w'
        for sq in range(128):
            if sq & 0x88: continue
            p = self.board[sq]
            if p == EMPTY or (p <= 6) != is_w: continue
            
            p_type = p if is_w else p - 6
            # Pawn
            if p_type == W_PAWN:
                fwd = 16 if is_w else -16
                # Push
                n_sq = sq + fwd
                if not (n_sq & 0x88) and self.board[n_sq] == EMPTY and not captures_only:
                    if (n_sq >> 4) in [0, 7]: # Promotion
                        for pr in [W_QUEEN, W_ROOK, W_BISHOP, W_KNIGHT] if is_w else [B_QUEEN, B_ROOK, B_BISHOP, B_KNIGHT]:
                            moves.append((sq, n_sq, pr))
                    else:
                        moves.append((sq, n_sq, 0))
                        # Double push
                        if (sq >> 4) == (1 if is_w else 6):
                            nn_sq = n_sq + fwd
                            if self.board[nn_sq] == EMPTY:
                                moves.append((sq, nn_sq, 0))
                # Captures
                for d in [fwd-1, fwd+1]:
                    c_sq = sq + d
                    if not (c_sq & 0x88):
                        if self.board[c_sq] != EMPTY and (self.board[c_sq] <= 6) != is_w:
                            if (c_sq >> 4) in [0, 7]:
                                for pr in [W_QUEEN, W_ROOK, W_BISHOP, W_KNIGHT] if is_w else [B_QUEEN, B_ROOK, B_BISHOP, B_KNIGHT]:
                                    moves.append((sq, c_sq, pr))
                            else: moves.append((sq, c_sq, 0))
                        elif c_sq == self.ep:
                            moves.append((sq, c_sq, 0))
            
            # Knight / King
            elif p_type in [W_KNIGHT, W_KING]:
                diffs = [-33, -31, -18, -14, 14, 18, 31, 33] if p_type == W_KNIGHT else [-17, -16, -15, -1, 1, 15, 16, 17]
                for d in diffs:
                    n_sq = sq + d
                    if not (n_sq & 0x88):
                        dest = self.board[n_sq]
                        if dest == EMPTY:
                            if not captures_only: moves.append((sq, n_sq, 0))
                        elif (dest <= 6) != is_w:
                            moves.append((sq, n_sq, 0))
                # Castling
                if p_type == W_KING and not captures_only:
                    if is_w:
                        if (self.castle & 1) and self.board[SQ_A1+5]==EMPTY and self.board[SQ_A1+6]==EMPTY and not self.is_attacked(SQ_A1+4, 'b') and not self.is_attacked(SQ_A1+5, 'b'):
                            moves.append((SQ_A1+4, SQ_A1+6, 0))
                        if (self.castle & 2) and self.board[SQ_A1+1]==EMPTY and self.board[SQ_A1+2]==EMPTY and self.board[SQ_A1+3]==EMPTY and not self.is_attacked(SQ_A1+4, 'b') and not self.is_attacked(SQ_A1+3, 'b'):
                            moves.append((SQ_A1+4, SQ_A1+2, 0))
                    else:
                        if (self.castle & 4) and self.board[SQ_A8+5]==EMPTY and self.board[SQ_A8+6]==EMPTY and not self.is_attacked(SQ_A8+4, 'w') and not self.is_attacked(SQ_A8+5, 'w'):
                            moves.append((SQ_A8+4, SQ_A8+6, 0))
                        if (self.castle & 8) and self.board[SQ_A8+1]==EMPTY and self.board[SQ_A8+2]==EMPTY and self.board[SQ_A8+3]==EMPTY and not self.is_attacked(SQ_A8+4, 'w') and not self.is_attacked(SQ_A8+3, 'w'):
                            moves.append((SQ_A8+4, SQ_A8+2, 0))

            # Sliders
            elif p_type in [W_BISHOP, W_ROOK, W_QUEEN]:
                dirs = []
                if p_type in [W_BISHOP, W_QUEEN]: dirs += [-17, -15, 15, 17]
                if p_type in [W_ROOK, W_QUEEN]: dirs += [-16, -1, 1, 16]
                for d in dirs:
                    n_sq = sq + d
                    while not (n_sq & 0x88):
                        dest = self.board[n_sq]
                        if dest == EMPTY:
                            if not captures_only: moves.append((sq, n_sq, 0))
                        else:
                            if (dest <= 6) != is_w: moves.append((sq, n_sq, 0))
                            break
                        n_sq += d
        return moves

    def make_move(self, move):
        f, t, prom = move
        p = self.board[f]
        cap = self.board[t]
        
        # State Backup
        undo = (self.hash, self.castle, self.ep, cap)
        
        # Update Hash for pieces moving
        self.hash ^= ZOBRIST_PIECE[p][f]
        if cap != EMPTY:
            self.hash ^= ZOBRIST_PIECE[cap][t]
            # Handle En Passant Capture
            if (p == W_PAWN or p == B_PAWN) and t == self.ep:
                ep_cap_sq = t - (16 if p == W_PAWN else -16)
                self.hash ^= ZOBRIST_PIECE[self.board[ep_cap_sq]][ep_cap_sq]
                self.board[ep_cap_sq] = EMPTY
        
        # Move Piece
        self.board[f] = EMPTY
        if prom:
            self.board[t] = prom
            self.hash ^= ZOBRIST_PIECE[prom][t]
        else:
            self.board[t] = p
            self.hash ^= ZOBRIST_PIECE[p][t]

        # Castling Rooks
        if p == W_KING:
            if f == 4:
                if t == 6: self.board[7]=EMPTY; self.board[5]=W_ROOK; self.hash^=ZOBRIST_PIECE[W_ROOK][7]^ZOBRIST_PIECE[W_ROOK][5]
                elif t == 2: self.board[0]=EMPTY; self.board[3]=W_ROOK; self.hash^=ZOBRIST_PIECE[W_ROOK][0]^ZOBRIST_PIECE[W_ROOK][3]
            self.castle &= ~3
        elif p == B_KING:
            if f == 116:
                if t == 118: self.board[119]=EMPTY; self.board[117]=B_ROOK; self.hash^=ZOBRIST_PIECE[B_ROOK][119]^ZOBRIST_PIECE[B_ROOK][117]
                elif t == 114: self.board[112]=EMPTY; self.board[115]=B_ROOK; self.hash^=ZOBRIST_PIECE[B_ROOK][112]^ZOBRIST_PIECE[B_ROOK][115]
            self.castle &= ~12
        
        # Update Castling Rights
        old_castle = self.castle
        if f == 0 or t == 0: self.castle &= ~2
        if f == 7 or t == 7: self.castle &= ~1
        if f == 112 or t == 112: self.castle &= ~8
        if f == 119 or t == 119: self.castle &= ~4
        self.hash ^= ZOBRIST_CASTLE[old_castle] ^ ZOBRIST_CASTLE[self.castle]

        # EP Square update
        if self.ep != -1: self.hash ^= ZOBRIST_EP[self.ep]
        if (p == W_PAWN or p == B_PAWN) and abs(f-t) == 32:
            self.ep = (f+t)//2
            self.hash ^= ZOBRIST_EP[self.ep]
        else:
            self.ep = -1
            
        self.side = 'b' if self.side == 'w' else 'w'
        self.hash ^= ZOBRIST_SIDE
        return undo

    def undo_move(self, move, undo):
        f, t, prom = move
        h, cas, ep, cap = undo
        self.side = 'b' if self.side == 'w' else 'w'
        
        # Simple board restoration
        p = self.board[t]
        if prom: p = W_PAWN if self.side == 'w' else B_PAWN
        
        self.board[f] = p
        self.board[t] = cap
        
        if (p == W_PAWN or p == B_PAWN) and t == ep:
            ep_cap_sq = t - (16 if p == W_PAWN else -16)
            self.board[ep_cap_sq] = B_PAWN if self.side == 'w' else W_PAWN
        
        # King move rroks
        if p == W_KING and f == 4:
            if t == 6: self.board[5]=EMPTY; self.board[7]=W_ROOK
            elif t == 2: self.board[3]=EMPTY; self.board[0]=W_ROOK
        elif p == B_KING and f == 116:
            if t == 118: self.board[117]=EMPTY; self.board[119]=B_ROOK
            elif t == 114: self.board[115]=EMPTY; self.board[112]=B_ROOK
            
        self.hash, self.castle, self.ep = h, cas, ep

    def evaluate(self):
        mg, eg = 0, 0
        game_phase = 0
        for sq in range(128):
            if sq & 0x88: continue
            p = self.board[sq]
            if p == EMPTY: continue
            
            p_type = p if p <= 6 else p - 6
            # Phase calculation
            if p_type == W_KNIGHT: game_phase += 1
            elif p_type == W_BISHOP: game_phase += 1
            elif p_type == W_ROOK: game_phase += 2
            elif p_type == W_QUEEN: game_phase += 4
            
            # Tapered Values
            if p <= 6:
                mg += MG_VAL[p] + PST_MG[p][sq]
                eg += EG_VAL[p] + PST_EG[p][sq]
            else:
                mg -= MG_VAL[p-6] + abs(PST_MG[p][sq])
                eg -= EG_VAL[p-6] + abs(PST_EG[p][sq])
        
        # Clamp phase
        game_phase = min(game_phase, 24)
        score = (mg * game_phase + eg * (24 - game_phase)) // 24
        return score if self.side == 'w' else -score

    def score_move(self, move, tt_move, ply):
        f, t, prom = move
        if move == tt_move: return 1000000
        
        score = 0
        cap = self.board[t]
        if cap != EMPTY:
            # MVV-LVA
            score = 100000 + (MG_VAL[cap if cap<=6 else cap-6] * 10) - MG_VAL[self.board[f] if self.board[f]<=6 else self.board[f]-6]
        else:
            if KILLERS[ply][0] == move: return 90000
            if KILLERS[ply][1] == move: return 80000
            score = HISTORY[f][t]
        
        if prom: score += 50000
        return score

    def quiescence(self, alpha, beta):
        self.nodes += 1
        stand_pat = self.evaluate()
        if stand_pat >= beta: return beta
        if alpha < stand_pat: alpha = stand_pat
        
        moves = self.get_moves(captures_only=True)
        moves.sort(key=lambda m: self.score_move(m, None, 0), reverse=True)
        
        for m in moves:
            undo = self.make_move(m)
            # Check legality
            k_sq = -1
            is_w = self.side == 'b' # because side flipped
            for i in range(128):
                if not (i & 0x88) and self.board[i] == (W_KING if is_w else B_KING):
                    k_sq = i; break
            if self.is_attacked(k_sq, 'b' if is_w else 'w'):
                self.undo_move(m, undo)
                continue
                
            score = -self.quiescence(-beta, -alpha)
            self.undo_move(m, undo)
            if score >= beta: return beta
            if score > alpha: alpha = score
        return alpha

    def negamax(self, depth, alpha, beta, ply):
        if (self.nodes & 1023) == 0:
            if time.time() - self.start_time > self.time_limit:
                self.abort = True
        if self.abort: return 0

        # TT Lookup
        tt_entry = TT.get(self.hash)
        tt_move = None
        if tt_entry and tt_entry[0] >= depth:
            flag, val = tt_entry[1], tt_entry[2]
            if flag == TT_EXACT: return val
            if flag == TT_ALPHA and val <= alpha: return val
            if flag == TT_BETA and val >= beta: return val
            tt_move = tt_entry[3]

        if depth == 0:
            return self.quiescence(alpha, beta)

        moves = self.get_moves()
        if not moves:
            # Checkmate or Draw
            k_sq = -1
            is_w = self.side == 'w'
            for i in range(128):
                if not (i & 0x88) and self.board[i] == (W_KING if is_w else B_KING):
                    k_sq = i; break
            if self.is_attacked(k_sq, 'b' if is_w else 'w'): return -30000 + ply
            return 0

        moves.sort(key=lambda m: self.score_move(m, tt_move, ply), reverse=True)
        
        best_val = -100000
        best_move = None
        orig_alpha = alpha
        
        legal_move_count = 0
        for m in moves:
            undo = self.make_move(m)
            # Legality
            k_sq = -1
            is_w = self.side == 'b'
            for i in range(128):
                if not (i & 0x88) and self.board[i] == (W_KING if is_w else B_KING):
                    k_sq = i; break
            if self.is_attacked(k_sq, 'b' if is_w else 'w'):
                self.undo_move(m, undo)
                continue
            
            legal_move_count += 1
            val = -self.negamax(depth - 1, -beta, -alpha, ply + 1)
            self.undo_move(m, undo)
            
            if val > best_val:
                best_val = val
                best_move = m
            
            if val > alpha:
                alpha = val
                if alpha >= beta:
                    # Beta cutoff
                    if self.board[m[1]] == EMPTY:
                        HISTORY[m[0]][m[1]] += depth * depth
                        KILLERS[ply][1] = KILLERS[ply][0]
                        KILLERS[ply][0] = m
                    break
        
        if legal_move_count == 0:
            k_sq = -1
            is_w = self.side == 'w'
            for i in range(128):
                if not (i & 0x88) and self.board[i] == (W_KING if is_w else B_KING):
                    k_sq = i; break
            if self.is_attacked(k_sq, 'b' if is_w else 'w'): return -30000 + ply
            return 0

        # TT Store
        flag = TT_EXACT
        if best_val <= orig_alpha: flag = TT_ALPHA
        elif best_val >= beta: flag = TT_BETA
        TT[self.hash] = (depth, flag, best_val, best_move)
        
        return best_val

    def get_best_move(self):
        best_m = None
        # Clear move specific heuristics
        global HISTORY, KILLERS
        HISTORY = [[0] * 128 for _ in range(128)]
        KILLERS = [[None, None] for _ in range(128)]
        
        for depth in range(1, 15):
            val = self.negamax(depth, -100000, 100000, 0)
            if self.abort: break
            
            entry = TT.get(self.hash)
            if entry: best_m = entry[3]
            
            # Print search info if needed
            # print(f"depth {depth} score cp {val} nodes {self.nodes}")
            if val > 20000 or val < -20000: break
            
        if best_m:
            f, t, prom = best_m
            move_str = f"{chr(97+(f&7))}{ (f>>4)+1 }{chr(97+(t&7))}{ (t>>4)+1 }"
            if prom: move_str += PIECES[prom].lower()
            return move_str
        return "0000"

# ==============================================================================
# ENTRY POINT
# ==============================================================================
def main():
    for line in sys.stdin:
        fen = line.strip()
        if not fen: continue
        engine = TitanEngine(fen)
        print(engine.get_best_move())
        sys.stdout.flush()

if __name__ == "__main__":
    main()