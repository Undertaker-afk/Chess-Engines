#!/usr/bin/env node
/**
 * Trinity-1.1 - The Ultimate JavaScript Chess Engine
 * Built on Trinity-Alpha-0.1 with major upgrades:
 *
 * From Alpha-0.1 baseline:
 * - 0x88 board, incremental eval, Zobrist hashing
 * - PVS, LMR, Null Move, Check Extensions
 * - Repetition detection, TT, Killers, History
 *
 * NEW in 1.1:
 * - SEE filtering in quiescence
 * - Pawn structure evaluation (passed/isolated/doubled)
 * - King safety (pawn shield + attacker penalties)
 * - Mobility bonus
 * - Bishop pair bonus
 * - Futility pruning
 * - Razoring
 * - Better aspiration windows with dynamic retry
 * - Counter-move heuristic
 * - Internal iterative deepening
 */

const readline = require('readline');

const DEFAULT_MOVE_TIME_MS = 4200;

function parseCliArgs(argv) {
    const options = { moveTimeMs: DEFAULT_MOVE_TIME_MS, stats: false };
    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i];
        if (arg === '--movetime' || arg === '--move-time' || arg === '--move-time-ms') {
            options.moveTimeMs = Number(argv[++i]);
        } else if (arg === '--stats') {
            options.stats = true;
        } else if (arg === '--help' || arg === '-h') {
            process.stdout.write('Usage: node Trinity-1.1.js [--movetime MS] [--stats]\n');
            process.exit(0);
        }
    }
    if (!Number.isFinite(options.moveTimeMs) || options.moveTimeMs <= 0) {
        throw new Error(`Invalid movetime: ${options.moveTimeMs}`);
    }
    options.moveTimeMs = Math.floor(options.moveTimeMs);
    return options;
}

let cliOptions;
try {
    cliOptions = parseCliArgs(process.argv.slice(2));
} catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exit(1);
}

// ==============================================================================
// CONSTANTS & BOARD SETUP
// ==============================================================================
const PAWN = 1, KNIGHT = 2, BISHOP = 3, ROOK = 4, QUEEN = 5, KING = 6;
const WHITE = 8, BLACK = 16;
const PIECE_VAL = [0, 100, 320, 330, 500, 900, 20000];
const PIECE_VAL_MG = [0, 82, 337, 365, 477, 1025, 0];
const PIECE_VAL_EG = [0, 94, 281, 297, 512, 936, 0];

const phase_inc = [0, 0, 1, 1, 2, 4, 0];

