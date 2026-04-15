const { spawn } = require('child_process');

const DEFAULT_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function parseCliArgs(argv) {
  const opts = { first: 'trinity', movetime: 1500 };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--first') opts.first = argv[++i];
    else if (arg === '--movetime') opts.movetime = Number(argv[++i]);
    else if (arg === '--help' || arg === '-h') {
      console.log('Usage: node stockfish_match.js [--first trinity|stockfish] [--movetime MS]');
      process.exit(0);
    }
  }
  return opts;
}

function runPython(cmd, args) {
  return new Promise((resolve, reject) => {
    const py = spawn('python', ['-c', cmd, ...args], { stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '', err = '';
    py.stdout.on('data', d => out += d.toString());
    py.stderr.on('data', d => err += d.toString());
    py.on('close', code => {
      if (code !== 0) return reject(new Error(err || `python exit ${code}`));
      resolve(out.trim());
    });
    setTimeout(() => py.kill(), 10000);
  });
}

async function validateMove(fen, uci) {
  const cmd = `import chess,sys
fen=sys.argv[1]
uci=sys.argv[2]
b=chess.Board(fen)
try:
    m=chess.Move.from_uci(uci)
    print('ok' if m in b.legal_moves else 'illegal')
except:
    print('bad')`;
  return runPython(cmd, [fen, uci]);
}

async function applyMove(fen, uci) {
  const cmd = `import chess,sys
fen=sys.argv[1]
uci=sys.argv[2]
b=chess.Board(fen)
m=chess.Move.from_uci(uci)
b.push(m)
print(b.fen())`;
  return runPython(cmd, [fen, uci]);
}

function spawnTrinity(enginePath, movetime) {
  return new Promise((resolve, reject) => {
    const proc = spawn('node', [enginePath, '--movetime', String(movetime)], { stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '';
    proc.stdout.on('data', d => out += d.toString());
    proc.stderr.on('data', d => process.stderr.write(d.toString()));
    proc.on('close', () => resolve(out.trim()));
    proc.stdin.write(DEFAULT_FEN + '\n');
    proc.stdin.end();
    setTimeout(() => {
      resolve(out.trim());
      proc.kill();
    }, movetime + 2000);
  });
}

async function runTrinityMove(enginePath, fen, movetime) {
  return new Promise((resolve, reject) => {
    const proc = spawn('node', [enginePath, '--movetime', String(movetime)], { stdio: ['pipe', 'pipe', 'pipe'] });
    let buffer = '';
    let finished = false;

    proc.stdout.on('data', d => {
      buffer += d.toString();
      const lines = buffer.split(/\r?\n/);
      while (lines.length > 1) {
        const line = lines.shift().trim();
        buffer = lines.join('\n');
        if (line) {
          finished = true;
          resolve(line);
          proc.kill();
          return;
        }
      }
    });
    proc.stderr.on('data', d => process.stderr.write(d.toString()));
    proc.stdin.write(fen + '\n');
    proc.stdin.end();
    setTimeout(() => {
      if (!finished) {
        finished = true;
        resolve('0000');
        proc.kill();
      }
    }, movetime + 2500);
  });
}

async function createStockfish(level, threads, hash) {
  const proc = spawn('node', ['node_modules/stockfish/bin/stockfish.js'], { stdio: ['pipe', 'pipe', 'pipe'] });
  let bestMoveResolve = null;
  let readyResolve = null;
  const readyPromise = new Promise(resolve => { readyResolve = resolve; });

  proc.stdout.on('data', d => {
    const lines = d.toString().split(/\r?\n/);
    for (let line of lines) {
      line = line.trim();
      if (!line) continue;
      if (line === 'uciok' || line === 'readyok') {
        if (line === 'readyok') readyResolve();
        continue;
      }
      if (line.startsWith('bestmove') && bestMoveResolve) {
        const parts = line.split(' ');
        const move = parts[1] || '0000';
        const resolve = bestMoveResolve;
        bestMoveResolve = null;
        console.log('Stockfish bestmove', move);
        resolve(move);
      }
    }
  });
  proc.stderr.on('data', d => process.stderr.write('SFERR ' + d.toString()));

  function send(cmd) {
    proc.stdin.write(cmd + '\n');
  }

  send('uci');
  await new Promise(resolve => setTimeout(resolve, 200));
  send('setoption name UCI_LimitStrength value true');
  send(`setoption name Skill Level value ${level}`);
  send(`setoption name Threads value ${threads}`);
  send(`setoption name Hash value ${hash}`);
  send('isready');
  await readyPromise;
  console.log('stockfish ready');
  send('ucinewgame');

  return {
    move: (fen, movetime) => new Promise((resolve) => {
      console.log('STOCKFISH: request move', movetime);
      let timer;
      bestMoveResolve = move => {
        if (!timer) return;
        clearTimeout(timer);
        timer = null;
        resolve(move);
      };
      send(`position fen ${fen}`);
      send(`go movetime ${movetime}`);
      timer = setTimeout(() => {
        if (bestMoveResolve) {
          bestMoveResolve('0000');
          bestMoveResolve = null;
        }
      }, movetime + 10000);
    })
  };
}

async function playGame(engineFile, movetime, first) {
  const stockfish = await createStockfish(0, 1, 16);
  let fen = DEFAULT_FEN;
  let result = '*';
  for (let ply = 0; ply < 100; ply++) {
    const currentEngine = (ply % 2 === 0)
      ? { type: first }
      : { type: first === 'trinity' ? 'stockfish' : 'trinity' };
    console.log(`PLY ${ply} turn=${currentEngine.type} fen=${fen}`);
    let move;
    if (currentEngine.type === 'trinity') {
      move = await runTrinityMove(engineFile, fen, movetime);
      console.log('Trinity move', move);
    } else {
      move = await stockfish.move(fen, movetime);
      console.log('Stockfish move', move);
    }
    if (!move || move === '0000') { result = currentEngine.type === 'trinity' ? '0-1' : '1-0'; break; }
    const valid = await validateMove(fen, move);
    if (valid !== 'ok') { result = currentEngine.type === 'trinity' ? '0-1' : '1-0'; break; }
    fen = await applyMove(fen, move);
  }
  console.log('Result:', result);
}

(async () => {
  try {
    const opts = parseCliArgs(process.argv.slice(2));
    await playGame('Trinity-1.2.js', opts.movetime, opts.first);
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
