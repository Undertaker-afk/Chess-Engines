#!/usr/bin/env python3
"""
Trinity-1.0 - The Ultimate Python Chess Engine
Synthesized from the best of Trinity-0.1, Trinity-0.4, and agent.js

Features:
- 0x88 board with integer piece IDs (fast, bug-free)
- PeSTO tapered evaluation (MG/EG blending)
- Zobrist hashing + Transposition Table
- PVS (Principal Variation Search)
- LMR (Late Move Reductions)
- Null Move Pruning
- SEE filtering in quiescence
- Check extensions
- Repetition detection
- Move ordering: MVV-LVA -> Killers -> History -> Counter-Moves
- Pawn structure, king safety, mobility, bishop pair
- Iterative deepening with aspiration windows
- Process reuse for TT persistence across moves
"""
import sys
import time
import random

# ==============================================================================
# CONSTANTS & BOARD SETUP (0x88 representation)
# ==============================================================================
EMPTY = 0
PIECES = " PNBRQKpnbrqk"
WP, WN, WB, WR, WQ, WK = 1, 2, 3, 4, 5, 6
BP, BN, BB, BR, BQ, BK = 7, 8, 9, 10, 11, 12

# Material values (middlegame, endgame) - PeSTO standard
MG_VAL = [0, 82, 337, 365, 477, 1025, 0, 82, 337, 365, 477, 1025, 0]
EG_VAL = [0, 94, 281, 297, 512, 936, 0, 94, 281, 297, 512, 936, 0]

# ==============================================================================
# PIECE-SQUARE TABLES (High-Resolution PeSTO)
# ==============================================================================
PST_MG = [[0] * 128 for _ in range(13)]
PST_EG = [[0] * 128 for _ in range(13)]