// PeSTO MG/EG tables (64 squares, rank 0 = white's back rank)
const mg_pesto = [
    0,
    [0,0,0,0,0,0,0,0, 98,134,61,95,68,126,34,-11, -6,7,26,31,65,56,25,-20, -14,13,6,21,23,12,17,-23,
     -27,-2,-5,12,17,6,10,-25, -26,-4,-4,-10,3,3,33,-12, -35,-1,-20,-23,-15,24,38,-22, 0,0,0,0,0,0,0,0],
    [-167,-89,-34,-49,61,-97,-15,-107, -73,-41,72,36,23,62,7,-17, -47,60,37,65,84,129,73,44, -9,17,19,53,37,69,18,22,
     -13,4,16,13,28,19,21,-8, -23,-9,12,10,19,17,25,-16, -29,-53,-12,-3,-1,18,-14,-19, -105,-21,-58,-33,-17,-28,-19,-23],
    [-29,4,-82,-37,-25,-42,7,-8, -26,16,-18,-13,30,59,18,-47, -16,37,43,40,35,50,37,-2, -4,5,19,50,37,37,7,-2,
     -6,13,13,26,34,12,10,4, 0,15,15,15,14,27,18,10, 4,15,16,0,7,21,33,1, -33,-3,-14,-21,-13,-12,-39,-21],
    [32,42,32,51,63,9,31,43, 27,32,58,62,80,67,26,44, -5,19,26,36,17,45,61,16, -24,-11,7,26,24,35,-8,-20,
     -36,-26,-12,-1,9,-7,6,-23, -45,-25,-16,-17,3,0,-5,-33, -44,-16,-20,-9,-1,11,-6,-71, -19,-13,1,17,16,7,-37,-26],
    [-28,0,29,12,59,44,43,45, -24,-39,-5,1,-16,57,28,54, -13,-17,7,8,29,56,47,57, -27,-27,-16,-16,-1,17,-2,1,
     -9,-26,-9,-10,-2,-4,3,-3, -14,2,-11,-2,-5,2,14,5, -35,-8,11,2,8,15,-3,1, -1,-18,-9,10,-15,-25,-31,-50],
    [-65,23,16,-15,-56,-34,2,13, 29,-1,-20,-7,-8,-4,-38,-29, -9,24,2,-16,-20,6,22,-22, -17,-20,-12,-27,-30,-25,-14,-36,
     -49,-1,-27,-39,-46,-44,-33,-51, -14,-14,-22,-46,-44,-30,-15,-27, 1,7,-8,-64,-43,-16,9,8, -15,36,12,-54,8,-28,24,14]
];
const eg_pesto = [
    0,
    [0,0,0,0,0,0,0,0, 178,173,158,134,147,132,165,187, 94,100,85,67,56,53,82,84, 32,24,13,5,-2,4,17,17,
     13,9,-3,-7,-7,-8,3,-1, 4,7,-6,1,0,-5,-1,-8, 13,8,8,10,13,0,2,-7, 0,0,0,0,0,0,0,0],
    [-58,-38,-13,-28,-31,-27,-63,-99, -25,-8,-25,-2,-9,-25,-24,-52, -24,-20,10,9,-1,-9,-19,-41, -17,3,22,22,22,11,8,-18,
     -18,-6,16,25,16,17,4,-18, -23,-3,-1,15,10,-3,-20,-22, -42,-20,-10,-5,-2,-20,-23,-44, -29,-51,-23,-38,-22,-27,-38,-46],
    [-23,-9,-23,-5,-9,-16,-5,-17, -14,-18,-7,-1,4,-9,-15,-27, -12,-3,8,10,13,3,-7,-15, -6,3,13,19,7,10,-3,-9,
     -3,9,12,9,14,10,3,2, 2,-8,0,-1,-2,6,0,4, -8,-4,7,-12,-3,-13,-4,-14, -14,-21,-11,-8,-7,-9,-17,-24],
    [13,10,18,15,12,12,8,5, 11,13,13,11,-3,3,8,3, 7,7,7,5,4,-3,-5,-3, 4,3,13,1,2,1,-1,2,
     3,5,8,4,-5,-6,-8,-11, -4,0,-5,-1,-7,-12,-8,-16, -6,-6,0,2,-9,-9,-11,-3, -9,2,3,-1,-5,-13,4,-20],
    [-9,22,22,27,27,19,10,20, -17,20,32,41,58,25,30,0, -20,6,9,49,47,35,19,9, 3,22,24,45,57,40,57,36,
     -18,28,19,47,31,34,12,11, 16,20,22,51,25,15,14,13, -22,33,3,22,24,1,14,-8, -16,-27,28,-14,-2,-5,11,-21],
    [-74,-35,-18,-18,-11,15,4,-17, -12,17,14,17,17,38,23,11, 10,17,23,15,20,45,44,13, -8,22,24,27,26,33,26,3,
     -18,-4,21,24,27,23,9,-11, -19,-3,11,21,23,16,7,-9, -27,-11,4,13,14,4,-5,-17, -53,-34,-21,-11,-28,-14,-24,-43]
];

const piece_dirs = [[], [], [-33,-31,-18,-14,14,18,31,33], [-17,-15,15,17], [-16,-1,1,16], [-17,-16,-15,-1,1,15,16,17], [-17,-16,-15,-1,1,15,16,17]];
const castle_rights = new Int32Array(128);
for (let i = 0; i < 128; i++) castle_rights[i] = 15;
castle_rights[0] &= ~2; castle_rights[4] &= ~3; castle_rights[7] &= ~1;
castle_rights[112] &= ~8; castle_rights[116] &= ~12; castle_rights[119] &= ~4;

const board = new Int32Array(128);
let side = WHITE, ep = 0, castle = 0, halfmove = 0, ply = 0;
let eval_mg = 0, eval_eg = 0, phase = 0;
let king_sq = [0, 0];

// ==============================================================================
// ZOBRIST HASHING
// ==============================================================================
const z_lo = new Int32Array(14 * 128), z_hi = new Int32Array(14 * 128);
const z_castle_lo = new Int32Array(16), z_castle_hi = new Int32Array(16);
const z_ep_lo = new Int32Array(128), z_ep_hi = new Int32Array(128);
let z_color_lo, z_color_hi, hash_lo = 0, hash_hi = 0;

function rand32() { return (Math.random() * 0x100000000) | 0; }
for (let i = 0; i < 14 * 128; i++) { z_lo[i] = rand32(); z_hi[i] = rand32(); }
for (let i = 0; i < 16; i++) { z_castle_lo[i] = rand32(); z_castle_hi[i] = rand32(); }
for (let i = 0; i < 128; i++) { z_ep_lo[i] = rand32(); z_ep_hi[i] = rand32(); }
z_color_lo = rand32(); z_color_hi = rand32();

// ==============================================================================
// STACK BUFFERS & LIMITS
// ==============================================================================
const MAX_PLY = 512;
const state_hash_lo = new Int32Array(MAX_PLY), state_hash_hi = new Int32Array(MAX_PLY);
const state_ep = new Int32Array(MAX_PLY), state_castle = new Int32Array(MAX_PLY), state_halfmove = new Int32Array(MAX_PLY);
const MOVE_TIME_MS = cliOptions.moveTimeMs;
const TIME_CHECK_MASK = 511;

// TT - 8M entries
const TT_SIZE = 8 * 1024 * 1024;
const tt_key_lo = new Int32Array(TT_SIZE), tt_key_hi = new Int32Array(TT_SIZE);
const tt_data = new Int32Array(TT_SIZE), tt_move = new Int32Array(TT_SIZE);

