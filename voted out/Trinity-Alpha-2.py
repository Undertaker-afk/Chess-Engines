# made by grok-4.20-multi-agent-beta-0309


import sys
import time
import random
from copy import deepcopy

class ChessAgent:
    def __init__(self):
        self.piece_values = {'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000}
        self.max_time = 4.8  # seconds

        # Simple piece-square tables (flattened 0-63, a1=0, h1=7, a8=56, h8=63)
        self.pst = {
            'P': [0, 0, 0, 0, 0, 0, 0, 0,
                  5, 10, 15, 20, 20, 15, 10, 5,
                  4, 8, 12, 16, 16, 12, 8, 4,
                  0, 5, 10, 25, 25, 10, 5, 0,
                  0, 0, 5, 20, 20, 5, 0, 0,
                  5, 0, -5, 0, 0, -5, 0, 5,
                  5, 10, 10, -20, -20, 10, 10, 5,
                  0, 0, 0, 0, 0, 0, 0, 0],
            'N': [-20, -10, -5, -5, -5, -5, -10, -20,
                  -10, 0, 5, 10, 10, 5, 0, -10,
                  -5, 5, 10, 15, 15, 10, 5, -5,
                  -5, 5, 15, 20, 20, 15, 5, -5,
                  -5, 5, 10, 15, 15, 10, 5, -5,
                  -10, 0, 5, 10, 10, 5, 0, -10,
                  -20, -10, -5, -5, -5, -5, -10, -20],
            'B': [-10, -5, -5, -10, -10, -5, -5, -10,
                  -5, 5, 5, 5, 5, 5, 5, -5,
                  -5, 5, 10, 10, 10, 10, 5, -5,
                  -5, 5, 10, 15, 15, 10, 5, -5,
                  -5, 5, 10, 15, 15, 10, 5, -5,
                  -5, 5, 10, 10, 10, 10, 5, -5,
                  -5, 5, 5, 5, 5, 5, 5, -5,
                  -10, -5, -5, -10, -10, -5, -5, -10],
            'R': [5, 10, 10, 10, 10, 10, 10, 5,
                  5, 10, 10, 10, 10, 10, 10, 5,
                  -5, 0, 0, 5, 5, 0, 0, -5,
                  -5, 0, 0, 5, 5, 0, 0, -5,
                  -5, 0, 0, 5, 5, 0, 0, -5,
                  -5, 0, 0, 5, 5, 0, 0, -5,
                  -5, 0, 0, 5, 5, 0, 0, -5,
                  5, 10, 10, 10, 10, 10, 10, 5],
            'Q': [-10, -5, -5, -5, -5, -5, -5, -10,
                  -5, 0, 0, 0, 0, 0, 0, -5,
                  -5, 0, 5, 5, 5, 5, 0, -5,
                  -5, 0, 5, 10, 10, 5, 0, -5,
                  -5, 0, 5, 10, 10, 5, 0, -5,
                  -5, 0, 5, 5, 5, 5, 0, -5,
                  -5, 0, 0, 0, 0, 0, 0, -5,
                  -10, -5, -5, -5, -5, -5, -5, -10],
            'K': [-30, -40, -40, -50, -50, -40, -40, -30,
                  -30, -40, -40, -50, -50, -40, -40, -30,
                  -30, -40, -40, -50, -50, -40, -40, -30,
                  -30, -40, -40, -50, -50, -40, -40, -30,
                  -20, -30, -30, -40, -40, -30, -30, -20,
                  -10, -20, -20, -20, -20, -20, -20, -10,
                  20, 20, 0, 0, 0, 0, 20, 20,
                  20, 30, 10, 0, 0, 10, 30, 20]
        }

    def parse_fen(self, fen):
        parts = fen.strip().split()
        board = [['.' for _ in range(8)] for _ in range(8)]
        rank, file = 7, 0
        for char in parts[0]:
            if char == '/':
                rank -= 1
                file = 0
            elif char.isdigit():
                file += int(char)
            else:
                board[rank][file] = char
                file += 1
        return board, parts[1], parts[2], parts[3] if len(parts) > 3 else '-'

    def square_name(self, r, c):
        return chr(ord('a') + c) + str(r + 1)

    def uci(self, move, promoted=''):
        r1, c1, r2, c2 = move
        u = self.square_name(r1, c1) + self.square_name(r2, c2)
        return u + promoted.lower() if promoted else u

    def get_legal_moves(self, board, side):
        moves = []
        is_white = side == 'w'
        for r in range(8):
            for c in range(8):
                piece = board[r][c]
                if not piece or (piece.isupper() != is_white):
                    continue
                ptype = piece.upper()
                if ptype == 'P':
                    moves.extend(self._pawn_moves(board, r, c, is_white))
                elif ptype == 'N':
                    moves.extend(self._knight_moves(board, r, c, is_white))
                elif ptype in 'BRQ':
                    moves.extend(self._sliding_moves(board, r, c, is_white, ptype))
                elif ptype == 'K':
                    moves.extend(self._king_moves(board, r, c, is_white))
        return [m for m in moves if not self._leaves_king_in_check(board, m, side)]

    def _pawn_moves(self, board, r, c, is_white):
        moves = []
        dir = 1 if is_white else -1
        start_rank = 1 if is_white else 6

        # Forward
        if 0 <= r + dir < 8 and board[r + dir][c] == '.':
            moves.append((r, c, r + dir, c))
            if r == start_rank and board[r + 2 * dir][c] == '.':
                moves.append((r, c, r + 2 * dir, c))

        # Captures
        for dc in [-1, 1]:
            nc = c + dc
            if 0 <= nc < 8:
                target = board[r + dir][nc]
                if target != '.' and target.isupper() != is_white:
                    moves.append((r, c, r + dir, nc))
        return moves

    def _knight_moves(self, board, r, c, is_white):
        deltas = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        moves = []
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target == '.' or target.isupper() != is_white:
                    moves.append((r, c, nr, nc))
        return moves

    def _sliding_moves(self, board, r, c, is_white, ptype):
        moves = []
        directions = []
        if ptype in ('R', 'Q'):
            directions += [(0,1),(0,-1),(1,0),(-1,0)]
        if ptype in ('B', 'Q'):
            directions += [(1,1),(1,-1),(-1,1),(-1,-1)]

        for dr, dc in directions:
            for i in range(1, 8):
                nr, nc = r + i*dr, c + i*dc
                if not (0 <= nr < 8 and 0 <= nc < 8):
                    break
                target = board[nr][nc]
                if target == '.':
                    moves.append((r, c, nr, nc))
                elif target.isupper() != is_white:
                    moves.append((r, c, nr, nc))
                    break
                else:
                    break
        return moves

    def _king_moves(self, board, r, c, is_white):
        moves = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = board[nr][nc]
                    if target == '.' or target.isupper() != is_white:
                        moves.append((r, c, nr, nc))
        return moves

    def _leaves_king_in_check(self, board, move, side):
        new_board = deepcopy(board)
        r1, c1, r2, c2 = move
        piece = new_board[r1][c1]
        new_board[r2][c2] = piece
        new_board[r1][c1] = '.'

        # Auto-promote to queen
        if piece.upper() == 'P' and (r2 == 0 or r2 == 7):
            new_board[r2][c2] = 'Q' if piece.isupper() else 'q'

        king = 'K' if side == 'w' else 'k'
        king_r, king_c = next((i, j) for i in range(8) for j in range(8) if new_board[i][j] == king)
        opponent_side = 'b' if side == 'w' else 'w'

        for r in range(8):
            for c in range(8):
                p = new_board[r][c]
                if p and p.isupper() != (opponent_side == 'w'):
                    for m in self.get_legal_moves(new_board, opponent_side):  # recursive but depth limited by pruning
                        if m[2] == king_r and m[3] == king_c:
                            return True
        return False

    def evaluate(self, board):
        score = 0
        for r in range(8):
            for c in range(8):
                piece = board[r][c]
                if piece == '.': continue
                ptype = piece.upper()
                value = self.piece_values.get(ptype, 0)
                if piece.islower():
                    value = -value
                score += value

                # Add PST
                pst_value = self.pst.get(ptype, [0]*64)[r*8 + c]
                if piece.islower():
                    pst_value = -pst_value
                score += pst_value
        return score

    def search(self, board, side, depth, alpha, beta, start_time):
        if time.time() - start_time > self.max_time:
            return self.evaluate(board), None

        if depth == 0:
            return self.evaluate(board), None

        best_move = None
        best_value = -999999 if side == 'w' else 999999
        moves = self.get_legal_moves(board, side)

        # Simple move ordering: captures first
        def move_score(m):
            captured = board[m[2]][m[3]]
            if captured:
                return self.piece_values.get(captured.upper(), 0) * 10
            return 0
        moves.sort(key=move_score, reverse=True)

        for move in moves:
            new_board = deepcopy(board)
            r1, c1, r2, c2 = move
            piece = new_board[r1][c1]
            new_board[r2][c2] = piece
            new_board[r1][c1] = '.'
            if piece.upper() == 'P' and (r2 == 0 or r2 == 7):
                new_board[r2][c2] = 'Q' if piece.isupper() else 'q'

            value, _ = self.search(new_board, 'b' if side == 'w' else 'w', depth - 1, alpha, beta, start_time)

            if side == 'w':
                if value > best_value:
                    best_value = value
                    best_move = move
                alpha = max(alpha, value)
            else:
                if value < best_value:
                    best_value = value
                    best_move = move
                beta = min(beta, value)

            if beta <= alpha:
                break

        return best_value, best_move

    def best_move(self, fen):
        board, side, _, _ = self.parse_fen(fen)
        start_time = time.time()

        # Iterative deepening
        best = None
        for depth in range(1, 6):
            if time.time() - start_time > self.max_time:
                break
            _, move = self.search(board, side, depth, -999999, 999999, start_time)
            if move:
                best = move

        if not best:
            legal = self.get_legal_moves(board, side)
            if legal:
                best = random.choice(legal)

        if best:
            r1, c1, r2, c2 = best
            promoted = 'q' if board[r1][c1].upper() == 'P' and (r2 in (0, 7)) else ''
            return self.uci(best, promoted)
        return "e2e4"  # fallback


if __name__ == "__main__":
    agent = ChessAgent()
    for line in sys.stdin:
        fen = line.strip()
        if fen:
            move = agent.best_move(fen)
            print(move, flush=True)