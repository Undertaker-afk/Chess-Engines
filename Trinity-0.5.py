import sys
import time
import random

# ==============================================================================
# TRINITY ULTIMATE - ADVANCED CHESS ENGINE
# ==============================================================================

# Global Constants
EMPTY, PIECES = 0, " PNBRQKpnbrqk"
W_PAWN, W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN, W_KING = 1, 2, 3, 4, 5, 6
B_PAWN, B_KNIGHT, B_BISHOP, B_ROOK, B_QUEEN, B_KING = 7, 8, 9, 10, 11, 12

# 0x88 board representation helper
SQ_A1, SQ_H1, SQ_A8, SQ_H8 = 0, 7, 112, 119

# Material Values (MG, EG)
MG_VAL = [0, 82, 337, 365, 477, 1025,  0, 82, 337, 365, 477, 1025, 0]
EG_VAL = [0, 94, 281, 297, 512,  936,  0, 94, 281, 297, 512,  936, 0]

# ==============================================================================
# EVALUATION KNOWLEDGE BASE (PST, Mobility, Safety)
# ==============================================================================

PST_MG = [[0] * 128 for _ in range(13)]
PST_EG = [[0] * 128 for _ in range(13)]

# High-resolution PeSTO Tables
RAW_PST = {
    W_PAWN: [
        [0,0,0,0,0,0,0,0], [98,134,61,95,68,126,34,-11], [-6,7,26,31,65,56,25,-20], [-14,13,6,21,23,12,17,-23],
        [-27,-2,-5,12,17,6,10,-25], [-26,-4,-4,-10,3,3,33,-12], [-35,-1,-20,-23,-15,24,38,-22], [0,0,0,0,0,0,0,0]
    ],
    W_KNIGHT: [
        [-167,-89,-34,-49,61,-97,-15,-107], [-73,-41,72,36,23,62,7,-17], [-47,60,37,65,84,129,73,44], [-9,17,19,53,37,69,18,22],
        [-13,4,16,13,28,19,21,-8], [-23,-9,12,10,19,17,25,-16], [-29,-53,-12,-3,-1,18,-14,-19], [-105,-21,-58,-33,-17,-28,-19,-23]
    ],
    W_BISHOP: [
        [-29,4,-82,-37,-25,-42,7,-8], [-26,16,-18,-13,30,59,18,-47], [-16,37,43,40,35,50,37,-2], [-4,5,19,50,37,37,7,-2],
        [-6,13,13,26,34,12,10,4], [0,15,15,15,14,27,18,10], [4,15,16,0,7,21,33,1], [-33,-3,-14,-21,-13,-12,-39,-21]
    ],
    W_ROOK: [
        [32,42,32,51,63,9,31,43], [27,32,58,62,80,67,26,44], [-5,19,26,36,17,45,61,16], [-24,-11,7,26,24,35,-8,-20],
        [-36,-26,-12,-1,9,-7,6,-23], [-45,-25,-16,-17,3,0,-5,-33], [-44,-16,-20,-9,-1,11,-6,-71], [-19,-13,1,17,16,7,-37,-26]
    ],
    W_QUEEN: [
        [-28,0,29,12,59,44,43,45], [-24,-39,-5,1,-16,57,28,54], [-13,-17,7,8,29,56,47,57], [-27,-27,-16,-16,-1,17,-2,1],
        [-9,-26,-9,-10,-2,-4,3,-3], [-14,2,11,-2,-5,2,14,5], [-35,-8,11,2,8,15,-3,1], [-1,-18,-9,10,-15,-25,-31,-50]
    ],
    W_KING: [
        [-65,23,16,-15,-56,-34,2,13], [29,-1,-20,-7,-8,-4,-38,-29], [-9,24,2,-16,-20,6,22,-22], [-17,-20,-12,-27,-30,-25,-14,-36],
        [-49,-1,-27,-39,-46,-44,-33,-51], [-14,-14,-22,-46,-44,-30,-15,-27], [1,7,-8,-64,-43,-16,9,8], [-15,36,12,-54,8,-28,24,14]
    ]
}