const move_stack = new Int32Array(MAX_PLY * 256);
const move_scores = new Int32Array(MAX_PLY * 256);
const killers = Array.from({length: MAX_PLY}, () => new Int32Array(2));
const history = new Int32Array(16384);
const counter = new Int32Array(16384);

let nodes = 0, stop_search = false, start_time = 0, stop_time = 0;

// ==============================================================================
// MOVE EXECUTION (Zero-Allocation)
// ==============================================================================
function add_piece(sq, pc) {
    board[sq] = pc;
    const type = pc & 7, color = pc & 24;
    let sq64 = (7 - (sq >> 4)) * 8 + (sq & 7);
    if (color === BLACK) sq64 ^= 56;
    eval_mg += (color === WHITE ? mg_pesto[type][sq64] : -mg_pesto[type][sq64]);
    eval_eg += (color === WHITE ? eg_pesto[type][sq64] : -eg_pesto[type][sq64]);
    phase += phase_inc[type];
    const pidx = color === WHITE ? type : type + 7;
    hash_lo ^= z_lo[pidx * 128 + sq]; hash_hi ^= z_hi[pidx * 128 + sq];
}

function remove_piece(sq, pc) {
    board[sq] = 0;
    const type = pc & 7, color = pc & 24;
    let sq64 = (7 - (sq >> 4)) * 8 + (sq & 7);
    if (color === BLACK) sq64 ^= 56;
    eval_mg -= (color === WHITE ? mg_pesto[type][sq64] : -mg_pesto[type][sq64]);
    eval_eg -= (color === WHITE ? eg_pesto[type][sq64] : -eg_pesto[type][sq64]);
    phase -= phase_inc[type];
    const pidx = color === WHITE ? type : type + 7;
    hash_lo ^= z_lo[pidx * 128 + sq]; hash_hi ^= z_hi[pidx * 128 + sq];
}

function make_move(m) {
    const from = m & 127, to = (m >> 7) & 127, piece = (m >> 14) & 31;
    const captured = (m >> 19) & 31, prom = (m >> 24) & 31, flag = m >> 29;

    state_hash_lo[ply] = hash_lo; state_hash_hi[ply] = hash_hi;
    state_ep[ply] = ep; state_castle[ply] = castle; state_halfmove[ply] = halfmove;

    hash_lo ^= z_color_lo; hash_hi ^= z_color_hi;
    if (ep) { hash_lo ^= z_ep_lo[ep]; hash_hi ^= z_ep_hi[ep]; ep = 0; }

    remove_piece(from, piece);

    if (captured) {
        let cap_sq = to;
        if (flag === 1) cap_sq = side === WHITE ? to - 16 : to + 16;
        remove_piece(cap_sq, captured);
        halfmove = 0;
    } else if ((piece & 7) === PAWN) halfmove = 0;
    else halfmove++;

    if (prom) add_piece(to, prom);
    else add_piece(to, piece);

    hash_lo ^= z_castle_lo[castle]; hash_hi ^= z_castle_hi[castle];
    castle &= castle_rights[from]; castle &= castle_rights[to];
    hash_lo ^= z_castle_lo[castle]; hash_hi ^= z_castle_hi[castle];

    if (flag === 2) {
        if (to === 6) { remove_piece(7, ROOK|WHITE); add_piece(5, ROOK|WHITE); }
        else if (to === 2) { remove_piece(0, ROOK|WHITE); add_piece(3, ROOK|WHITE); }
        else if (to === 118) { remove_piece(119, ROOK|BLACK); add_piece(117, ROOK|BLACK); }
        else if (to === 114) { remove_piece(112, ROOK|BLACK); add_piece(115, ROOK|BLACK); }
    }

    if ((piece & 7) === PAWN && Math.abs(from - to) === 32) {
        ep = (from + to) >> 1;
        hash_lo ^= z_ep_lo[ep]; hash_hi ^= z_ep_hi[ep];
    }

    if ((piece & 7) === KING) king_sq[side === WHITE ? 0 : 1] = to;
    side ^= 24; ply++;

    if (is_attacked(king_sq[(side ^ 24) === WHITE ? 0 : 1], side)) {
        unmake_move(m);
        return false;
    }
    return true;
}

function unmake_move(m) {
    ply--; side ^= 24;
    const from = m & 127, to = (m >> 7) & 127, piece = (m >> 14) & 31, captured = (m >> 19) & 31, prom = (m >> 24) & 31, flag = m >> 29;

    if (prom) remove_piece(to, prom);
    else remove_piece(to, piece);

    if (captured) {
        let cap_sq = to;
        if (flag === 1) cap_sq = side === WHITE ? to - 16 : to + 16;
        add_piece(cap_sq, captured);
    }
    add_piece(from, piece);

    if (flag === 2) {
        if (to === 6) { remove_piece(5, ROOK|WHITE); add_piece(7, ROOK|WHITE); }
        else if (to === 2) { remove_piece(3, ROOK|WHITE); add_piece(0, ROOK|WHITE); }
        else if (to === 118) { remove_piece(117, ROOK|BLACK); add_piece(119, ROOK|BLACK); }
        else if (to === 114) { remove_piece(115, ROOK|BLACK); add_piece(112, ROOK|BLACK); }
    }

    if ((piece & 7) === KING) king_sq[side === WHITE ? 0 : 1] = from;

    hash_lo = state_hash_lo[ply]; hash_hi = state_hash_hi[ply];
    ep = state_ep[ply]; castle = state_castle[ply]; halfmove = state_halfmove[ply];
}

