#!/usr/bin/env python3
import sys, time

# Piece encoding: 1-6 white, -1 to -6 black
P,N,B,R,Q,K = 1,2,3,4,5,6
PIECE = {'P':1,'N':2,'B':3,'R':4,'Q':5,'K':6,'p':-1,'n':-2,'b':-3,'r':-4,'q':-5,'k':-6}
UNICODE = {1:'♙',2:'♘',3:'♗',4:'♖',5:'♕',6:'♔',-1:'♟',-2:'♞',-3:'♝',-4:'♜',-5:'♛',-6:'♚',0:''}

# 0x88 board helpers
def on_board(sq): return not (sq & 0x88)
def rank(sq): return sq >> 4
def file(sq): return sq & 7
def sq(f,r): return (r<<4)|f
def alg(sq): return 'abcdefgh'[file(sq)]+str(rank(sq)+1)
def parse_alg(s): return sq('abcdefgh'.index(s[0]), int(s[1])-1)

# Piece-square tables (PeSTO, tapered)
PST_MG = [
[],  # 0
[0,0,0,0,0,0,0,0, 98,134,61,95,68,126,34,-11, -6,7,26,31,65,56,25,-20, -14,13,6,21,23,12,17,-23, -27,-2,-5,12,17,6,10,-25, -26,-4,-4,-10,3,3,33,-12, -35,-1,-20,-23,-15,24,38,-22, 0,0,0,0,0,0,0,0],
[-167,-89,-34,-49,61,-97,-15,-107, -73,-41,72,36,23,62,7,-17, -47,60,37,65,84,129,73,44, -9,17,19,53,37,69,18,22, -13,4,16,13,28,19,21,-8, -23,-9,12,10,19,17,25,-16, -29,-53,-12,-3,-1,18,-14,-19, -105,-21,-58,-33,-17,-28,-19,-23],
[-29,-4,-82,-37,-25,-42,7,-8, -26,16,-18,-13,30,59,18,-47, -16,37,43,40,35,50,37,-2, -4,5,19,50,37,37,7,-2, -6,13,13,26,34,12,10,4, 0,15,15,15,14,27,18,10, 4,15,16,0,7,21,33,1, -33,-3,-14,-21,-13,-12,-39,-21],
[32,42,32,51,63,9,31,43, 27,32,58,62,80,67,26,44, -5,19,26,36,17,45,61,16, -24,-11,7,26,24,35,-8,-20, -36,-26,-12,-1,9,-7,6,-23, -45,-25,-16,-17,3,0,-5,-33, -44,-20,-20,-9,-1,11,-6,-71, -19,-13,1,17,16,7,-37,-26],
[28,0,29,12,59,44,43,45, -24,-39,-5,1,-16,57,28,54, -13,-17,7,8,29,56,47,57, -27,-27,-16,-16,-1,17,-2,1, -9,-26,-9,-10,-2,-4,3,-3, -14,2,-11,-2,-5,2,14,5, -35,-8,11,2,8,15,-3,1, -1,-18,-9,10,-15,-25,-31,-50],
[-65,23,16,-15,-56,-34,2,13, 29,-1,-20,-7,-8,-4,-38,-29, -9,24,2,-16,-20,6,22,-22, -17,-20,-12,-27,-30,-25,-14,-36, -49,-1,-27,-39,-46,-44,-33,-51, -14,-14,-22,-46,-44,-30,-15,-27, 1,7,-8,-64,-43,-16,9,8, -15,36,12,-54,8,-28,24,14]
]

