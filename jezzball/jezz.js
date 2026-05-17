import { initRegions, regions } from "./engine/regions.js";
import { initBalls, updateBalls, balls } from "./engine/balls.js";
import { setupInput } from "./engine/input.js";
import { currentSplit, updateSplit, splitFailed, clearSplitFlags } from "./engine/split.js";
import { floodAssign } from "./engine/floodfill.js";
import { render } from "./engine/renderer.js";

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

let level = 1;
let lives = 5;
let captured = 0;

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener("resize", resize);
resize();

function updateUI() {
  document.getElementById("level").textContent = level;
  document.getElementById("lives").textContent = lives;
  document.getElementById("captured").textContent = captured + "%";
}

function startLevel() {
  initRegions(canvas.width, canvas.height);
  initBalls(level + 1, regions); // classic: level N = N+1 balls
  captured = 0;
  updateUI();
}

setupInput(canvas);

let last = 0;
function loop(ts) {
  const dt = (ts - last) / 1000;
  last = ts;

  updateBalls(dt, regions);
  updateSplit(dt, balls, regions);

  if (splitFailed.flag) {
    lives--;
    clearSplitFlags();
    if (lives <= 0) {
      level = 1;
      lives = 5;
      startLevel();
    }
    updateUI();
  }

  if (currentSplit && currentSplit.completed) {
    floodAssign(balls, regions); // assign balls to regions & mark captured
    clearSplitFlags();
  }

  const totalArea = regions.reduce((a, r) => a + r.area, 0);
  const ballArea = regions
    .filter(r => !r.captured)
    .reduce((a, r) => a + r.area, 0);

  captured = Math.floor(100 - (ballArea / totalArea) * 100);
  if (captured < 0) captured = 0;
  if (captured > 100) captured = 100;

  if (captured >= 75) {
    level++;
    startLevel();
  }

  updateUI();
  render(ctx, canvas.width, canvas.height, regions, balls, currentSplit);

  requestAnimationFrame(loop);
}

startLevel();
requestAnimationFrame(loop);
