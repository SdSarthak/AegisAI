const emojis = ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼'];

let matches = 0;
let moves   = 0;
let flipped = [];
let locked  = false;
let timerInterval = null;
let elapsedSeconds = 0;
let timerStarted = false;

const scoreBoard  = document.getElementById('score-board');
const movesBoard  = document.getElementById('moves');
const timerEl     = document.getElementById('timer');
const bestTimeEl  = document.getElementById('best-time');
const board       = document.getElementById('game-board');
const resetBtn    = document.getElementById('reset-btn');
const winModal    = document.getElementById('win-modal');
const modalBody   = document.getElementById('modal-body');
const modalBest   = document.getElementById('modal-best');
const modalPlayAgain = document.getElementById('modal-play-again');

function startTimer() {
  if (timerStarted) return;
  timerStarted = true;
  timerInterval = setInterval(() => {
    elapsedSeconds++;
    timerEl.textContent = elapsedSeconds + 's';
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
}

function resetTimer() {
  stopTimer();
  elapsedSeconds = 0;
  timerStarted = false;
  timerEl.textContent = '0s';
}

function getBest() {
  const v = localStorage.getItem('memgame_best');
  return v ? parseInt(v, 10) : null;
}

function updateBestDisplay() {
  const best = getBest();
  bestTimeEl.textContent = best !== null ? best + 's' : '--';
}

function updateScore() {
  matches++;
  scoreBoard.textContent = matches;
  bump(scoreBoard);

  if (matches === emojis.length) {
    stopTimer();
    const best = getBest();
    const isNew = best === null || elapsedSeconds < best;
    if (isNew) localStorage.setItem('memgame_best', elapsedSeconds);
    updateBestDisplay();
    setTimeout(() => showWinModal(isNew, best), 500);
  }
}

function updateMoves() {
  moves++;
  movesBoard.textContent = moves;
}

function bump(el) {
  el.classList.remove('bump');
  void el.offsetWidth; // reflow to restart animation
  el.classList.add('bump');
  setTimeout(() => el.classList.remove('bump'), 220);
}

function showWinModal(isNewBest, prevBest) {
  modalBody.textContent = `Completed in ${elapsedSeconds}s with ${moves} moves.`;
  if (isNewBest && prevBest !== null) {
    modalBest.textContent = `🏆 New best! Previous: ${prevBest}s`;
  } else if (isNewBest) {
    modalBest.textContent = `🏆 First record set: ${elapsedSeconds}s`;
  } else {
    modalBest.textContent = `Best time: ${getBest()}s`;
  }
  winModal.hidden = false;
  launchConfetti();
}

function launchConfetti() {
  const colors = ['#6c63ff','#48cae4','#f72585','#43e97b','#ffd700','#ff6b6b'];
  for (let i = 0; i < 60; i++) {
    const el = document.createElement('div');
    el.className = 'confetti-piece';
    el.style.cssText = `
      left: ${Math.random() * 100}vw;
      top: -12px;
      background: ${colors[Math.floor(Math.random() * colors.length)]};
      width: ${6 + Math.random() * 8}px;
      height: ${6 + Math.random() * 8}px;
      border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
      animation-duration: ${1.5 + Math.random() * 2}s;
      animation-delay: ${Math.random() * 0.8}s;
    `;
    document.body.appendChild(el);
    el.addEventListener('animationend', () => el.remove());
  }
}

function createCard(emoji, index) {
  const card = document.createElement('div');
  card.classList.add('card');
  card.dataset.value = emoji;
  card.style.animationDelay = `${index * 0.05}s`;

  const inner = document.createElement('div');
  inner.className = 'card-inner';

  const front = document.createElement('div');
  front.className = 'card-front';

  const back = document.createElement('div');
  back.className = 'card-back';
  back.textContent = emoji;

  inner.appendChild(front);
  inner.appendChild(back);
  card.appendChild(inner);

  card.addEventListener('click', () => {
    if (locked || card.classList.contains('flipped') || card.classList.contains('matched')) return;

    startTimer();

    card.classList.add('flipped');
    flipped.push(card);

    if (flipped.length === 2) {
      locked = true;
      updateMoves();
      const [a, b] = flipped;

      if (a.dataset.value === b.dataset.value) {
        setTimeout(() => {
          a.classList.add('matched');
          b.classList.add('matched');
          updateScore();
          flipped = [];
          locked  = false;
        }, 400);
      } else {
        setTimeout(() => {
          a.classList.remove('flipped');
          b.classList.remove('flipped');
          flipped = [];
          locked  = false;
        }, 1000);
      }
    }
  });

  return card;
}

function initGame() {
  board.innerHTML = '';
  matches = 0;
  moves   = 0;
  flipped = [];
  locked  = false;
  scoreBoard.textContent = '0';
  movesBoard.textContent = '0';
  winModal.hidden = true;
  resetTimer();
  updateBestDisplay();

  const shuffled = [...emojis, ...emojis].sort(() => Math.random() - 0.5);
  shuffled.forEach((emoji, i) => board.appendChild(createCard(emoji, i)));
}

resetBtn.addEventListener('click', initGame);
modalPlayAgain.addEventListener('click', initGame);

initGame();