PST_EG = [
[],
[0,0,0,0,0,0,0,0, 178,173,158,134,147,132,165,187, 94,100,85,67,56,53,82,84, 32,24,13,5,-2,4,17,17, 13,9,-3,-7,-7,-8,3,-1, 4,7,-6,1,0,-5,-1,-8, 13,8,8,10,13,0,2,-7, 0,0,0,0,0,0,0,0],
[-58,-38,-13,-28,-31,-27,-63,-99, -25,-8,-25,-2,-9,-25,-24,-52, -24,-20,10,9,-1,-9,-19,-41, -17,3,22,22,22,11,8,-18, -18,-6,16,25,16,17,4,-18, -23,-3,-1,15,10,-3,-20,-22, -42,-20,-10,-5,-2,-20,-23,-44, -29,-51,-23,-15,-22,-18,-50,-64],
[-14,-21,-11,-8,-7,-9,-17,-24, -8,-4,7,-12,-3,-13,-4,-14, 2,-8,0,-1,-2,6,0,4, -3,9,12,9,14,10,3,2, -6,3,13,19,7,10,-3,-9, -12,-3,8,10,13,3,-7,-15, -14,-18,-7,-1,4,-9,-15,-27, -23,-9,-23,-5,-9,-16,-5,-17],
[-9,11,-3,12,21,8,19,17, 25,23,43,40,66,49,35,50, 11,4,35,54,76,64,39,25, 2,3,12,36,54,48,21,2, -6,-5,15,21,23,26,0,-8, -14,-9,-1,4,9,12,-19,-25, -23,-20,-24,7,1,-5,-18,-24, -24,-4,-10,2,-4,-9,-1,-9],
[14,32,22,21,4,5,17,32, 12,17,23,15,29,35,30,23, 8,17,22,35,38,45,43,29, -6,-4,3,13,16,21,15,2, -12,-18,0,-1,0,-3,-18,-15, -38,-22,-18,-11,-11,-17,-27,-49, -40,-35,-23,-9,-19,-30,-44,-55, -36,-26,-24,-19,-34,-42,-38,-31],
[-72,-54,47,-8,-32,22,55,78, -2,7,21,54,92,108,74,24, 24,7,26,40,75,106,84,47, -16,-10,17,45,66,93,68,28, -36,-20,3,25,54,77,47,12, -51,-37,-20,4,37,61,32,-8, -68,-58,-38,-21,5,20,6,-21, -68,-26,-3,-33,-3,-32,55,-38]
]

PIECE_VAL = [0,100,320,330,500,900,20000]
PHASE = [0,0,1,1,2,4]

DIRS = {
    N: [-33,-31,-18,-14,14,18,31,33],
    B: [-17,-15,15,17],
    R: [-16,-1,1,16],
    Q: [-17,-16,-15,-1,1,15,16,17],
    K: [-17,-16,-15,-1,1,15,16,17]
}

class Board:
    __slots__ = ('b','side','castle','ep','half','full','king','hash','stack')
    def __init__(self, fen):
        self.b = [0]*128; self.stack=[]
        parts = fen.split()
        r=7; f=0
        for ch in parts[0]:
            if ch=='/': r-=1; f=0
            elif ch.isdigit(): f+=int(ch)
            else: self.b[sq(f,r)]=PIECE[ch]; f+=1
        self.side = 1 if parts[1]=='w' else -1
        self.castle = 0
        for c in parts[2]:
            if c=='K':self.castle|=1
            elif c=='Q':self.castle|=2
            elif c=='k':self.castle|=4
            elif c=='q':self.castle|=8
        self.ep = parse_alg(parts[3]) if parts[3]!='-' else -1
        self.half=int(parts[4]); self.full=int(parts[5])
        self.king=[0,0]
        for s in range(128):
            if on_board(s):
                p=self.b[s]
                if p==K: self.king[0]=s
                elif p==-K: self.king[1]=s
        self.hash=0

    def at(self,s): return self.b[s] if on_board(s) else 99

