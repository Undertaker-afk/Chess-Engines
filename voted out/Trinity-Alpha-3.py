#!/usr/bin/env python3
"""Chess agent: reads FEN from stdin, outputs best UCI move to stdout"""
import sys, time, random

# Piece values (centipawns)
PV = {'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000}

# Piece-square tables (white's perspective, row-major 0-63)
PST_P = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]
PST_N = [
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -30,  5, 15, 25, 25, 15,  5,-30,
   -30,  0, 15, 25, 25, 15,  0,-30,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50
]

class Chess:
    def __init__(self):
        self.b = [[None]*8 for _ in range(8)]
        self.turn = 'w'
        self.castling = {'K':1,'Q':1,'k':1,'q':1}
        self.ep = None
        
    def load_fen(self, fen):
        p = fen.split()
        r, c = 0, 0
        for ch in p[0]:
            if ch == '/': r += 1; c = 0
            elif ch.isdigit(): c += int(ch)
            else: self.b[r][c] = ch; c += 1
        self.turn = p[1]
        for f in 'KQkq': self.castling[f] = f in p[2]
        self.ep = p[3] if p[3] != '-' else None
        
    def at(self, r, c): return self.b[r][c] if 0<=r<8 and 0<=c<8 else None
    def enemy(self, p): return p and ((p.islower() if self.turn=='w' else p.isupper()))
    
    def attacked(self, r, c, by):
        """Is square (r,c) attacked by color 'by'?"""
        d = -1 if by=='w' else 1
        for dc in (-1,1):
            nr, nc = r+d, c+dc
            if 0<=nr<8 and 0<=nc<8 and self.at(nr,nc)==('P'if by=='w'else'p'): return True
        for dr,dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            nr, nc = r+dr, c+dc
            if 0<=nr<8 and 0<=nc<8 and self.at(nr,nc)==('N'if by=='w'else'n'): return True
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr==0 and dc==0: continue
                nr, nc = r+dr, c+dc
                if 0<=nr<8 and 0<=nc<8 and self.at(nr,nc)==('K'if by=='w'else'k'): return True
        for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            while 0<=nr<8 and 0<=nc<8:
                p = self.at(nr,nc)
                if p:
                    if p in ('RQ' if by=='w' else 'rq'): return True
                    break
                nr += dr; nc += dc
        for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            nr, nc = r+dr, c+dc
            while 0<=nr<8 and 0<=nc<8:
                p = self.at(nr,nc)
                if p:
                    if p in ('BQ' if by=='w' else 'bq'): return True
                    break
                nr += dr; nc += dc
        return False
        
    def gen_pseudo(self):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.at(r,c)
                if not p or (self.turn=='w' and p.islower()) or (self.turn=='b' and p.isupper()): continue
                pt = p.upper()
                if pt == 'P': self._pawn(moves,r,c)
                elif pt == 'N': self._knight(moves,r,c)
                elif pt == 'B': self._slide(moves,r,c,[(-1,-1),(-1,1),(1,-1),(1,1)])
                elif pt == 'R': self._slide(moves,r,c,[(-1,0),(1,0),(0,-1),(0,1)])
                elif pt == 'Q': self._slide(moves,r,c,[(-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)])
                elif pt == 'K': self._king(moves,r,c)
        return moves
        
    def _pawn(self, moves, r, c):
        d = -1 if self.turn=='w' else 1; sr = 6 if self.turn=='w' else 1; pr = 0 if self.turn=='w' else 7
        nr = r + d
        if 0<=nr<8 and not self.at(nr,c):
            if nr == pr:
                for q in 'qrbn': moves.append((r,c,nr,c,q))
            else:
                moves.append((r,c,nr,c,None))
                if r == sr and not self.at(r+2*d,c): moves.append((r,c,r+2*d,c,None))
        for dc in (-1,1):
            nc = c + dc
            if 0<=nr<8 and 0<=nc<8:
                t = self.at(nr,nc)
                if self.enemy(t):
                    if nr == pr:
                        for q in 'qrbn': moves.append((r,c,nr,nc,q))
                    else: moves.append((r,c,nr,nc,None))
                if self.ep:
                    ec, er = ord(self.ep[0])-97, 8-int(self.ep[1])
                    if nr==er and nc==ec: moves.append((r,c,nr,nc,'ep'))
                    
    def _knight(self, moves, r, c):
        for dr,dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            nr, nc = r+dr, c+dc
            if 0<=nr<8 and 0<=nc<8 and (not self.at(nr,nc) or self.enemy(self.at(nr,nc))):
                moves.append((r,c,nr,nc,None))
                
    def _slide(self, moves, r, c, dirs):
        for dr,dc in dirs:
            nr, nc = r+dr, c+dc
            while 0<=nr<8 and 0<=nc<8:
                t = self.at(nr,nc)
                if not t: moves.append((r,c,nr,nc,None))
                elif self.enemy(t): moves.append((r,c,nr,nc,None)); break
                else: break
                nr += dr; nc += dc
                
    def _king(self, moves, r, c):
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr==0 and dc==0: continue
                nr, nc = r+dr, c+dc
                if 0<=nr<8 and 0<=nc<8 and (not self.at(nr,nc) or self.enemy(self.at(nr,nc))):
                    moves.append((r,c,nr,nc,None))
        if self.turn=='w' and r==7 and c==4:
            if self.castling['K'] and not self.at(7,5) and not self.at(7,6) and not self.attacked(7,4,'b') and not self.attacked(7,5,'b') and not self.attacked(7,6,'b'):
                moves.append((7,4,7,6,'ck'))
            if self.castling['Q'] and not self.at(7,3) and not self.at(7,2) and not self.at(7,1) and not self.attacked(7,4,'b') and not self.attacked(7,3,'b'):
                moves.append((7,4,7,2,'cq'))
        elif self.turn=='b' and r==0 and c==4:
            if self.castling['k'] and not self.at(0,5) and not self.at(0,6) and not self.attacked(0,4,'w') and not self.attacked(0,5,'w') and not self.attacked(0,6,'w'):
                moves.append((0,4,0,6,'ck'))
            if self.castling['q'] and not self.at(0,3) and not self.at(0,2) and not self.at(0,1) and not self.attacked(0,4,'w') and not self.attacked(0,3,'w'):
                moves.append((0,4,0,2,'cq'))
                
    def make(self, m):
        r1,c1,r2,c2,sp = m
        p = self.b[r1][c1]; cap = self.b[r2][c2]; self.b[r1][c1] = None
        if sp == 'ep': self.b[r1][c2] = None; cap = 'p' if p.isupper() else 'P'
        elif sp == 'ck':
            if r1==7: self.b[7][7]=None; self.b[7][5]='R'
            else: self.b[0][7]=None; self.b[0][5]='r'
        elif sp == 'cq':
            if r1==7: self.b[7][0]=None; self.b[7][3]='R'
            else: self.b[0][0]=None; self.b[0][3]='r'
        elif sp in 'qrbn': p = sp if p.islower() else sp.upper()
        self.b[r2][c2] = p
        return cap
        
    def unmake(self, m, cap):
        r1,c1,r2,c2,sp = m
        p = self.b[r2][c2]
        if sp in 'qrbn': p = 'P' if p.isupper() else 'p'
        self.b[r2][c2] = cap; self.b[r1][c1] = p
        if sp == 'ep': self.b[r1][c2] = 'p' if p.isupper() else 'P'
        elif sp == 'ck':
            if r1==7: self.b[7][5]=None; self.b[7][7]='R'
            else: self.b[0][5]=None; self.b[0][7]='r'
        elif sp == 'cq':
            if r1==7: self.b[7][3]=None; self.b[7][0]='R'
            else: self.b[0][3]=None; self.b[0][0]='r'
            
    def legal(self, m):
        sb = [row[:] for row in self.b]
        cap = self.make(m)
        k = 'K' if self.turn=='w' else 'k'; kp = None
        for r in range(8):
            for c in range(8):
                if self.b[r][c] == k: kp = (r,c); break
            if kp: break
        chk = self.attacked(kp[0], kp[1], 'b' if self.turn=='w' else 'w')
        self.b = sb
        return not chk
        
    def gen_legal(self): return [m for m in self.gen_pseudo() if self.legal(m)]
    
    def evaluate(self):
        """Evaluate position from current player's perspective"""
        score = 0
        for r in range(8):
            for c in range(8):
                p = self.at(r,c)
                if not p: continue
                sign = 1 if p.isupper() else -1
                val = PV.get(p.upper(), 0) * sign
                if p.upper() == 'P':
                    idx = r*8+c if p.isupper() else (7-r)*8+c
                    val += PST_P[idx] * sign
                elif p.upper() == 'N':
                    idx = r*8+c if p.isupper() else (7-r)*8+c
                    val += PST_N[idx] * sign
                score += val
        return score if self.turn == 'w' else -score
        
    def quiesce(self, alpha, beta):
        stand = self.evaluate()
        if stand >= beta: return beta
        if stand > alpha: alpha = stand
        for m in self.gen_legal():
            if not (self.at(m[2],m[3]) or m[4]=='ep'): continue
            cap = self.make(m)
            sc = -self.quiesce(-beta, -alpha)
            self.unmake(m, cap)
            if sc >= beta: return beta
            if sc > alpha: alpha = sc
        return alpha
        
    def search(self, depth, alpha, beta, tl, st):
        if time.time() - st > tl: return None, self.evaluate()
        if depth == 0: return None, self.quiesce(alpha, beta)
        moves = self.gen_legal()
        moves.sort(key=lambda m: bool(self.at(m[2],m[3]) or m[4]=='ep'), reverse=True)
        if not moves:
            k = 'K' if self.turn=='w' else 'k'
            for r in range(8):
                for c in range(8):
                    if self.b[r][c] == k:
                        chk = self.attacked(r, c, 'b' if self.turn=='w' else 'w')
                        return None, (-100000 if chk and self.turn=='w' else (100000 if chk else 0))
        best = None
        if self.turn == 'w':
            for m in moves:
                cap = self.make(m)
                _, sc = self.search(depth-1, alpha, beta, tl, st)
                self.unmake(m, cap)
                if sc > alpha: alpha = sc; best = m
                if alpha >= beta: break
            return best, alpha
        else:
            for m in moves:
                cap = self.make(m)
                _, sc = self.search(depth-1, alpha, beta, tl, st)
                self.unmake(m, cap)
                if sc < beta: beta = sc; best = m
                if alpha >= beta: break
            return best, beta
            
    def best_move(self, tl=4.5):
        st = time.time(); best = None
        for d in range(1, 20):
            if time.time() - st > tl: break
            m, _ = self.search(d, -10**6, 10**6, tl, st)
            if m: best = m
        return best
        
    def to_uci(self, m):
        r1,c1,r2,c2,sp = m
        u = chr(97+c1) + str(8-r1) + chr(97+c2) + str(8-r2)
        if sp in 'qrbn': u += sp
        return u

def main():
    ch = Chess()
    for line in sys.stdin:
        fen = line.strip()
        if not fen: continue
        ch.load_fen(fen)
        move = ch.best_move()
        if move: print(ch.to_uci(move))
        else:
            legal = ch.gen_legal()
            if legal: print(ch.to_uci(random.choice(legal)))
        sys.stdout.flush()  # Keep process alive for reuse!

if __name__ == '__main__': main()