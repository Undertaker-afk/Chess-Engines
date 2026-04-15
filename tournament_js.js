#!/usr/bin/env node
/**
 * Trinity JS Tournament Harness
 * 
 * Runs Trinity JS engines against each other or against Stockfish.
 * Supports:
 * - Multiple engines in round-robin
 * - Configurable time control
 * - Live leaderboard
 * - Endgame PGN saving
 * - Stockfish integration via UCI
 *
 * Usage:
 *   node tournament_js.js --engines "Trinity-Alpha-0.1.js,Trinity-1.1.js" --games 2 --movetime 3000
 *   node tournament_js.js --engines "Trinity-1.1.js,stockfish" --games 4 --movetime 5000 --stockfish-path "stockfish.exe"
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// ==============================================================================
// CONFIG
// ==============================================================================
const DEFAULT_CONFIG = {
    engines: [],
    gamesPerPair: 2,
    moveTimeMs: 3000,
    maxConcurrent: 2,
    stockfishPath: 'stockfish',
    outputDir: 'tournament_js',
};

function parseArgs() {
    const config = { ...DEFAULT_CONFIG };
    const args = process.argv.slice(2);
    for (let i = 0; i < args.length; i++) {
        switch (args[i]) {
            case '--engines':
                config.engines = args[++i].split(',').map(s => s.trim());
                break;
            case '--games':
                config.gamesPerPair = parseInt(args[++i]);
                break;
            case '--movetime':
                config.moveTimeMs = parseInt(args[++i]);
                break;
            case '--concurrent':
                config.maxConcurrent = parseInt(args[++i]);
                break;
            case '--stockfish-path':
                config.stockfishPath = args[++i];
                break;
            case '--output':
                config.outputDir = args[++i];
                break;
            case '--help':
                console.log('Usage: node tournament_js.js --engines "file1.js,file2.js" [--games N] [--movetime MS] [--concurrent N] [--stockfish-path PATH] [--output DIR]');
                process.exit(0);
        }
    }
    return config;
}

// ==============================================================================
// ENGINE WRAPPER
// ==============================================================================
class Engine {
    constructor(name, scriptPath, isStockfish = false, stockfishPath = null) {
        this.name = name;
        this.scriptPath = scriptPath;
        this.isStockfish = isStockfish;
        this.stockfishPath = stockfishPath;
        this.elo = 1500;
        this.games = 0;
        this.score = 0;
        this.wins = 0;
        this.draws = 0;
        this.losses = 0;
        this.totalTime = 0;
        this.moveCount = 0;
        this.proc = null;
    }

    avgResponseTime() {
        return this.moveCount > 0 ? (this.totalTime / this.moveCount).toFixed(0) : '0';
    }

    start() {
        if (this.proc) return;
        if (this.isStockfish) {
            this.proc = spawn(this.stockfishPath, [], { stdio: ['pipe', 'pipe', 'pipe'] });
        } else {
            this.proc = spawn('node', [this.scriptPath, '--movetime', String(process.env.MOVE_TIME || 3000)], { stdio: ['pipe', 'pipe', 'pipe'] });
        }
        this.proc.stderr.on('data', () => {}); // Suppress stderr
    }

    async getMove(fen, timeoutMs) {
        if (!this.proc) return '0000';
        const start = Date.now();

        return new Promise((resolve) => {
            let resolved = false;
            const timer = setTimeout(() => {
                if (!resolved) { resolved = true; resolve('0000'); }
            }, timeoutMs);

            const onData = (data) => {
                const line = data.toString().trim();
                if (this.isStockfish) {
                    if (line.startsWith('bestmove')) {
                        const move = line.split(' ')[1];
                        clearTimeout(timer);
                        this.proc.stdout.off('data', onData);
                        if (!resolved) { resolved = true; resolve(move || '0000'); }
                    }
                } else {
                    if (line && line.length >= 4) {
                        clearTimeout(timer);
                        this.proc.stdout.off('data', onData);
                        if (!resolved) { resolved = true; resolve(line); }
                    }
                }
            };

            this.proc.stdout.on('data', onData);

            if (this.isStockfish) {
                this.proc.stdin.write(`position fen ${fen}\ngo movetime ${timeoutMs}\n`);
            } else {
                this.proc.stdin.write(fen + '\n');
            }

            this.proc.stdin.uncork();
        }).then(move => {
            const elapsed = Date.now() - start;
            this.totalTime += elapsed;
            this.moveCount++;
            return move;
        });
    }

    stop() {
        if (this.proc) {
            if (this.isStockfish) {
                this.proc.stdin.write('quit\n');
            }
            this.proc.kill();
            this.proc = null;
        }
    }
}

// ==============================================================================
// ELO UPDATE
// ==============================================================================
function updateElo(eloA, eloB, scoreA, k = 32) {
    const expected = 1 / (1 + Math.pow(10, (eloB - eloA) / 400));
    return [
        eloA + k * (scoreA - expected),
        eloB + k * ((1 - scoreA) - (1 - expected))
    ];
}

// ==============================================================================
// GAME PLAY
// ==============================================================================
async function validateMove(fen, uci) {
    // Use python chess library for reliable move validation
    return new Promise((resolve) => {
        const { spawn } = require('child_process');
        const py = spawn('python', ['-c', `
import chess, sys
fen = sys.argv[1]
uci = sys.argv[2]
b = chess.Board(fen)
try:
    m = chess.Move.from_uci(uci)
    print('ok' if m in b.legal_moves else 'illegal')
except:
    print('bad')
`, fen, uci], { stdio: ['pipe', 'pipe', 'pipe'] });
        let out = '';
        py.stdout.on('data', d => out += d.toString());
        py.on('close', () => resolve(out.trim()));
        setTimeout(() => { py.kill(); resolve('timeout'); }, 3000);
    });
}

async function playGame(white, black, gameId, config) {
    white.start();
    black.start();

    // Use python chess for game state management
    const { spawn } = require('child_process');
    const moves = [];
    let result = '*';
    let endReason = 'normal';
    let currentFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    const timeout = config.moveTimeMs + 2000;

    while (true) {
        // Check game state via python
        const state = await new Promise((resolve) => {
            const py = spawn('python', ['-c', `
import chess, sys, json
fen = sys.argv[1]
b = chess.Board(fen)
print(json.dumps({
    'over': b.is_game_over(),
    'result': b.result(),
    'turn': 'w' if b.turn else 'b'
}))
`, currentFen], { stdio: ['pipe', 'pipe', 'pipe'] });
            let out = '';
            py.stdout.on('data', d => out += d.toString());
            py.on('close', () => { try { resolve(JSON.parse(out)); } catch { resolve(null); } });
            setTimeout(() => { py.kill(); resolve(null); }, 3000);
        });

        if (!state || state.over) {
            result = state ? state.result : '1/2-1/2';
            endReason = 'normal';
            break;
        }

        const current = state.turn === 'w' ? white : black;
        const uci = await current.getMove(currentFen, timeout);

        if (!uci || uci === '0000') {
            result = state.turn === 'w' ? '0-1' : '1-0';
            endReason = `forfeit: ${current.name} timeout/empty`;
            break;
        }

        const valid = await validateMove(currentFen, uci);
        if (valid !== 'ok') {
            result = state.turn === 'w' ? '0-1' : '1-0';
            endReason = `forfeit: ${current.name} invalid move ${uci}`;
            break;
        }

        // Apply move via python to get new FEN
        const newFen = await new Promise((resolve) => {
            const py = spawn('python', ['-c', `
import chess, sys
fen = sys.argv[1]
uci = sys.argv[2]
b = chess.Board(fen)
m = chess.Move.from_uci(uci)
b.push(m)
print(b.fen())
`, currentFen, uci], { stdio: ['pipe', 'pipe', 'pipe'] });
            let out = '';
            py.stdout.on('data', d => out += d.toString());
            py.on('close', () => resolve(out.trim()));
            setTimeout(() => { py.kill(); resolve(null); }, 3000);
        });

        if (!newFen) {
            result = state.turn === 'w' ? '0-1' : '1-0';
            endReason = `error: failed to apply move ${uci}`;
            break;
        }

        moves.push(uci);
        currentFen = newFen;
    }

    // Update scores
    let whiteScore = 0, blackScore = 0;
    if (result === '1-0') { whiteScore = 1; }
    else if (result === '0-1') { blackScore = 1; }
    else { whiteScore = 0.5; blackScore = 0.5; }

    white.score += whiteScore;
    black.score += blackScore;
    white.games++;
    black.games++;
    if (whiteScore > blackScore) { white.wins++; black.losses++; }
    else if (whiteScore < blackScore) { black.wins++; white.losses++; }
    else { white.draws++; black.draws++; }

    const [newWhiteElo, newBlackElo] = updateElo(white.elo, black.elo, whiteScore);
    white.elo = newWhiteElo;
    black.elo = newBlackElo;

    return {
        gameId, white: white.name, black: black.name, result, endReason,
        moves, ply: moves.length
    };
}

// ==============================================================================
// LEADERBOARD
// ==============================================================================
function printLeaderboard(engines) {
    const sorted = [...engines].sort((a, b) => b.elo - a.elo);
    console.log('\n🏆 LIVE LEADERBOARD 🏆');
    console.log('─'.repeat(100));
    console.log(`${'Rank'.padEnd(4)} ${'Engine'.padEnd(25)} ${'Elo'.padEnd(7)} ${'Games'.padEnd(6)} ${'Score'.padEnd(6)} ${'Avg(ms)'.padEnd(9)} W/D/L`);
    console.log('─'.repeat(100));
    sorted.forEach((e, i) => {
        console.log(`${(i + 1).toString().padEnd(4)} ${e.name.padEnd(25)} ${e.elo.toFixed(0).padEnd(7)} ${e.games.toString().padEnd(6)} ${e.score.toFixed(1).padEnd(6)} ${e.avgResponseTime().padStart(8)} ${e.wins}/${e.draws}/${e.losses}`);
    });
    console.log('─'.repeat(100));
}

// ==============================================================================
// MAIN
// ==============================================================================
async function main() {
    const config = parseArgs();

    if (config.engines.length < 2) {
        console.error('Need at least 2 engines. Use --engines "file1.js,file2.js"');
        process.exit(1);
    }

    // Create output directory
    if (!fs.existsSync(config.outputDir)) {
        fs.mkdirSync(config.outputDir, { recursive: true });
    }

    // Initialize engines
    const engines = [];
    for (const eng of config.engines) {
        if (eng.toLowerCase() === 'stockfish') {
            engines.push(new Engine('Stockfish', null, true, config.stockfishPath));
        } else {
            const name = path.basename(eng, '.js');
            engines.push(new Engine(name, eng));
        }
    }

    console.log(`Found ${engines.length} engines: ${engines.map(e => e.name).join(', ')}`);
    console.log(`Games per pair: ${config.gamesPerPair}`);
    console.log(`Move time: ${config.moveTimeMs}ms`);
    console.log(`Max concurrent: ${config.maxConcurrent}`);

    // Generate matches
    const matches = [];
    for (let i = 0; i < engines.length; i++) {
        for (let j = i + 1; j < engines.length; j++) {
            for (let g = 0; g < config.gamesPerPair; g++) {
                const white = g % 2 === 0 ? engines[i] : engines[j];
                const black = g % 2 === 0 ? engines[j] : engines[i];
                matches.push({ white, black, id: matches.length + 1 });
            }
        }
    }

    console.log(`\nTotal matches: ${matches.length}\n`);

    // Run matches
    const results = [];

    for (let i = 0; i < matches.length; i++) {
        const match = matches[i];
        process.env.MOVE_TIME = String(config.moveTimeMs);
        const result = await playGame(match.white, match.black, match.id, config);
        results.push(result);
        console.log(`Game ${result.gameId}: ${result.white} vs ${result.black} → ${result.result} (${result.endReason}, ${result.ply} plies)`);
        printLeaderboard(engines);
    }

    // Save results
    const statsPath = path.join(config.outputDir, 'gamestats.txt');
    const sorted = [...engines].sort((a, b) => b.elo - a.elo);
    let stats = `Tournament finished: ${new Date().toISOString()}\n\n`;
    stats += 'FINAL LEADERBOARD\n';
    stats += '─'.repeat(100) + '\n';
    stats += `${'Rank'.padEnd(4)} ${'Engine'.padEnd(25)} ${'Elo'.padEnd(7)} ${'Games'.padEnd(6)} ${'Score'.padEnd(6)} ${'Avg Time'.padEnd(9)} W/D/L\n`;
    sorted.forEach((e, i) => {
        stats += `${(i + 1).toString().padEnd(4)} ${e.name.padEnd(25)} ${e.elo.toFixed(0).padEnd(7)} ${e.games.toString().padEnd(6)} ${e.score.toFixed(1).padEnd(6)} ${e.avgResponseTime().padStart(8)}s ${e.wins}/${e.draws}/${e.losses}\n`;
    });

    fs.writeFileSync(statsPath, stats);
    console.log(`\nResults saved to ${statsPath}`);

    // Cleanup
    engines.forEach(e => e.stop());
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