def gen_pseudo(board, side):
    moves=[]; b=board.b; ep=board.ep
    for s in range(128):
        if not on_board(s): continue
        p=b[s]
        if p*side<=0: continue
        t=abs(p)
        if t==P:
            fwd = s+16*side
            if on_board(fwd) and b[fwd]==0:
                if rank(fwd)==(7 if side==1 else 0):
                    for q in [Q,R,B,N]: moves.append((s,fwd,q*side,0))
                else:
                    moves.append((s,fwd,0,0))
                    if rank(s)==(1 if side==1 else 6):
                        f2=s+32*side
                        if b[f2]==0: moves.append((s,f2,0,1))
            for df in (-1,1):
                cap=s+16*side+df
                if not on_board(cap): continue
                target=b[cap]
                if target*side<0:
                    if rank(cap)==(7 if side==1 else 0):
                        for q in [Q,R,B,N]: moves.append((s,cap,q*side,0))
                    else: moves.append((s,cap,0,0))
                elif cap==ep: moves.append((s,cap,0,2))
        elif t==N:
            for d in DIRS[N]:
                t2=s+d
                if on_board(t2) and b[t2]*side<=0: moves.append((s,t2,0,0))
        else:
            dirs = DIRS[t] if t in DIRS else []
            for d in dirs:
                t2=s+d
                while on_board(t2):
                    tp=b[t2]
                    if tp==0: moves.append((s,t2,0,0))
                    else:
                        if tp*side<0: moves.append((s,t2,0,0))
                        break
                    if t in (N,K): break
                    t2+=d
    # castling
    if side==1 and board.king[0]==sq(4,0):
        if board.castle&1 and b[sq(5,0)]==0 and b[sq(6,0)]==0 and b[sq(7,0)]==R:
            moves.append((sq(4,0),sq(6,0),0,3))
        if board.castle&2 and b[sq(3,0)]==0 and b[sq(2,0)]==0 and b[sq(1,0)]==0 and b[sq(0,0)]==R:
            moves.append((sq(4,0),sq(2,0),0,4))
    if side==-1 and board.king[1]==sq(4,7):
        if board.castle&4 and b[sq(5,7)]==0 and b[sq(6,7)]==0 and b[sq(7,7)]==-R:
            moves.append((sq(4,7),sq(6,7),0,3))
        if board.castle&8 and b[sq(3,7)]==0 and b[sq(2,7)]==0 and b[sq(1,7)]==0 and b[sq(0,7)]==-R:
            moves.append((sq(4,7),sq(2,7),0,4))
    return moves

def attacked(board, sq_attack, side):
    b=board.b
    # pawns
    for df in (-1,1):
        s = sq_attack-16*side+df
        if on_board(s) and b[s]==P*side: return True
    # knights
    for d in DIRS[N]:
        s=sq_attack+d
        if on_board(s) and b[s]==N*side: return True
    # bishops/queens
    for d in DIRS[B]:
        s=sq_attack+d
        while on_board(s):
            p=b[s]
            if p!=0:
                if p==B*side or p==Q*side: return True
                break
            s+=d
    # rooks/queens
    for d in DIRS[R]:
        s=sq_attack+d
        while on_board(s):
            p=b[s]
            if p!=0:
                if p==R*side or p==Q*side: return True
                break
            s+=d
    # king
    for d in DIRS[K]:
        s=sq_attack+d
        if on_board(s) and b[s]==K*side: return True
    return False

def make(board, move):
    fr,to,promo,flag = move
    b=board.b; side=board.side
    piece=b[fr]; cap=b[to]
    board.stack.append((fr,to,piece,cap,promo,flag,board.castle,board.ep,board.half,board.king[:]))
    b[fr]=0
    if flag==2: # ep
        cap_sq = to-16*side
        cap=b[cap_sq]; b[cap_sq]=0
    elif flag==3: # castle K
        rk = sq(7, rank(fr)); b[rk]=0; b[sq(5,rank(fr))]=R*side
    elif flag==4: # castle Q
        rk=sq(0,rank(fr)); b[rk]=0; b[sq(3,rank(fr))]=R*side
    b[to]=promo if promo else piece
    if abs(piece)==K:
        board.king[0 if side==1 else 1]=to
        board.castle &= ~(3 if side==1 else 12)
    if piece==R*side:
        if fr==sq(0,0): board.castle&=~2
        elif fr==sq(7,0): board.castle&=~1
        elif fr==sq(0,7): board.castle&=~8
        elif fr==sq(7,7): board.castle&=~4
    if cap==-R*side or (flag==2 and side==1):
        if to==sq(0,7): board.castle&=~8
        elif to==sq(7,7): board.castle&=~4
    if cap==R*side or (flag==2 and side==-1):
        if to==sq(0,0): board.castle&=~2
        elif to==sq(7,0): board.castle&=~1
    board.ep = to-8*side if flag==1 else -1
    board.half = 0 if abs(piece)==P or cap!=0 else board.half+1
    board.side=-side

def unmake(board):
    fr,to,piece,cap,promo,flag,castle,ep,half,king = board.stack.pop()
    b=board.b; side=-board.side
    board.castle=castle; board.ep=ep; board.half=half; board.king=king
    b[fr]=piece; b[to]=cap
    if flag==2:
        cap_sq=to-16*side
        b[cap_sq]=-P*side; b[to]=0
    elif flag==3:
        b[sq(5,rank(fr))]=0; b[sq(7,rank(fr))]=R*side
    elif flag==4:
        b[sq(3,rank(fr))]=0; b[sq(0,rank(fr))]=R*side
    board.side=side

