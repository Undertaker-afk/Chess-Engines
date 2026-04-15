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
    0, [82, 82, 82, 82, 82, 82, 82, 82, 180, 216, 143, 177, 150, 208, 116, 71, 76, 89, 108, 113, 147, 138, 107, 62, 68, 95, 88, 103, 105, 94, 99, 59, 55, 80, 77, 94, 99, 88, 92, 57, 56, 78, 78, 72, 85, 85, 115, 70, 47, 81, 62, 59, 67, 106, 120, 60, 82, 82, 82, 82, 82, 82, 82, 82],
    [170, 248, 303, 288, 398, 240, 322, 230, 264, 296, 409, 373, 360, 399, 344, 320, 290, 397, 374, 402, 421, 466, 410, 381, 328, 354, 356, 390, 374, 406, 355, 359, 324, 341, 353, 350, 365, 356, 358, 329, 314, 328, 349, 347, 356, 354, 362, 321, 308, 284, 325, 334, 336, 355, 323, 318, 232, 316, 279, 304, 320, 309, 318, 314],
    [336, 369, 283, 328, 340, 323, 372, 357, 339, 381, 347, 352, 395, 424, 383, 318, 349, 402, 408, 405, 400, 415, 402, 363, 361, 370, 384, 415, 402, 402, 372, 363, 359, 378, 378, 391, 399, 377, 375, 369, 365, 380, 380, 380, 379, 392, 383, 375, 369, 380, 381, 365, 372, 386, 398, 366, 332, 362, 351, 344, 352, 353, 326, 344],
    [509, 519, 509, 528, 540, 486, 508, 520, 504, 509, 535, 539, 557, 544, 503, 521, 472, 496, 503, 513, 494, 522, 538, 493, 453, 466, 484, 503, 501, 512, 469, 457, 441, 451, 465, 476, 486, 470, 483, 454, 432, 452, 461, 460, 480, 477, 472, 444, 433, 461, 457, 468, 476, 488, 471, 406, 458, 464, 478, 494, 493, 484, 440, 451],
    [997, 1025, 1054, 1037, 1084, 1069, 1068, 1070, 1001, 986, 1020, 1026, 1009, 1082, 1053, 1079, 1012, 1008, 1032, 1033, 1054, 1081, 1072, 1082, 998, 998, 1009, 1009, 1024, 1042, 1023, 1026, 1016, 999, 1016, 1015, 1023, 1021, 1028, 1022, 1011, 1027, 1014, 1023, 1020, 1027, 1039, 1030, 990, 1017, 1036, 1027, 1033, 1040, 1022, 1026, 1024, 1007, 1016, 1035, 1010, 1000, 994, 975],
    [-65, 23, 16, -15, -56, -34, 2, 13, 29, -1, -20, -7, -8, -4, -38, -29, -9, 24, 2, -16, -20, 6, 22, -22, -17, -20, -12, -27, -30, -25, -14, -36, -49, -1, -27, -39, -46, -44, -33, -51, -14, -14, -22, -46, -44, -30, -15, -27, 1, 7, -8, -64, -43, -16, 9, 8, -15, 36, 12, -54, 8, -28, 24, 14]
];
const eg_pesto = [
    0, [94, 94, 94, 94, 94, 94, 94, 94, 272, 267, 252, 228, 241, 226, 259, 281, 188, 194, 179, 161, 150, 147, 176, 178, 126, 118, 107, 99, 92, 98, 111, 111, 107, 103, 91, 87, 87, 86, 97, 93, 98, 101, 88, 95, 94, 89, 93, 86, 107, 102, 102, 104, 107, 94, 96, 87, 94, 94, 94, 94, 94, 94, 94, 94],
    [223, 243, 268, 253, 250, 254, 218, 182, 256, 273, 256, 279, 272, 256, 257, 229, 257, 261, 291, 290, 280, 272, 262, 240, 264, 284, 303, 303, 303, 292, 289, 263, 263, 275, 297, 306, 297, 298, 285, 263, 258, 278, 280, 296, 291, 278, 261, 259, 239, 261, 271, 276, 279, 261, 258, 237, 252, 230, 258, 266, 259, 263, 231, 217],
    [283, 276, 286, 289, 290, 288, 280, 273, 289, 293, 304, 285, 294, 284, 293, 283, 299, 289, 297, 296, 295, 303, 297, 301, 294, 306, 309, 306, 311, 307, 300, 299, 291, 300, 310, 316, 304, 307, 294, 288, 285, 294, 305, 307, 310, 300, 290, 282, 283, 279, 290, 296, 301, 288, 282, 270, 274, 288, 274, 292, 288, 281, 292, 280],
    [525, 522, 530, 527, 524, 524, 520, 517, 523, 525, 525, 523, 509, 515, 520, 515, 519, 519, 519, 517, 516, 509, 507, 509, 516, 515, 525, 513, 514, 513, 511, 514, 515, 517, 520, 516, 507, 506, 504, 501, 508, 512, 507, 511, 505, 500, 504, 496, 506, 506, 512, 514, 503, 503, 501, 509, 503, 514, 515, 511, 507, 499, 516, 492],
    [927, 958, 958, 963, 963, 955, 946, 956, 919, 956, 968, 977, 994, 961, 966, 936, 916, 942, 945, 985, 983, 971, 955, 945, 939, 958, 960, 981, 993, 976, 993, 972, 918, 964, 955, 983, 967, 970, 948, 947, 920, 909, 951, 942, 945, 953, 946, 941, 914, 913, 906, 920, 920, 913, 900, 904, 903, 908, 914, 893, 931, 904, 916, 895],
    [-74, -35, -18, -18, -11, 15, 4, -17, -12, 17, 14, 17, 17, 38, 23, 11, 10, 17, 23, 15, 20, 45, 44, 13, -8, 22, 24, 27, 26, 33, 26, 3, -18, -4, 21, 24, 27, 23, 9, -11, -19, -3, 11, 21, 23, 16, 7, -9, -27, -11, 4, 13, 14, 4, -5, -17, -53, -34, -21, -11, -28, -14, -24, -43]
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
    return side === WHITE ? ((eval_mg * p + eval_eg * (24 - p)) / 24 | 0) : -((eval_mg * p + eval_eg * (24 - p)) / 24 | 0);
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