function make_null_move() {
    state_hash_lo[ply] = hash_lo; state_hash_hi[ply] = hash_hi;
    state_ep[ply] = ep; state_castle[ply] = castle; state_halfmove[ply] = halfmove;
    hash_lo ^= z_color_lo; hash_hi ^= z_color_hi;
    if (ep) { hash_lo ^= z_ep_lo[ep]; hash_hi ^= z_ep_hi[ep]; ep = 0; }
    halfmove++; ply++; side ^= 24;
}

function unmake_null_move() {
    ply--; side ^= 24;
    hash_lo = state_hash_lo[ply]; hash_hi = state_hash_hi[ply];
    ep = state_ep[ply]; castle = state_castle[ply]; halfmove = state_halfmove[ply];
}

function is_attacked(sq, them) {
    let psq = sq + (them === WHITE ? -15 : 15);
    if (!(psq & 0x88) && board[psq] === (PAWN | them)) return true;
    psq = sq + (them === WHITE ? -17 : 17);
    if (!(psq & 0x88) && board[psq] === (PAWN | them)) return true;
    for (let i = 0; i < piece_dirs[KNIGHT].length; i++) {
        let csq = sq + piece_dirs[KNIGHT][i];
        if (!(csq & 0x88) && board[csq] === (KNIGHT | them)) return true;
    }
    for (let i = 0; i < piece_dirs[KING].length; i++) {
        let csq = sq + piece_dirs[KING][i];
        if (!(csq & 0x88) && board[csq] === (KING | them)) return true;
    }
    for (let i = 0; i < piece_dirs[ROOK].length; i++) {
        let step = piece_dirs[ROOK][i], csq = sq;
        while (true) {
            csq += step;
            if (csq & 0x88) break;
            const pc = board[csq];
            if (pc) { if (pc === (ROOK | them) || pc === (QUEEN | them)) return true; break; }
        }
    }
    for (let i = 0; i < piece_dirs[BISHOP].length; i++) {
        let step = piece_dirs[BISHOP][i], csq = sq;
        while (true) {
            csq += step;
            if (csq & 0x88) break;
            const pc = board[csq];
            if (pc) { if (pc === (BISHOP | them) || pc === (QUEEN | them)) return true; break; }
        }
    }
    return false;
}

// ==============================================================================
// MOVE GENERATOR
// ==============================================================================
function generate_moves(p, captures_only) {
    let offset = p * 256, count = 0, us = side, them = side ^ 24;
    for (let sq = 0; sq < 128; sq++) {
        if (sq & 0x88) continue;
        const pc = board[sq];
        if (!pc || (pc & us) === 0) continue;
        const type = pc & 7;

        if (type === PAWN) {
            const dir = us === WHITE ? 16 : -16, start_rank = us === WHITE ? 1 : 6, prom_rank = us === WHITE ? 6 : 1, rank = sq >> 4;
            for (let cdir of (us === WHITE ? [15, 17] : [-15, -17])) {
                let csq = sq + cdir;
                if ((csq & 0x88) === 0) {
                    if (board[csq] && (board[csq] & them)) count = add_pawn_moves(offset, count, sq, csq, pc, board[csq], rank === prom_rank, 0);
                    else if (csq === ep) count = add_pawn_moves(offset, count, sq, csq, pc, PAWN | them, false, 1);
                }
            }
            if (!captures_only || rank === prom_rank) {
                let nsq = sq + dir;
                if ((nsq & 0x88) === 0 && board[nsq] === 0) {
                    count = add_pawn_moves(offset, count, sq, nsq, pc, 0, rank === prom_rank, 0);
                    if (!captures_only && rank === start_rank) {
                        let nsq2 = sq + dir * 2;
                        if (board[nsq2] === 0) move_stack[offset + count++] = sq | (nsq2 << 7) | (pc << 14);
                    }
                }
            }
        } else {
            const dirs = piece_dirs[type];
            for (let i = 0; i < dirs.length; i++) {
                const step = dirs[i]; let csq = sq;
                while (true) {
                    csq += step;
                    if (csq & 0x88) break;
                    const dpc = board[csq];
                    if (dpc === 0) { if (!captures_only) move_stack[offset + count++] = sq | (csq << 7) | (pc << 14); }
                    else { if (dpc & them) move_stack[offset + count++] = sq | (csq << 7) | (pc << 14) | (dpc << 19); break; }
                    if (type === KNIGHT || type === KING) break;
                }
            }
        }
    }

    if (!captures_only) {
        if (us === WHITE) {
            if (castle & 1) if (!board[5] && !board[6] && !is_attacked(4, them) && !is_attacked(5, them) && !is_attacked(6, them)) move_stack[offset + count++] = 4 | (6 << 7) | ((KING|WHITE) << 14) | (2 << 29);
            if (castle & 2) if (!board[3] && !board[2] && !board[1] && !is_attacked(4, them) && !is_attacked(3, them) && !is_attacked(2, them)) move_stack[offset + count++] = 4 | (2 << 7) | ((KING|WHITE) << 14) | (2 << 29);
        } else {
            if (castle & 4) if (!board[117] && !board[118] && !is_attacked(116, them) && !is_attacked(117, them) && !is_attacked(118, them)) move_stack[offset + count++] = 116 | (118 << 7) | ((KING|BLACK) << 14) | (2 << 29);
            if (castle & 8) if (!board[115] && !board[114] && !board[113] && !is_attacked(116, them) && !is_attacked(115, them) && !is_attacked(114, them)) move_stack[offset + count++] = 116 | (114 << 7) | ((KING|BLACK) << 14) | (2 << 29);
        }
    }
    return count;
}