RAW_PST_EG = {
    W_PAWN: [
        [0,0,0,0,0,0,0,0], [178,173,158,134,147,132,165,187], [94,100,85,67,56,53,82,84], [32,24,13,5,-2,4,17,17],
        [13,9,-3,-7,-7,-8,3,-1], [4,7,-6,1,0,-5,-1,-8], [13,8,8,10,13,0,2,-7], [0,0,0,0,0,0,0,0]
    ],
    W_KNIGHT: [
        [-58,-38,-13,-28,-31,-27,-63,-99], [-25,-8,-25,-2,-9,-25,-24,-52], [-24,-20,10,9,-1,-9,-19,-41], [-17,3,22,22,22,11,8,-18],
        [-18,-6,16,25,16,17,4,-18], [-23,-3,-1,15,10,-3,-20,-22], [-42,-20,-10,-5,-2,-20,-23,-44], [-29,-51,-23,-38,-22,-27,-38,-46]
    ],
    W_BISHOP: [
        [-23,-9,-23,-5,-9,-16,-5,-17], [-14,-18,-7,-1,4,-9,-15,-27], [-12,-3,8,10,13,3,-7,-15], [-6,3,13,19,7,10,-3,-9],
        [-3,9,12,9,14,10,3,2], [2,-8,0,-1,-2,6,0,4], [-8,-4,7,-12,-3,-13,-4,-14], [-14,-21,-11,-8,-7,-9,-17,-24]
    ],
    W_ROOK: [
        [13,10,18,15,12,12,8,5], [11,13,13,11,-3,3,8,3], [7,7,7,5,4,-3,-5,-3], [4,3,13,1,2,1,-1,2],
        [3,5,8,4,-5,-6,-8,-11], [-4,0,-5,-1,-7,-12,-8,-16], [-6,-6,0,2,-9,-9,-11,-3], [-9,2,3,-1,-5,-13,4,-20]
    ],
    W_QUEEN: [
        [-9,22,22,27,27,19,10,20], [-17,20,32,41,58,25,30,0], [-20,6,9,49,47,35,19,9], [3,22,24,45,57,40,57,36],
        [-18,28,19,47,31,34,12,11], [16,20,22,51,25,15,14,13], [-22,33,3,22,24,1,14,-8], [-16,-27,28,-14,-2,-5,11,-21]
    ],
    W_KING: [
        [-74,-35,-18,-18,-11,15,4,-17], [-12,17,14,17,17,38,23,11], [10,17,23,15,20,45,44,13], [-8,22,24,27,26,33,26,3],
        [-18,-4,21,24,27,23,9,-11], [-19,-3,11,21,23,16,7,-9], [-27,-11,4,13,14,4,-5,-17], [-53,-34,-21,-11,-28,-14,-24,-43]
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
                sq_b = r * 16 + f
                PST_MG[p+6][sq_b] = -table[r][f]
                PST_EG[p+6][sq_b] = -eg_table[r][f]
init_tables()

# ==============================================================================
# HASHING & TT
# ==============================================================================
Z_PIECE = [[random.getrandbits(64) for _ in range(128)] for _ in range(13)]
Z_SIDE = random.getrandbits(64)
Z_CASTLE = [random.getrandbits(64) for _ in range(16)]
Z_EP = [random.getrandbits(64) for _ in range(128)]

def get_hash(board, side, castle, ep):
    h = 0
    for i in range(128):
        if not (i & 0x88) and board[i] != EMPTY:
            h ^= Z_PIECE[board[i]][i]
    if side == 'b': h ^= Z_SIDE
    h ^= Z_CASTLE[castle]
    if ep != -1: h ^= Z_EP[ep]
    return h

TT = {}
HISTORY = [[0] * 128 for _ in range(128)]
KILLERS = [[None, None] for _ in range(256)]
COUNTER_MOVES = [[None] * 128 for _ in range(128)]

# ==============================================================================
# ENGINE CLASS
# ==============================================================================
class TrinityEngine:
    def __init__(self, fen):
        self.board = [EMPTY] * 128
        self.parse_fen(fen)
        self.nodes = 0
        self.start_time = time.time()
        self.time_limit = 4.80
        self.abort = False
        self.pawn_cache = {}

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
        self.hash = get_hash(self.board, self.side, self.castle, self.ep)

    def is_attacked(self, sq, side):
        if side == 'w':
            if not ((sq-17) & 0x88) and self.board[sq-17] == W_PAWN: return True
            if not ((sq-15) & 0x88) and self.board[sq-15] == W_PAWN: return True
        else:
            if not ((sq+17) & 0x88) and self.board[sq+17] == B_PAWN: return True
            if not ((sq+15) & 0x88) and self.board[sq+15] == B_PAWN: return True
        for d in [-33,-31,-18,-14,14,18,31,33]:
            n = sq+d
            if not (n & 0x88) and self.board[n] == (W_KNIGHT if side == 'w' else B_KNIGHT): return True
        for d, t in [(-16,'RQ'),(16,'RQ'),(-1,'RQ'),(1,'RQ'),(-17,'BQ'),(17,'BQ'),(-15,'BQ'),(15,'BQ')]:
            c = sq+d
            while not (c & 0x88):
                p = self.board[c]
                if p != EMPTY:
                    if PIECES[p].upper() in t and (p <= 6 if side == 'w' else p > 6): return True
                    break
                c += d
        for d in [-17,-16,-15,-1,1,15,16,17]:
            k = sq+d
            if not (k & 0x88) and self.board[k] == (W_KING if side == 'w' else B_KING): return True
        return False

    def see(self, sq, target_side):
        # Static Exchange Evaluation - extremely important for tactical stability
        value = 0
        # This is a simplified version to save space but keep tactical awareness
        piece = self.board[sq]
        if piece == EMPTY: return 0
        return MG_VAL[piece if piece <= 6 else piece - 6]

    def get_moves(self, captures_only=False):
        moves = []
        is_w = self.side == 'w'
        for sq in range(128):
            if sq & 0x88: continue
            p = self.board[sq]
            if p == EMPTY or (p <= 6) != is_w: continue
            pt = p if is_w else p - 6
            if pt == W_PAWN:
                fwd = 16 if is_w else -16
                n = sq+fwd
                if not (n & 0x88) and self.board[n] == EMPTY and not captures_only:
                    if (n >> 4) in [0, 7]:
                        for pr in ([W_QUEEN,W_ROOK,W_BISHOP,W_KNIGHT] if is_w else [B_QUEEN,B_ROOK,B_BISHOP,B_KNIGHT]): moves.append((sq, n, pr))
                    else:
                        moves.append((sq, n, 0))
                        if (sq >> 4) == (1 if is_w else 6) and self.board[n+fwd] == EMPTY: moves.append((sq, n+fwd, 0))
                for d in [fwd-1, fwd+1]:
                    c = sq+d
                    if not (c & 0x88):
                        if self.board[c] != EMPTY and (self.board[c] <= 6) != is_w:
                            if (c >> 4) in [0, 7]:
                                for pr in ([W_QUEEN,W_ROOK,W_BISHOP,W_KNIGHT] if is_w else [B_QUEEN,B_ROOK,B_BISHOP,B_KNIGHT]): moves.append((sq, c, pr))
                            else: moves.append((sq, c, 0))
                        elif c == self.ep: moves.append((sq, c, 0))
            elif pt in [W_KNIGHT, W_KING]:
                diffs = [-33,-31,-18,-14,14,18,31,33] if pt == W_KNIGHT else [-17,-16,-15,-1,1,15,16,17]
                for d in diffs:
                    n = sq+d
                    if not (n & 0x88):
                        if self.board[n] == EMPTY:
                            if not captures_only: moves.append((sq, n, 0))
                        elif (self.board[n] <= 6) != is_w: moves.append((sq, n, 0))
                if pt == W_KING and not captures_only:
                    if is_w:
                        if (self.castle&1) and self.board[5]==EMPTY and self.board[6]==EMPTY and not self.is_attacked(4,'b') and not self.is_attacked(5,'b'): moves.append((4, 6, 0))
                        if (self.castle&2) and self.board[1]==EMPTY and self.board[2]==EMPTY and self.board[3]==EMPTY and not self.is_attacked(4,'b') and not self.is_attacked(3,'b'): moves.append((4, 2, 0))
                    else:
                        if (self.castle&4) and self.board[117]==EMPTY and self.board[118]==EMPTY and not self.is_attacked(116,'w') and not self.is_attacked(117,'w'): moves.append((116, 118, 0))
                        if (self.castle&8) and self.board[113]==EMPTY and self.board[114]==EMPTY and self.board[115]==EMPTY and not self.is_attacked(116,'w') and not self.is_attacked(115,'w'): moves.append((116, 114, 0))
            else:
                ds = []
                if pt in [W_BISHOP, W_QUEEN]: ds += [-17,-15,15,17]
                if pt in [W_ROOK, W_QUEEN]: ds += [-16,-1,1,16]
                for d in ds:
                    n = sq+d
                    while not (n & 0x88):
                        if self.board[n] == EMPTY:
                            if not captures_only: moves.append((sq, n, 0))
                        else:
                            if (self.board[n] <= 6) != is_w: moves.append((sq, n, 0))
                            break
                        n += d
        return moves

    def make_move(self, m):
        f, t, pr = m
        p, cap = self.board[f], self.board[t]
        undo = (self.hash, self.castle, self.ep, cap)
        self.hash ^= Z_PIECE[p][f]
        if cap != EMPTY:
            self.hash ^= Z_PIECE[cap][t]
            if (p == W_PAWN or p == B_PAWN) and t == self.ep:
                ex = t - (16 if p == W_PAWN else -16)
                self.hash ^= Z_PIECE[self.board[ex]][ex]
                self.board[ex] = EMPTY
        self.board[f] = EMPTY
        if pr: self.board[t] = pr; self.hash ^= Z_PIECE[pr][t]
        else: self.board[t] = p; self.hash ^= Z_PIECE[p][t]
        if p == W_KING:
            if f == 4:
                if t == 6: self.board[7]=EMPTY; self.board[5]=W_ROOK; self.hash^=Z_PIECE[W_ROOK][7]^Z_PIECE[W_ROOK][5]
                elif t == 2: self.board[0]=EMPTY; self.board[3]=W_ROOK; self.hash^=Z_PIECE[W_ROOK][0]^Z_PIECE[W_ROOK][3]
            self.castle &= ~3
        elif p == B_KING:
            if f == 116:
                if t == 118: self.board[119]=EMPTY; self.board[117]=B_ROOK; self.hash^=Z_PIECE[B_ROOK][119]^Z_PIECE[B_ROOK][117]
                elif t == 114: self.board[112]=EMPTY; self.board[115]=B_ROOK; self.hash^=Z_PIECE[B_ROOK][112]^Z_PIECE[B_ROOK][115]
            self.castle &= ~12
        oc = self.castle
        if f == 0 or t == 0: self.castle &= ~2
        if f == 7 or t == 7: self.castle &= ~1
        if f == 112 or t == 112: self.castle &= ~8
        if f == 119 or t == 119: self.castle &= ~4
        self.hash ^= Z_CASTLE[oc] ^ Z_CASTLE[self.castle]
        if self.ep != -1: self.hash ^= Z_EP[self.ep]
        if (p == W_PAWN or p == B_PAWN) and abs(f-t) == 32: self.ep = (f+t)//2; self.hash ^= Z_EP[self.ep]
        else: self.ep = -1
        self.side = 'b' if self.side == 'w' else 'w'; self.hash ^= Z_SIDE
        return undo

    def undo_move(self, m, u):
        f, t, pr = m
        h, c, e, cap = u
        self.side = 'b' if self.side == 'w' else 'w'
        p = self.board[t]
        if pr: p = W_PAWN if self.side == 'w' else B_PAWN
        self.board[f], self.board[t] = p, cap
        if (p == W_PAWN or p == B_PAWN) and t == e:
            ex = t - (16 if p == W_PAWN else -16)
            self.board[ex] = B_PAWN if self.side == 'w' else W_PAWN
        if p == W_KING and f == 4:
            if t == 6: self.board[5]=EMPTY; self.board[7]=W_ROOK
            elif t == 2: self.board[3]=EMPTY; self.board[0]=W_ROOK
        elif p == B_KING and f == 116:
            if t == 118: self.board[117]=EMPTY; self.board[119]=B_ROOK
            elif t == 114: self.board[115]=EMPTY; self.board[112]=B_ROOK
        self.hash, self.castle, self.ep = h, c, e

    # ==============================================================================
    # EVALUATION (The Knowledge Expansion)
    # ==============================================================================
    def evaluate_pawns(self):
        # Pawn structure is the soul of chess
        score = 0
        w_pawns = [sq for sq in range(128) if not (sq&0x88) and self.board[sq] == W_PAWN]
        b_pawns = [sq for sq in range(128) if not (sq&0x88) and self.board[sq] == B_PAWN]
        
        # Files setup
        wf, bf = [0]*8, [0]*8
        for p in w_pawns: wf[p&7] += 1
        for p in b_pawns: bf[p&7] += 1
        
        for p in w_pawns:
            f, r = p&7, p>>4
            # Doubled
            if wf[f] > 1: score -= 15
            # Isolated
            if (f == 0 or wf[f-1] == 0) and (f == 7 or wf[f+1] == 0): score -= 20
            # Passed
            is_passed = True
            for r_opp in range(r + 1, 8):
                for f_opp in [f-1, f, f+1]:
                    if 0 <= f_opp <= 7:
                        if self.board[r_opp*16+f_opp] == B_PAWN: is_passed = False; break
            if is_passed: score += 10 + (r * r)

        for p in b_pawns:
            f, r = p&7, p>>4
            if bf[f] > 1: score += 15
            if (f == 0 or bf[f-1] == 0) and (f == 7 or bf[f+1] == 0): score += 20
            is_passed = True
            for r_opp in range(0, r):
                for f_opp in [f-1, f, f+1]:
                    if 0 <= f_opp <= 7:
                        if self.board[r_opp*16+f_opp] == W_PAWN: is_passed = False; break
            if is_passed: score -= (10 + ((7-r) * (7-r)))
        return score

    def evaluate_safety(self, side):
        # King safety based on pawn shield
        bonus = 0
        is_w = side == 'w'
        k_char = W_KING if is_w else B_KING
        ksq = -1
        for i in range(128):
            if not (i&0x88) and self.board[i] == k_char: ksq = i; break
        if ksq == -1: return 0
        
        f, r = ksq&7, ksq>>4
        shield_rank = r + (1 if is_w else -1)
        if 0 <= shield_rank <= 7:
            for f_off in [-1, 0, 1]:
                sf = f + f_off
                if 0 <= sf <= 7:
                    if self.board[shield_rank*16+sf] == (W_PAWN if is_w else B_PAWN): bonus += 15
        return bonus if is_w else -bonus

    def evaluate(self):
        mg, eg, phase = 0, 0, 0
        for sq in range(128):
            if sq & 0x88: continue
            p = self.board[sq]
            if p == EMPTY: continue
            pt = p if p <= 6 else p - 6
            if pt == W_KNIGHT or pt == W_BISHOP: phase += 1
            elif pt == W_ROOK: phase += 2
            elif pt == W_QUEEN: phase += 4
            if p <= 6:
                mg += MG_VAL[pt] + PST_MG[p][sq]
                eg += EG_VAL[pt] + PST_EG[p][sq]
            else:
                mg -= MG_VAL[pt] + abs(PST_MG[p][sq])
                eg -= EG_VAL[pt] + abs(PST_EG[p][sq])
        
        # Add Knowledge Modules
        mg += self.evaluate_pawns() + self.evaluate_safety('w') + self.evaluate_safety('b')
        
        phase = min(phase, 24)
        score = (mg * phase + eg * (24 - phase)) // 24
        return score if self.side == 'w' else -score

    def score_move(self, m, tt_move, ply, last_move):
        if m == tt_move: return 1000000
        f, t, pr = m
        cap = self.board[t]
        if cap != EMPTY:
            return 900000 + (MG_VAL[cap if cap<=6 else cap-6] * 10) - MG_VAL[self.board[f] if self.board[f]<=6 else self.board[f]-6]
        if KILLERS[ply][0] == m: return 800000
        if KILLERS[ply][1] == m: return 700000
        if last_move and COUNTER_MOVES[last_move[0]][last_move[1]] == m: return 600000
        return HISTORY[f][t]

    def quiescence(self, alpha, beta):
        self.nodes += 1
        stand_pat = self.evaluate()
        if stand_pat >= beta: return beta
        if alpha < stand_pat: alpha = stand_pat
        moves = [m for m in self.get_moves(captures_only=True) if self.see(m[1], self.side) >= 0]
        moves.sort(key=lambda m: self.score_move(m, None, 0, None), reverse=True)
        for m in moves:
            u = self.make_move(m)
            ksq = -1
            is_w = self.side == 'b'
            for i in range(128):
                if not (i&0x88) and self.board[i] == (W_KING if is_w else B_KING): ksq = i; break
            if self.is_attacked(ksq, 'b' if is_w else 'w'): self.undo_move(m, u); continue
            score = -self.quiescence(-beta, -alpha)
            self.undo_move(m, u)
            if score >= beta: return beta
            if score > alpha: alpha = score
        return alpha

    def negamax(self, depth, alpha, beta, ply, last_move, can_null=True):
        if (self.nodes & 2047) == 0 and time.time() - self.start_time > self.time_limit: self.abort = True
        if self.abort: return 0
        
        # TT
        tt_entry = TT.get(self.hash)
        tt_move = None
        if tt_entry and tt_entry[0] >= depth:
            if tt_entry[1] == 0: return tt_entry[2]
            if tt_entry[1] == 1 and tt_entry[2] <= alpha: return tt_entry[2]
            if tt_entry[1] == 2 and tt_entry[2] >= beta: return tt_entry[2]
            tt_move = tt_entry[3]

        if depth <= 0: return self.quiescence(alpha, beta)

        # Null Move Pruning
        if can_null and depth >= 3 and not self.is_attacked(4 if self.side=='w' else 116, 'b' if self.side=='w' else 'w'):
            u = self.make_move((0,0,0)) # Logic for null move needs a real skip in 0x88
            # (Simplified null move: we just flip sides)
            self.side = 'b' if self.side == 'w' else 'w'
            score = -self.negamax(depth - 3, -beta, -beta + 1, ply + 1, None, False)
            self.side = 'b' if self.side == 'w' else 'w'
            if score >= beta: return beta

        moves = self.get_moves()
        if not moves:
            ksq = -1
            is_w = self.side == 'w'
            for i in range(128):
                if not (i&0x88) and self.board[i] == (W_KING if is_w else B_KING): ksq = i; break
            return -30000 + ply if self.is_attacked(ksq, 'b' if is_w else 'w') else 0

        moves.sort(key=lambda m: self.score_move(m, tt_move, ply, last_move), reverse=True)
        
        best_v, best_m, orig_a = -100000, None, alpha
        for i, m in enumerate(moves):
            # Futility Pruning
            if depth == 1 and i > 4 and self.evaluate() + 200 < alpha and self.board[m[1]] == EMPTY: continue
            
            u = self.make_move(m)
            ksq = -1
            is_w = self.side == 'b'
            for idx in range(128):
                if not (idx&0x88) and self.board[idx] == (W_KING if is_w else B_KING): ksq = idx; break
            if self.is_attacked(ksq, 'b' if is_w else 'w'): self.undo_move(m, u); continue
            
            # PVS
            if i == 0: score = -self.negamax(depth - 1, -beta, -alpha, ply + 1, m)
            else:
                # LMR
                reduction = 1 if depth >= 3 and i >= 5 and self.board[m[1]] == EMPTY else 0
                score = -self.negamax(depth - 1 - reduction, -alpha - 1, -alpha, ply + 1, m)
                if score > alpha and reduction: score = -self.negamax(depth - 1, -alpha - 1, -alpha, ply + 1, m)
                if score > alpha: score = -self.negamax(depth - 1, -beta, -alpha, ply + 1, m)
            
            self.undo_move(m, u)
            if self.abort: return 0
            if score > best_v:
                best_v, best_m = score, m
                if score > alpha:
                    alpha = score
                    if alpha >= beta:
                        if self.board[m[1]] == EMPTY:
                            HISTORY[m[0]][m[1]] += depth * depth
                            KILLERS[ply][1], KILLERS[ply][0] = KILLERS[ply][0], m
                            if last_move: COUNTER_MOVES[last_move[0]][last_move[1]] = m
                        break
        
        flag = 0 if best_v > orig_a and best_v < beta else (1 if best_v <= orig_a else 2)
        TT[self.hash] = (depth, flag, best_v, best_m)
        return best_v

    def get_best_move(self):
        legal_moves = []
        for m in self.get_moves(False):
            u = self.make_move(m)
            ksq = -1
            is_w = self.side == 'b'
            for idx in range(128):
                if not (idx & 0x88) and self.board[idx] == (W_KING if is_w else B_KING):
                    ksq = idx
                    break
            illegal = self.is_attacked(ksq, 'b' if is_w else 'w')
            self.undo_move(m, u)
            if not illegal:
                legal_moves.append(m)

        if not legal_moves:
            return "0000"

        best_m = None
        # Aspiration Windows
        alpha, beta = -100000, 100000
        for depth in range(1, 15):
            val = self.negamax(depth, alpha, beta, 0, None)
            if self.abort: break
            if val <= alpha or val >= beta:
                alpha, beta = -100000, 100000
                val = self.negamax(depth, alpha, beta, 0, None)
            
            # Use TT to extract best move
            entry = TT.get(self.hash)
            if entry: best_m = entry[3]
            alpha, beta = val - 30, val + 30
            if val > 25000 or val < -25000: break
            
        if best_m not in legal_moves:
            best_m = legal_moves[0]

        if best_m:
            f, t, pr = best_m
            res = f"{chr(97+(f&7))}{ (f>>4)+1 }{chr(97+(t&7))}{ (t>>4)+1 }"
            if pr: res += PIECES[pr].lower()
            return res
        return "0000"

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    for line in sys.stdin:
        fen = line.strip()
        if not fen: continue
        engine = TrinityEngine(fen)
        print(engine.get_best_move())
        sys.stdout.flush()