RAW_MG = {
    WP: [0,0,0,0,0,0,0,0, 98,134,61,95,68,126,34,-11, -6,7,26,31,65,56,25,-20, -14,13,6,21,23,12,17,-23,
         -27,-2,-5,12,17,6,10,-25, -26,-4,-4,-10,3,3,33,-12, -35,-1,-20,-23,-15,24,38,-22, 0,0,0,0,0,0,0,0],
    WN: [-167,-89,-34,-49,61,-97,-15,-107, -73,-41,72,36,23,62,7,-17, -47,60,37,65,84,129,73,44, -9,17,19,53,37,69,18,22,
         -13,4,16,13,28,19,21,-8, -23,-9,12,10,19,17,25,-16, -29,-53,-12,-3,-1,18,-14,-19, -105,-21,-58,-33,-17,-28,-19,-23],
    WB: [-29,4,-82,-37,-25,-42,7,-8, -26,16,-18,-13,30,59,18,-47, -16,37,43,40,35,50,37,-2, -4,5,19,50,37,37,7,-2,
         -6,13,13,26,34,12,10,4, 0,15,15,15,14,27,18,10, 4,15,16,0,7,21,33,1, -33,-3,-14,-21,-13,-12,-39,-21],
    WR: [32,42,32,51,63,9,31,43, 27,32,58,62,80,67,26,44, -5,19,26,36,17,45,61,16, -24,-11,7,26,24,35,-8,-20,
         -36,-26,-12,-1,9,-7,6,-23, -45,-25,-16,-17,3,0,-5,-33, -44,-16,-20,-9,-1,11,-6,-71, -19,-13,1,17,16,7,-37,-26],
    WQ: [-28,0,29,12,59,44,43,45, -24,-39,-5,1,-16,57,28,54, -13,-17,7,8,29,56,47,57, -27,-27,-16,-16,-1,17,-2,1,
         -9,-26,-9,-10,-2,-4,3,-3, -14,2,-11,-2,-5,2,14,5, -35,-8,11,2,8,15,-3,1, -1,-18,-9,10,-15,-25,-31,-50],
    WK: [-65,23,16,-15,-56,-34,2,13, 29,-1,-20,-7,-8,-4,-38,-29, -9,24,2,-16,-20,6,22,-22, -17,-20,-12,-27,-30,-25,-14,-36,
         -49,-1,-27,-39,-46,-44,-33,-51, -14,-14,-22,-46,-44,-30,-15,-27, 1,7,-8,-64,-43,-16,9,8, -15,36,12,-54,8,-28,24,14]
}
RAW_EG = {
    WP: [0,0,0,0,0,0,0,0, 178,173,158,134,147,132,165,187, 94,100,85,67,56,53,82,84, 32,24,13,5,-2,4,17,17,
         13,9,-3,-7,-7,-8,3,-1, 4,7,-6,1,0,-5,-1,-8, 13,8,8,10,13,0,2,-7, 0,0,0,0,0,0,0,0],
    WN: [-58,-38,-13,-28,-31,-27,-63,-99, -25,-8,-25,-2,-9,-25,-24,-52, -24,-20,10,9,-1,-9,-19,-41, -17,3,22,22,22,11,8,-18,
         -18,-6,16,25,16,17,4,-18, -23,-3,-1,15,10,-3,-20,-22, -42,-20,-10,-5,-2,-20,-23,-44, -29,-51,-23,-38,-22,-27,-38,-46],
    WB: [-23,-9,-23,-5,-9,-16,-5,-17, -14,-18,-7,-1,4,-9,-15,-27, -12,-3,8,10,13,3,-7,-15, -6,3,13,19,7,10,-3,-9,
         -3,9,12,9,14,10,3,2, 2,-8,0,-1,-2,6,0,4, -8,-4,7,-12,-3,-13,-4,-14, -14,-21,-11,-8,-7,-9,-17,-24],
    WR: [13,10,18,15,12,12,8,5, 11,13,13,11,-3,3,8,3, 7,7,7,5,4,-3,-5,-3, 4,3,13,1,2,1,-1,2,
         3,5,8,4,-5,-6,-8,-11, -4,0,-5,-1,-7,-12,-8,-16, -6,-6,0,2,-9,-9,-11,-3, -9,2,3,-1,-5,-13,4,-20],
    WQ: [-9,22,22,27,27,19,10,20, -17,20,32,41,58,25,30,0, -20,6,9,49,47,35,19,9, 3,22,24,45,57,40,57,36,
         -18,28,19,47,31,34,12,11, 16,20,22,51,25,15,14,13, -22,33,3,22,24,1,14,-8, -16,-27,28,-14,-2,-5,11,-21],
    WK: [-74,-35,-18,-18,-11,15,4,-17, -12,17,14,17,17,38,23,11, 10,17,23,15,20,45,44,13, -8,22,24,27,26,33,26,3,
         -18,-4,21,24,27,23,9,-11, -19,-3,11,21,23,16,7,-9, -27,-11,4,13,14,4,-5,-17, -53,-34,-21,-11,-28,-14,-24,-43]
}

def _init_pst():
    for p in RAW_MG:
        for r in range(8):
            for f in range(8):
                sq = (7 - r) * 16 + f
                PST_MG[p][sq] = RAW_MG[p][r * 8 + f]
                PST_EG[p][sq] = RAW_EG[p][r * 8 + f]
                PST_MG[p + 6][r * 16 + f] = -RAW_MG[p][r * 8 + f]
                PST_EG[p + 6][r * 16 + f] = -RAW_EG[p][r * 8 + f]
_init_pst()

# ==============================================================================
# ZOBRIST HASHING
# ==============================================================================
Z_PIECE = [[random.getrandbits(64) for _ in range(128)] for _ in range(13)]
Z_SIDE = random.getrandbits(64)
Z_CASTLE = [random.getrandbits(64) for _ in range(16)]
Z_EP = [random.getrandbits(64) for _ in range(128)]

def zobrist(board, side, castle, ep):
    h = 0
    for sq in range(128):
        if not (sq & 0x88) and board[sq]:
            h ^= Z_PIECE[board[sq]][sq]
    if side == 'b':
        h ^= Z_SIDE
    h ^= Z_CASTLE[castle]
    if ep != -1:
        h ^= Z_EP[ep]
    return h

# ==============================================================================
# GLOBAL SEARCH DATA (persistent for process reuse)
# ==============================================================================
TT = {}  # {hash: (depth, flag, score, move)}
HIST = [[0] * 128 for _ in range(128)]
KILLER = [[None, None] for _ in range(256)]
COUNTER = [[None] * 128 for _ in range(128)]
NODES, START, LIMIT, ABORT = 0, 0, 4.85, False