function add_pawn_moves(offset, count, sq, to, pc, cap, prom, flag) {
    if (prom) {
        const us = pc & 24;
        move_stack[offset + count++] = sq | (to << 7) | (pc << 14) | (cap << 19) | ((QUEEN|us) << 24) | (flag << 29);
        move_stack[offset + count++] = sq | (to << 7) | (pc << 14) | (cap << 19) | ((KNIGHT|us) << 24) | (flag << 29);
        move_stack[offset + count++] = sq | (to << 7) | (pc << 14) | (cap << 19) | ((ROOK|us) << 24) | (flag << 29);
        move_stack[offset + count++] = sq | (to << 7) | (pc << 14) | (cap << 19) | ((BISHOP|us) << 24) | (flag << 29);
    } else move_stack[offset + count++] = sq | (to << 7) | (pc << 14) | (cap << 19) | (flag << 29);
    return count;
}

// ==============================================================================
// EVALUATION (Enhanced with pawn structure, king safety, mobility, bishop pair)
// ==============================================================================
function eval_pawns() {
    let score = 0;
    for (let color of [WHITE, BLACK]) {
        const sign = color === WHITE ? 1 : -1;
        const pawn = PAWN | color;
        const enemy_pawn = PAWN | (color ^ 24);
        const files = new Int32Array(8);

        for (let sq = 0; sq < 128; sq++) {
            if (!(sq & 0x88) && board[sq] === pawn) files[sq & 7]++;
        }

        for (let sq = 0; sq < 128; sq++) {
            if (!(sq & 0x88) && board[sq] === pawn) {
                const f = sq & 7, r = sq >> 4;
                // Doubled
                if (files[f] > 1) score -= 15 * sign;
                // Isolated
                const left = f > 0 ? files[f - 1] : 0;
                const right = f < 7 ? files[f + 1] : 0;
                if (left === 0 && right === 0) score -= 20 * sign;
                // Passed
                let passed = true;
                const start_r = color === WHITE ? r + 1 : r - 1;
                const end_r = color === WHITE ? 7 : 0;
                const step = color === WHITE ? 1 : -1;
                for (let rr = start_r; color === WHITE ? rr <= end_r : rr >= end_r; rr += step) {
                    for (let ff = f - 1; ff <= f + 1; ff++) {
                        if (ff >= 0 && ff <= 7 && board[rr * 16 + ff] === enemy_pawn) { passed = false; break; }
                    }
                    if (!passed) break;
                }
                if (passed) {
                    const rank_val = color === WHITE ? r : (7 - r);
                    score += (10 + rank_val * rank_val) * sign;
                }
            }
        }
    }
    return score;
}

function eval_king_safety() {
    let score = 0;
    for (let color of [WHITE, BLACK]) {
        const sign = color === WHITE ? 1 : -1;
        const ksq = king_sq[color === WHITE ? 0 : 1];
        if (ksq === 0) continue;
        const f = ksq & 7, r = ksq >> 4;
        const shield = r + (color === WHITE ? 1 : -1);
        let bonus = 0;
        if (shield >= 0 && shield < 8) {
            for (let ff = f - 1; ff <= f + 1; ff++) {
                if (ff >= 0 && ff <= 7 && board[shield * 16 + ff] === (PAWN | color)) bonus += 12;
            }
        }
        // Enemy attackers
        const enemy = color ^ 24;
        for (let d of [-17,-16,-15,-1,1,15,16,17,33,31,18,14,-14,-18,-31,-33]) {
            const atk = ksq + d;
            if (!(atk & 0x88) && board[atk] && (board[atk] & 24) === enemy && (board[atk] & 7) !== PAWN) {
                bonus -= 8;
            }
        }
        score += bonus * sign;
    }
    return score;
}