def gen_legal(board):
    moves=gen_pseudo(board, board.side)
    legal=[]
    for m in moves:
        make(board,m)
        ksq=board.king[0 if board.side==-1 else 1]
        if not attacked(board, ksq, board.side):
            # check castling through check
            fr,to,p,fl=m
            if fl in (3,4):
                mid = (fr+to)//2
                if attacked(board, fr, board.side) or attacked(board, mid, board.side):
                    unmake(board); continue
            legal.append(m)
        unmake(board)
    return legal

def eval_pos(board):
    score=0; phase=0
    b=board.b
    for s in range(128):
        if not on_board(s): continue
        p=b[s]
        if p==0: continue
        t=abs(p); v=PIECE_VAL[t]
        sign=1 if p>0 else -1
        # pst
        idx = s if p>0 else s^0x70
        mg=PST_MG[t][rank(idx)*8+file(idx)]
        eg=PST_EG[t][rank(idx)*8+file(idx)]
        score += sign*(v+mg)
        phase += PHASE[t]
    phase = min(24, phase)
    # tapered (simplified)
    return score*board.side

def mvv_lva(board, move):
    fr,to,p,fl=move
    cap=abs(board.b[to]) if board.b[to]!=0 else (P if fl==2 else 0)
    att=abs(board.b[fr])
    return cap*10 - att

nodes=0
killers=[]
def search(board, depth, alpha, beta, ply, start, limit):
    global nodes, killers
    if time.time()-start>limit: raise TimeoutError
    nodes+=1
    if depth<=0: return quiesce(board, alpha, beta, start, limit)
    in_check = attacked(board, board.king[0 if board.side==1 else 1], -board.side)
    if in_check: depth+=1
    moves=gen_legal(board)
    if not moves: return -20000+ply if in_check else 0
    # sort
    moves.sort(key=lambda m: mvv_lva(board,m), reverse=True)
    if ply < len(killers):
        k = killers[ply]
        if k in moves: moves.remove(k); moves.insert(0,k)
    best=-30000
    for i,m in enumerate(moves):
        make(board,m)
        score = -search(board, depth-1, -beta, -alpha, ply+1, start, limit)
        unmake(board)
        if score>best: best=score
        if score>alpha:
            alpha=score
            if ply>=len(killers): killers.append(m)
            else: killers[ply]=m
        if alpha>=beta: break
    return best

def quiesce(board, alpha, beta, start, limit):
    global nodes
    nodes+=1
    stand = eval_pos(board)
    if stand>=beta: return beta
    if stand>alpha: alpha=stand
    moves=[m for m in gen_legal(board) if board.b[m[1]]!=0 or m[3]==2]
    moves.sort(key=lambda m: mvv_lva(board,m), reverse=True)
    for m in moves[:8]:
        make(board,m)
        score=-quiesce(board, -beta, -alpha, start, limit)
        unmake(board)
        if score>=beta: return beta
        if score>alpha: alpha=score
    return alpha

def find_best(board, max_time=4.8):
    global nodes, killers
    start=time.time(); nodes=0; killers=[]
    best_move=None; depth=1
    moves=gen_legal(board)
    if not moves: return None,0,0,[]
    moves.sort(key=lambda m: mvv_lva(board,m), reverse=True)
    try:
        while time.time()-start < max_time*0.85 and depth<=32:
            best_score=-30000
            for m in moves:
                make(board,m)
                score=-search(board, depth-1, -30000, 30000, 1, start, max_time)
                unmake(board)
                if score>best_score:
                    best_score=score; best_move=m
            depth+=1
    except TimeoutError:
        pass
    return best_move, best_score, depth-1, moves

def move_to_uci(m):
    fr,to,p,fl=m
    u=alg(fr)+alg(to)
    if p:
        u+='qrbn'[[Q,R,B,N].index(abs(p))]
    return u

def main():
    for line in sys.stdin:
        fen=line.strip()
        if not fen: continue
        board=Board(fen)
        start=time.time()
        move,score,depth,_=find_best(board,4.8)
        elapsed=int((time.time()-start)*1000)
        uci = move_to_uci(move) if move else '0000'
        sys.stdout.write(uci+'\n'); sys.stdout.flush()

if __name__=='__main__':
    main()