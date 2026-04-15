const init = require('stockfish');
const fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
init().then(engine => {
  engine.print = msg => {
    if (msg) console.error('PRINT:' + msg);
  };
  engine.printErr = msg => {
    if (msg) console.error('ERR:' + msg);
  };
  engine.sendCommand('uci');
  engine.sendCommand('isready');
  engine.sendCommand('ucinewgame');
  engine.sendCommand(`position fen ${fen}`);
  engine.sendCommand('go movetime 300');
  setTimeout(() => process.exit(0), 2000);
});