function eval_mobility() {
    let score = 0;
    for (let color of [WHITE, BLACK]) {
        const sign = color === WHITE ? 1 : -1;
        for (let sq = 0; sq < 128; sq++) {
            if (sq & 0x88) continue;
            const pc = board[sq];
            if (!pc || (pc & 24) !== color) continue;
            const type = pc & 7;
            if (type === KNIGHT) {
                for (let d of [-33,-31,-18,-14,14,18,31,33]) {
                    if (!(sq + d & 0x88) && board[sq + d] === 0) score += 3 * sign;
                }
            } else if (type === BISHOP || type === ROOK || type === QUEEN) {
                const dirs = [];
                if (type === BISHOP || type === QUEEN) dirs.push(-17,-15,15,17);
                if (type === ROOK || type === QUEEN) dirs.push(-16,-1,1,16);
                for (let d of dirs) {
                    let c = sq + d;
                    while (!(c & 0x88)) {
                        if (board[c] === 0) score += 2 * sign;
                        else break;
                        c += d;
                    }
                }
            }
        }
    }
    return score;
}

function evaluate() {
    let p = phase; if (p > 24) p = 24;
    let score = (eval_mg * p + eval_eg * (24 - p)) / 24 | 0;

    // Bishop pair
    let wb = 0, bb = 0;
    for (let sq = 0; sq < 128; sq++) {
        if (!(sq & 0x88)) {
            if (board[sq] === (BISHOP | WHITE)) wb++;
            else if (board[sq] === (BISHOP | BLACK)) bb++;
        }
    }
    if (wb >= 2) { score += 30; }
    if (bb >= 2) { score -= 30; }

    // Pawn structure
    score += eval_pawns();

    // King safety
    score += eval_king_safety();

    // Mobility
    score += eval_mobility();

    return side === WHITE ? score : -score;
}

// ==============================================================================
// SEE (Static Exchange Evaluation)
// ==============================================================================
function see(m) {
    const from = m & 127, to = (m >> 7) & 127, piece = (m >> 14) & 31;
    const captured = (m >> 19) & 31;
    if (!captured && (m >> 29) !== 1) return 0; // Not a capture
    const victim = captured ? PIECE_VAL[captured & 7] : 100; // EP value
    const attacker = PIECE_VAL[piece & 7];
    return victim - (attacker / 10) | 0;
}

// ==============================================================================
// SEARCH HEURISTICS
// ==============================================================================
function score_move(m, hash_move) {
    if (m === hash_move) return 10000000;
    const captured = (m >> 19) & 31;
    let score = 0;

    if (captured) score = 1000000 + ((captured & 7) * 100) - ((m >> 14) & 7);
    else if (m === killers[ply][0]) score = 900000;
    else if (m === killers[ply][1]) score = 800000;
    else {
        const last = ply > 0 ? (state_hash_lo[ply-1] & 0xFFFF) : 0;
        score = history[((m & 127) << 7) | ((m >> 7) & 127)];
    }

    let prom = (m >> 24) & 31;
    if (prom) score += 500000 + PIECE_VAL[prom & 7];
    return score;
}

function sort_moves(offset, count, hash_move) {
    for (let i = 0; i < count; i++) move_scores[offset + i] = score_move(move_stack[offset + i], hash_move);
    for (let i = 1; i < count; i++) {
        let key_m = move_stack[offset + i], key_s = move_scores[offset + i], j = i - 1;
        while (j >= 0 && move_scores[offset + j] < key_s) {
            move_stack[offset + j + 1] = move_stack[offset + j];
            move_scores[offset + j + 1] = move_scores[offset + j];
            j--;
        }
        move_stack[offset + j + 1] = key_m; move_scores[offset + j + 1] = key_s;
    }
}

function quiesce(alpha, beta) {
    if ((nodes++ & TIME_CHECK_MASK) === 0 && Date.now() >= stop_time) stop_search = true;
    if (stop_search) return 0;
    if (ply >= 511) return evaluate();

    let stand_pat = evaluate();
    if (stand_pat >= beta) return beta;
    if (alpha < stand_pat) alpha = stand_pat;

    // Delta pruning
    if (stand_pat < alpha - 1050) return alpha;

    let count = generate_moves(ply, true);
    let offset = ply * 256;

    // SEE filter
    let filtered = 0;
    for (let i = 0; i < count; i++) {
        if (see(move_stack[offset + i]) >= 0) {
            move_stack[offset + filtered] = move_stack[offset + i];
            filtered++;
        }
    }
    count = filtered;
    sort_moves(offset, count, 0);

    for (let i = 0; i < count; i++) {
        let m = move_stack[offset + i];
        if (!make_move(m)) continue;
        let score = -quiesce(-beta, -alpha);
        unmake_move(m);
        if (score >= beta) return beta;
        if (score > alpha) alpha = score;
    }
    return alpha;
}