# Replication stack for repetition detection
REP_STACK = []

# ==============================================================================
# CHESS ENGINE CLASS
# ==============================================================================
class Trinity:
    def __init__(self, fen=None):
        self.b = [0] * 128
        if fen:
            self.parse_fen(fen)

    def parse_fen(self, fen):
        self.b = [0] * 128
        p = fen.split()
        r, f = 7, 0
        for c in p[0]:
            if c == '/':
                r, f = r - 1, 0
            elif c.isdigit():
                f += int(c)
            else:
                self.b[r * 16 + f] = PIECES.index(c)
                f += 1
        self.side = p[1]
        self.castle = sum(1 << i for i, c in enumerate('KQkq') if c in (p[2] if len(p) > 2 else '-'))
        self.ep = -1 if len(p) < 4 or p[3] == '-' else (int(p[3][1]) - 1) * 16 + ord(p[3][0]) - 97
        self.hash = zobrist(self.b, self.side, self.castle, self.ep)

    def attacked(self, sq, white):
        for d in (-17, -15) if white else (17, 15):
            if not (sq + d & 0x88) and self.b[sq + d] == (WP if white else BP):
                return True
        for d in (-33, -31, -18, -14, 14, 18, 31, 33):
            if not (sq + d & 0x88) and self.b[sq + d] == (WN if white else BN):
                return True
        for d in (-17, -16, -15, -1, 1, 15, 16, 17):
            if not (sq + d & 0x88) and self.b[sq + d] == (WK if white else BK):
                return True
        for dirs, types in [((-16, 16, -1, 1), 'RQ'), ((-17, -15, 15, 17), 'BQ')]:
            for d in dirs:
                c = sq + d
                while not (c & 0x88):
                    p = self.b[c]
                    if p:
                        if PIECES[p].upper() in types and (p <= 6) == white:
                            return True
                        break
                    c += d
        return False

    def gen_moves(self, caps_only=False):
        moves, is_w = [], self.side == 'w'
        for sq in range(128):
            if sq & 0x88:
                continue
            p = self.b[sq]
            if not p or (p <= 6) != is_w:
                continue
            pt = p if is_w else p - 6
            if pt == WP:
                fwd, sr, pr = (16, 1, 7) if is_w else (-16, 6, 0)
                if not caps_only:
                    to = sq + fwd
                    if not (to & 0x88) and not self.b[to]:
                        if (to >> 4) == pr:
                            for promo in (WQ, WR, WB, WN) if is_w else (BQ, BR, BB, BN):
                                moves.append((sq, to, promo))
                        else:
                            moves.append((sq, to, 0))
                            if (sq >> 4) == sr and not self.b[to + fwd]:
                                moves.append((sq, to + fwd, 0))
                for cd in (fwd - 1, fwd + 1):
                    to = sq + cd
                    if not (to & 0x88):
                        t = self.b[to]
                        if t and (t <= 6) != is_w:
                            if (to >> 4) == pr:
                                for promo in (WQ, WR, WB, WN) if is_w else (BQ, BR, BB, BN):
                                    moves.append((sq, to, promo))
                            else:
                                moves.append((sq, to, 0))
                        elif to == self.ep:
                            moves.append((sq, to, 0))
            elif pt in (WN, WK):
                for d in ((-33, -31, -18, -14, 14, 18, 31, 33) if pt == WN else (-17, -16, -15, -1, 1, 15, 16, 17)):
                    to = sq + d
                    if not (to & 0x88):
                        t = self.b[to]
                        if not t:
                            if not caps_only:
                                moves.append((sq, to, 0))
                        elif (t <= 6) != is_w:
                            moves.append((sq, to, 0))
                if pt == WK and not caps_only:
                    if is_w:
                        if self.castle & 1 and not self.b[5] and not self.b[6] and self.b[7] == WR and not self.attacked(4, 0) and not self.attacked(5, 0):
                            moves.append((4, 6, 0))
                        if self.castle & 2 and not self.b[1] and not self.b[2] and not self.b[3] and self.b[0] == WR and not self.attacked(4, 0) and not self.attacked(3, 0):
                            moves.append((4, 2, 0))
                    else:
                        if self.castle & 4 and not self.b[117] and not self.b[118] and self.b[119] == BR and not self.attacked(116, 1) and not self.attacked(117, 1):
                            moves.append((116, 118, 0))
                        if self.castle & 8 and not self.b[113] and not self.b[114] and not self.b[115] and self.b[112] == BR and not self.attacked(116, 1) and not self.attacked(115, 1):
                            moves.append((116, 114, 0))
            elif pt in (WB, WR, WQ):
                dirs = []
                if pt in (WB, WQ):
                    dirs += (-17, -15, 15, 17)
                if pt in (WR, WQ):
                    dirs += (-16, -1, 1, 16)
                for d in dirs:
                    to = sq + d
                    while not (to & 0x88):
                        t = self.b[to]
                        if not t:
                            if not caps_only:
                                moves.append((sq, to, 0))
                        else:
                            if (t <= 6) != is_w:
                                moves.append((sq, to, 0))
                            break
                        to += d
        return moves

    def make(self, m):
        f, t, pr = m
        p, cap = self.b[f], self.b[t]
        undo = (self.hash, self.castle, self.ep, cap)
        self.hash ^= Z_PIECE[p][f]
        if cap:
            self.hash ^= Z_PIECE[cap][t]
            if p in (WP, BP) and t == self.ep:
                ex = t - (16 if p == WP else -16)
                self.hash ^= Z_PIECE[self.b[ex]][ex]
                self.b[ex] = 0
        self.b[f] = 0
        self.b[t] = pr if pr else p
        self.hash ^= Z_PIECE[self.b[t]][t]
        if p == WK and f == 4:
            if t == 6:
                self.b[5], self.b[7] = WR, 0
                self.hash ^= Z_PIECE[WR][5] ^ Z_PIECE[WR][7]
            elif t == 2:
                self.b[3], self.b[0] = WR, 0
                self.hash ^= Z_PIECE[WR][3] ^ Z_PIECE[WR][0]
            self.castle &= ~3
        elif p == BK and f == 116:
            if t == 118:
                self.b[117], self.b[119] = BR, 0
                self.hash ^= Z_PIECE[BR][117] ^ Z_PIECE[BR][119]
            elif t == 114:
                self.b[115], self.b[112] = BR, 0
                self.hash ^= Z_PIECE[BR][115] ^ Z_PIECE[BR][112]
            self.castle &= ~12
        oc = self.castle
        if f in (0, 4) or t in (0, 4):
            self.castle &= ~2
        if f in (7, 4) or t in (7, 4):
            self.castle &= ~1
        if f in (112, 116) or t in (112, 116):
            self.castle &= ~8
        if f in (119, 116) or t in (119, 116):
            self.castle &= ~4
        self.hash ^= Z_CASTLE[oc] ^ Z_CASTLE[self.castle]
        if self.ep != -1:
            self.hash ^= Z_EP[self.ep]
        if p in (WP, BP) and abs(f - t) == 32:
            self.ep = (f + t) // 2
            self.hash ^= Z_EP[self.ep]
        else:
            self.ep = -1
        self.side = 'b' if self.side == 'w' else 'w'
        self.hash ^= Z_SIDE
        return undo

    def unmake(self, m, u):
        f, t, pr = m
        h, cas, ep, cap = u
        self.side = 'b' if self.side == 'w' else 'w'
        p = self.b[t]
        if pr:
            p = WP if self.side == 'w' else BP
        self.b[f], self.b[t] = p, cap
        if p in (WP, BP) and t == ep:
            ex = t - (16 if p == WP else -16)
            self.b[ex] = BP if self.side == 'w' else WP
        if p == WK and f == 4:
            if t == 6:
                self.b[5], self.b[7] = 0, WR
            elif t == 2:
                self.b[3], self.b[0] = 0, WR
        elif p == BK and f == 116:
            if t == 118:
                self.b[117], self.b[119] = 0, BR
            elif t == 114:
                self.b[115], self.b[112] = 0, BR
        self.hash, self.castle, self.ep = h, cas, ep

    def eval_pawns(self):
        score = 0
        for side_p, enemy_p, sign in [(WP, BP, 1), (BP, WP, -1)]:
            pawns = [sq for sq in range(128) if not (sq & 0x88) and self.b[sq] == side_p]
            files = [sum(1 for p in pawns if p & 7 == f) for f in range(8)]
            for p in pawns:
                f, r = p & 7, p >> 4
                if files[f] > 1:
                    score -= 15 * sign
                if (f == 0 or files[f - 1] == 0) and (f == 7 or files[f + 1] == 0):
                    score -= 20 * sign
                passed = True
                rank_iter = range(r + 1, 8) if side_p == WP else range(r - 1, -1, -1)
                for rr in rank_iter:
                    for ff in (f - 1, f, f + 1):
                        if 0 <= ff < 8 and self.b[rr * 16 + ff] == enemy_p:
                            passed = False
                            break
                    if not passed:
                        break
                if passed:
                    if side_p == WP:
                        score += (10 + r * r) * sign
                    else:
                        score += (10 + (7 - r) * (7 - r)) * sign
        return score

    def eval_king_safety(self, side):
        is_w = side == 'w'
        ksq = next((i for i in range(128) if not (i & 0x88) and self.b[i] == (WK if is_w else BK)), -1)
        if ksq < 0:
            return 0
        f, r = ksq & 7, ksq >> 4
        shield = r + (1 if is_w else -1)
        bonus = 0
        if 0 <= shield < 8:
            for ff in (f - 1, f, f + 1):
                if 0 <= ff < 8 and self.b[shield * 16 + ff] == (WP if is_w else BP):
                    bonus += 12
        for d in (-17, -16, -15, -1, 1, 15, 16, 17, 33, 31, 18, 14, -14, -18, -31, -33):
            atk = ksq + d
            if not (atk & 0x88) and self.b[atk] and (self.b[atk] <= 6) != is_w and self.b[atk] not in (WP, BP):
                bonus -= 8
        return bonus if is_w else -bonus

    def eval_mobility(self, side):
        score, is_w = 0, side == 'w'
        for sq in range(128):
            if sq & 0x88:
                continue
            p = self.b[sq]
            if not p or (p <= 6) != is_w:
                continue
            pt = p if is_w else p - 6
            if pt == WN:
                for d in (-33, -31, -18, -14, 14, 18, 31, 33):
                    if not (sq + d & 0x88) and not self.b[sq + d]:
                        score += 3
            elif pt in (WB, WR, WQ):
                dirs = []
                if pt in (WB, WQ):
                    dirs += (-17, -15, 15, 17)
                if pt in (WR, WQ):
                    dirs += (-16, -1, 1, 16)
                for d in dirs:
                    c = sq + d
                    while not (c & 0x88):
                        if not self.b[c]:
                            score += 2
                        else:
                            break
                        c += d
        return score if is_w else -score

    def evaluate(self):
        mg = eg = phase = 0
        for sq in range(128):
            if sq & 0x88:
                continue
            p = self.b[sq]
            if not p:
                continue
            pt = p if p <= 6 else p - 6
            if pt in (WN, WB):
                phase += 1
            elif pt == WR:
                phase += 2
            elif pt == WQ:
                phase += 4
            if p <= 6:
                mg += MG_VAL[pt] + PST_MG[p][sq]
                eg += EG_VAL[pt] + PST_EG[p][sq]
            else:
                mg -= MG_VAL[pt] + PST_MG[p][sq]
                eg -= EG_VAL[pt] + PST_EG[p][sq]
        wb = bb = 0
        for sq in range(128):
            if not (sq & 0x88):
                if self.b[sq] == WB:
                    wb += 1
                elif self.b[sq] == BB:
                    bb += 1
        if wb >= 2:
            mg += 30
            eg += 45
        if bb >= 2:
            mg -= 30
            eg -= 45
        mg += self.eval_pawns() + self.eval_king_safety('w') + self.eval_king_safety('b')
        mg += self.eval_mobility('w') + self.eval_mobility('b')
        phase = min(phase, 24)
        score = (mg * phase + eg * (24 - phase)) // 24
        return score if self.side == 'w' else -score

    def see(self, m):
        f, t, pr = m
        cap = self.b[t]
        if not cap and m[1] != self.ep:
            return 0
        victim = MG_VAL[cap if cap <= 6 else cap - 6] if cap else 100
        attacker = MG_VAL[self.b[f] if self.b[f] <= 6 else self.b[f] - 6]
        return victim - attacker // 10

    def score_move(self, m, tt_m, ply, last):
        f, t, pr = m
        if m == tt_m:
            return 10 ** 7
        cap = self.b[t]
        if cap or m[1] == self.ep:
            victim = MG_VAL[cap if cap <= 6 else cap - 6] if cap else 100
            attacker = MG_VAL[self.b[f] if self.b[f] <= 6 else self.b[f] - 6]
            return 9 * 10 ** 6 + victim * 10 - attacker
        if pr:
            return 8 * 10 ** 6 + MG_VAL[pr]
        if KILLER[ply][0] == m:
            return 7 * 10 ** 6
        if KILLER[ply][1] == m:
            return 6 * 10 ** 6
        if last and COUNTER[last[0]][last[1]] == m:
            return 5 * 10 ** 6
        return HIST[f][t]

    def is_repetition(self):
        if len(REP_STACK) < 2:
            return False
        current = self.hash
        count = 0
        for i in range(len(REP_STACK) - 2, -1, -2):
            if REP_STACK[i] == current:
                count += 1
                if count >= 1:
                    return True
        return False

    def quiesce(self, alpha, beta):
        global NODES, ABORT
        NODES += 1
        if NODES & 2047 == 0 and time.time() - START > LIMIT:
            ABORT = True
            return 0
        stand = self.evaluate()
        if stand >= beta:
            return beta
        if stand > alpha:
            alpha = stand
        moves = [m for m in self.gen_moves(caps_only=True) if self.see(m) >= 0]
        moves.sort(key=lambda m: self.score_move(m, None, 0, None), reverse=True)
        for m in moves:
            u = self.make(m)
            original_side = 'w' if self.side == 'b' else 'b'
            king_piece = WK if original_side == 'w' else BK
            ks = next((i for i in range(128) if not (i & 0x88) and self.b[i] == king_piece), -1)
            if ks != -1 and self.attacked(ks, original_side == 'b'):
                self.unmake(m, u)
                continue
            s = -self.quiesce(-beta, -alpha)
            self.unmake(m, u)
            if s >= beta:
                return beta
            if s > alpha:
                alpha = s
        return alpha

    def search(self, depth, alpha, beta, ply, last, can_null=True, is_pv=True):
        global NODES, ABORT, TT, HIST, KILLER, COUNTER
        NODES += 1
        if NODES & 2047 == 0 and time.time() - START > LIMIT:
            ABORT = True
            return 0

        if ply > 0 and self.is_repetition():
            return 0

        entry = TT.get(self.hash)
        tt_m = None
        if entry and entry[0] >= depth:
            d, f, v, m = entry
            if f == 0:
                return v
            if f == 1 and v <= alpha:
                return v
            if f == 2 and v >= beta:
                return v
            tt_m = m

        if depth <= 0:
            return self.quiesce(alpha, beta)

        in_check = self.attacked(
            next((i for i in range(128) if not (i & 0x88) and self.b[i] == (WK if self.side == 'w' else BK)), -1),
            self.side == 'b'
        )
        if in_check:
            depth += 1

        if depth == 1 and self.evaluate() + 250 < alpha:
            return self.quiesce(alpha, beta)

        if can_null and depth >= 3 and not in_check and is_pv:
            has_minor = any(self.b[s] in (WN, WN + 6, WB, WB + 6) for s in range(128) if not (s & 0x88))
            if has_minor:
                self.side = 'b' if self.side == 'w' else 'w'
                self.hash ^= Z_SIDE
                s = -self.search(depth - 3, -beta, -beta + 1, ply + 1, None, False, False)
                self.side = 'b' if self.side == 'w' else 'w'
                self.hash ^= Z_SIDE
                if s >= beta:
                    return beta

        moves = self.gen_moves()
        if not moves:
            ks = next((i for i in range(128) if not (i & 0x88) and self.b[i] == (WK if self.side == 'w' else BK)), -1)
            return -30000 + ply if self.attacked(ks, self.side == 'b') else 0

        moves.sort(key=lambda m: self.score_move(m, tt_m, ply, last), reverse=True)
        best, best_m, orig_a = -10 ** 6, None, alpha
        legal = 0

        for i, m in enumerate(moves):
            if depth == 1 and i > 5 and self.evaluate() + 150 < alpha and not self.b[m[1]] and m[1] != self.ep:
                continue

            u = self.make(m)
            original_side = 'w' if self.side == 'b' else 'b'
            king_piece = WK if original_side == 'w' else BK
            ks = next((i for i in range(128) if not (i & 0x88) and self.b[i] == king_piece), -1)
            if ks != -1 and self.attacked(ks, original_side == 'b'):
                self.unmake(m, u)
                continue

            legal += 1

            if legal == 1:
                s = -self.search(depth - 1, -beta, -alpha, ply + 1, m, can_null, is_pv)
            else:
                reduction = 1 if depth >= 3 and i >= 4 and not self.b[m[1]] and m[1] != self.ep else 0
                s = -self.search(depth - 1 - reduction, -alpha - 1, -alpha, ply + 1, m, can_null, False)
                if s > alpha and reduction:
                    s = -self.search(depth - 1, -alpha - 1, -alpha, ply + 1, m, can_null, False)
                if is_pv and s > alpha and s < beta:
                    s = -self.search(depth - 1, -beta, -alpha, ply + 1, m, can_null, True)

            self.unmake(m, u)
            if ABORT:
                return 0

            if s > best:
                best, best_m = s, m
            if s > alpha:
                alpha = s
                if alpha >= beta:
                    if not self.b[m[1]] and m[1] != self.ep:
                        HIST[m[0]][m[1]] += depth * depth
                        KILLER[ply][1], KILLER[ply][0] = KILLER[ply][0], m
                        if last:
                            COUNTER[last[0]][last[1]] = m
                    break

        flag = 0 if best > orig_a and best < beta else (1 if best <= orig_a else 2)
        TT[self.hash] = (depth, flag, best, best_m)
        return best

    def get_move(self, fen):
        global TT, HIST, KILLER, COUNTER, NODES, ABORT, START, LIMIT, REP_STACK
        if len(TT) > 500000:
            TT.clear()
        HIST = [[0] * 128 for _ in range(128)]
        KILLER = [[None, None] for _ in range(256)]
        COUNTER = [[None] * 128 for _ in range(128)]
        NODES = ABORT = 0
        self.parse_fen(fen)
        START = time.time()
        LIMIT = 4.85
        REP_STACK.append(self.hash)

        legal = []
        for m in self.gen_moves():
            u = self.make(m)
            original_side = 'w' if self.side == 'b' else 'b'
            king_piece = WK if original_side == 'w' else BK
            ks = next((i for i in range(128) if not (i & 0x88) and self.b[i] == king_piece), -1)
            if ks != -1 and not self.attacked(ks, original_side == 'b'):
                legal.append(m)
            self.unmake(m, u)
        if not legal:
            REP_STACK.pop()
            return "0000"

        best_m = legal[0]
        alpha, beta = -50000, 50000
        for depth in range(1, 30):
            if time.time() - START > LIMIT:
                break
            val = self.search(depth, alpha, beta, 0, None, can_null=True, is_pv=True)
            if ABORT:
                break
            if val <= alpha or val >= beta:
                alpha, beta = -50000, 50000
                val = self.search(depth, alpha, beta, 0, None, can_null=True, is_pv=True)
            alpha, beta = val - 30, val + 30
            entry = TT.get(self.hash)
            if entry and entry[3] in legal:
                best_m = entry[3]
            if val > 25000 or val < -25000:
                break

        if best_m not in legal:
            best_m = legal[0]
        f, t, pr = best_m
        uci = f"{chr(97 + (f & 7))}{(f >> 4) + 1}{chr(97 + (t & 7))}{(t >> 4) + 1}"
        if pr:
            uci += PIECES[pr].lower()
        REP_STACK.pop()
        return uci


# ==============================================================================
# MAIN LOOP - Process Reuse for Multiple Moves
# ==============================================================================
if __name__ == "__main__":
    engine = None
    for line in sys.stdin:
        fen = line.strip()
        if not fen:
            continue
        if not engine:
            engine = Trinity(fen)
        print(engine.get_move(fen))
        sys.stdout.flush()