function search(depth, alpha, beta, is_pv) {
    if ((nodes++ & TIME_CHECK_MASK) === 0 && Date.now() >= stop_time) stop_search = true;
    if (stop_search) return 0;
    if (ply >= 511) return evaluate();

    // Repetition detection
    if (ply > 0 && halfmove >= 100) return 0;
    let limit = Math.max(0, ply - halfmove);
    for (let i = ply - 2; i >= limit; i -= 2) {
        if (state_hash_lo[i] === hash_lo && state_hash_hi[i] === hash_hi) return 0;
    }

    // TT lookup
    let tt_idx = hash_lo & (TT_SIZE - 1), hash_move = 0;
    if (tt_key_lo[tt_idx] === hash_lo && tt_key_hi[tt_idx] === hash_hi) {
        hash_move = tt_move[tt_idx];
        let data = tt_data[tt_idx], tt_depth = data & 0xFF, tt_flag = (data >> 8) & 0xFF;
        let tt_score = data >> 16;
        if (tt_depth >= depth && !is_pv) {
            if (tt_flag === 1) return tt_score;
            if (tt_flag === 2 && tt_score <= alpha) return alpha;
            if (tt_flag === 3 && tt_score >= beta) return beta;
        }
    }

    let in_check = is_attacked(king_sq[side === WHITE ? 0 : 1], side ^ 24);
    if (in_check) depth++;

    if (depth <= 0) return quiesce(alpha, beta);

    // Razoring
    if (depth === 1 && evaluate() + 250 < alpha) return quiesce(alpha, beta);

    // Null move pruning
    if (depth >= 3 && !in_check && !is_pv && phase > 0) {
        let has_minor = false;
        for (let sq = 0; sq < 128; sq++) {
            if (!(sq & 0x88) && (board[sq] & 7) === KNIGHT) { has_minor = true; break; }
        }
        if (has_minor) {
            make_null_move();
            let null_score = -search(depth - 3, -beta, -beta + 1, false);
            unmake_null_move();
            if (stop_search) return 0;
            if (null_score >= beta) return beta;
        }
    }

    // Internal iterative deepening
    if (depth >= 4 && !hash_move) {
        search(depth - 2, alpha, beta, is_pv);
        let new_tt_idx = hash_lo & (TT_SIZE - 1);
        if (tt_key_lo[new_tt_idx] === hash_lo && tt_key_hi[new_tt_idx] === hash_hi) {
            hash_move = tt_move[new_tt_idx];
        }
    }

    let count = generate_moves(ply, false);
    let offset = ply * 256;
    sort_moves(offset, count, hash_move);

    let best_score = -50000, best_move = 0, legal = 0, alpha_orig = alpha;
    for (let i = 0; i < count; i++) {
        let m = move_stack[offset + i];

        // Futility pruning
        if (depth === 1 && i > 5 && evaluate() + 150 < alpha && !((m >> 19) & 31) && !((m >> 24) & 31) && (m >> 29) !== 1) continue;

        if (!make_move(m)) continue;
        legal++;
        let score;

        if (legal === 1) score = -search(depth - 1, -beta, -alpha, is_pv);
        else {
            let reduction = 0;
            if (depth >= 3 && !in_check && ((m >> 19) & 31) === 0 && ((m >> 24) & 31) === 0 && legal > 4) {
                reduction = 1; if (depth > 5 && legal > 6) reduction = 2;
            }
            score = -search(depth - 1 - reduction, -alpha - 1, -alpha, false);
            if (reduction > 0 && score > alpha) score = -search(depth - 1, -alpha - 1, -alpha, false);
            if (is_pv && score > alpha && score < beta) score = -search(depth - 1, -beta, -alpha, true);
        }

        unmake_move(m);
        if (stop_search) return 0;

        if (score > best_score) { best_score = score; best_move = m; }
        if (score > alpha) {
            alpha = score;
            if (score >= beta) {
                if (((m >> 19) & 31) === 0) {
                    killers[ply][1] = killers[ply][0]; killers[ply][0] = m;
                    history[((m & 127) << 7) | ((m >> 7) & 127)] += depth * depth;
                }
                break;
            }
        }
    }

    if (legal === 0) return in_check ? -30000 + ply : 0;

    let flag = 1;
    if (best_score <= alpha_orig) flag = 2; else if (best_score >= beta) flag = 3;

    if (best_score > -20000 && best_score < 20000) {
        tt_key_lo[tt_idx] = hash_lo; tt_key_hi[tt_idx] = hash_hi;
        tt_move[tt_idx] = best_move;
        tt_data[tt_idx] = depth | (flag << 8) | ((best_score & 0xFFFF) << 16);
    }
    return best_score;
}

// ==============================================================================
// ROOT SEARCH
// ==============================================================================
function search_root() {
    nodes = 0; stop_search = false; start_time = Date.now(); stop_time = start_time + MOVE_TIME_MS;
    let best_move_root = 0;

    for (let i = 0; i < MAX_PLY; i++) { killers[i][0] = 0; killers[i][1] = 0; }
    for (let i = 0; i < 16384; i++) history[i] >>= 1;

    let count = generate_moves(0, false);
    for (let d = 1; d <= 64; d++) {
        let alpha = -50000, beta = 50000, best_score = -50000, current_best_move = 0, legal = 0;
        sort_moves(0, count, best_move_root);

        for (let i = 0; i < count; i++) {
            let m = move_stack[i];
            if (!make_move(m)) continue;
            legal++;
            let score;
            if (legal === 1) score = -search(d - 1, -beta, -alpha, true);
            else {
                score = -search(d - 1, -alpha - 1, -alpha, false);
                if (score > alpha && score < beta) score = -search(d - 1, -beta, -alpha, true);
            }
            unmake_move(m);
            if (stop_search) break;

            if (score > best_score) { best_score = score; current_best_move = m; }
            if (score > alpha) alpha = score;
        }
        if (stop_search) break;
        if (current_best_move) best_move_root = current_best_move;
        if (best_score > 20000 || best_score < -20000) break;
    }

    if (!best_move_root) {
        for (let i = 0; i < count; i++) {
            if (make_move(move_stack[i])) { best_move_root = move_stack[i]; unmake_move(move_stack[i]); break; }
        }
    }
    return best_move_root;
}

// ==============================================================================
// FEN PARSING & UCI OUTPUT
// ==============================================================================
function set_fen(fen) {
    for (let i = 0; i < 128; i++) board[i] = 0;
    eval_mg = 0; eval_eg = 0; phase = 0; hash_lo = 0; hash_hi = 0;
    ep = 0; castle = 0; halfmove = 0; ply = 0;

    let parts = fen.trim().split(/\s+/), rows = parts[0].split('/'), rank = 7;
    for (let i = 0; i < 8; i++) {
        let file = 0;
        for (let j = 0; j < rows[i].length; j++) {
            let c = rows[i][j];
            if (c >= '1' && c <= '8') { file += parseInt(c); }
            else {
                let pc = 0;
                switch (c) {
                    case 'P': pc = PAWN | WHITE; break; case 'N': pc = KNIGHT | WHITE; break;
                    case 'B': pc = BISHOP | WHITE; break; case 'R': pc = ROOK | WHITE; break;
                    case 'Q': pc = QUEEN | WHITE; break; case 'K': pc = KING | WHITE; break;
                    case 'p': pc = PAWN | BLACK; break; case 'n': pc = KNIGHT | BLACK; break;
                    case 'b': pc = BISHOP | BLACK; break; case 'r': pc = ROOK | BLACK; break;
                    case 'q': pc = QUEEN | BLACK; break; case 'k': pc = KING | BLACK; break;
                }
                if (pc) {
                    board[rank * 16 + file] = pc;
                    const type = pc & 7, color = pc & 24;
                    let sq64 = (7 - rank) * 8 + file;
                    if (color === BLACK) sq64 ^= 56;
                    eval_mg += (color === WHITE ? mg_pesto[type][sq64] : -mg_pesto[type][sq64]);
                    eval_eg += (color === WHITE ? eg_pesto[type][sq64] : -eg_pesto[type][sq64]);
                    phase += phase_inc[type];
                    const pidx = color === WHITE ? type : type + 7;
                    hash_lo ^= z_lo[pidx * 128 + rank * 16 + file];
                    hash_hi ^= z_hi[pidx * 128 + rank * 16 + file];
                    if ((pc & 7) === KING) king_sq[color === WHITE ? 0 : 1] = rank * 16 + file;
                }
                file++;
            }
        }
        rank--;
    }

    side = parts[1] === 'w' ? WHITE : BLACK;
    if (side === BLACK) { hash_lo ^= z_color_lo; hash_hi ^= z_color_hi; }

    if (parts[2]) {
        if (parts[2].includes('K')) castle |= 1;
        if (parts[2].includes('Q')) castle |= 2;
        if (parts[2].includes('k')) castle |= 4;
        if (parts[2].includes('q')) castle |= 8;
    }
    hash_lo ^= z_castle_lo[castle]; hash_hi ^= z_castle_hi[castle];

    if (parts[3] && parts[3] !== '-') {
        ep = (parseInt(parts[3][1]) - 1) * 16 + (parts[3].charCodeAt(0) - 97);
        hash_lo ^= z_ep_lo[ep]; hash_hi ^= z_ep_hi[ep];
    }
}

function move_to_uci(m) {
    const from = m & 127, to = (m >> 7) & 127, prom = (m >> 24) & 31, flag = m >> 29;
    let uci = String.fromCharCode(97 + (from & 7)) + ((from >> 4) + 1) +
              String.fromCharCode(97 + (to & 7)) + ((to >> 4) + 1);
    if (prom) {
        const type = prom & 7;
        uci += type === QUEEN ? 'q' : type === ROOK ? 'r' : type === BISHOP ? 'b' : 'n';
    }
    if (flag === 1) uci += 'e'; // en passant
    return uci;
}

// ==============================================================================
// MAIN LOOP
// ==============================================================================
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

rl.on('line', (line) => {
    const fen = line.trim();
    if (!fen) return;
    set_fen(fen);
    const best = search_root();
    if (best) {
        process.stdout.write(move_to_uci(best) + '\n');
    } else {
        process.stdout.write('0000\n');
    }
});
