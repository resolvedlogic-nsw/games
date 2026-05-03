// ===== CONSTANTS =====
const DIE_SIZE = 80;
const NUMBER_DICE = 5;
const MAX_ROLLS = 5;
const GRAVITY = 0.6;
const BOUNCE_DAMPING = 0.55;
const FRICTION = 0.90;
const MIN_VELOCITY = 0.6;

// Level system: stack=3 (top), bank=2 (middle), table=1 (bottom)
// After a roll, dice cannot be moved DOWN a level.
const ZONE_LEVEL = { table: 1, bank: 2, stack: 3 };

// ===== HI/LO MAPPING =====
const HILO_DISPLAY = {
    1: "1↓", 2: "2↓", 3: "3↓",
    4: "1↑", 5: "2↑", 6: "3↑"
};

const FLAT_ROTATIONS = {
    1: { x: 0,   y: 0,   z: 0 },
    2: { x: -90, y: 0,   z: 0 },
    3: { x: 0,   y: -90, z: 0 },
    4: { x: 0,   y: 90,  z: 0 },
    5: { x: 90,  y: 0,   z: 0 },
    6: { x: 0,   y: 180, z: 0 }
};

const VALUE_TO_FACE_CLASS = { 1: 'front', 2: 'top', 3: 'right', 4: 'left', 5: 'bottom', 6: 'back' };

// ===== DOM ELEMENTS =====
const diceTable   = document.getElementById("dice-table");
const stackArea   = document.getElementById("stack-area");
const bankArea    = document.getElementById("bank-area");
const rollBtn     = document.getElementById("rollBtn");
const endTurnBtn  = document.getElementById("endTurnBtn");
const rollsDisplay= document.getElementById("rolls");
const p1ScoreDisplay = document.getElementById("p1score");
const p2ScoreDisplay = document.getElementById("p2score");
const stackTotal  = document.getElementById("stack-total");

// ===== GAME STATE =====
let dice = [];
let rollsThisTurn = 0;
let currentPlayer = 1;
let scores = { p1: 0, p2: 0 };
let animationFrame = null;
let draggedDie = null;
let diceAreFlying = false;   // true from roll click until all dice settle

// ===== SCORE CHART =====
const HI_BASE = { 22: 1, 23: 2, 24: 3, 25: 4, 26: 5, 27: 6, 28: 7, 29: 8, 30: 10 };
const LO_BASE = { 13: 1, 12: 2, 11: 3, 10: 4, 9: 5, 8: 6, 7: 7, 6: 8, 5: 10 };
const HILO_PIPS = { 1: 1, 2: 2, 3: 3, 4: 1, 5: 2, 6: 3 };

// ===== UTILS =====
function rand(min, max) { return Math.random() * (max - min) + min; }

function isStraight(values) {
    const s = values.slice().sort((a, b) => a - b).join(",");
    return s === "1,2,3,4,5" || s === "2,3,4,5,6";
}

function wakeDie(die) {
    die.settled = false;
    die.isCollided = false;
    die.settleFrames = 0;
    die.angularV = rand(-15, 15);
}

function highlightFaceByValue(die) {
    die.cube.querySelectorAll(".face").forEach(f => f.classList.remove("active"));
    const targetFaceClass = VALUE_TO_FACE_CLASS[die.value];
    const face = die.cube.querySelector(`.face.${targetFaceClass}`);
    if (face) face.classList.add("active");

    if (die.type === "hilo") {
        const isHi = die.value >= 4;
        document.getElementById("hi-table").classList.toggle("inactive", !isHi);
        document.getElementById("lo-table").classList.toggle("inactive", isHi);
    }
}

// ===== STACK TOTAL + TABLE ROW HIGHLIGHT =====
function updateStackTotal() {
    // Sum of number dice that are in stack OR bank (bank will auto-move at end)
    const committedDice = dice.filter(d => (d.zone === "stack" || d.zone === "bank") && d.type === "number");
    const sum = committedDice.reduce((total, die) => total + die.value, 0);

    stackTotal.textContent = sum;
    stackTotal.className = `stack-total player${currentPlayer}`;
    stackTotal.classList.toggle("visible", sum > 0);

    updateTableHighlight(sum);
}

function updateTableHighlight(sum) {
    // Clear all highlights
    document.querySelectorAll(".reference-table tr.highlighted").forEach(tr => tr.classList.remove("highlighted"));
    if (!sum) return;

    // Highlight matching row in whichever table(s) contain this sum
    ["hi-table", "lo-table"].forEach(tableId => {
        const table = document.getElementById(tableId);
        table.querySelectorAll("tbody tr").forEach(tr => {
            const sumCell = tr.querySelector("td:first-child");
            if (sumCell && parseInt(sumCell.textContent) === sum) {
                tr.classList.add("highlighted");
            }
        });
    });
}

// ===== PIP CREATION =====
function createPips(value, isHiLo) {
    const container = document.createElement("div");

    if (isHiLo) {
        container.className = "hilo-face-content";
        const pipsContainer = document.createElement("div");
        pipsContainer.className = "hilo-dots";
        const numPips = ((value - 1) % 3) + 1;
        for (let i = 0; i < numPips; i++) {
            const pip = document.createElement("div");
            pip.className = "hilo-dot";
            pipsContainer.appendChild(pip);
        }
        const arrow = document.createElement("div");
        arrow.className = "hilo-arrow";
        arrow.innerHTML = value <= 3 ? "🢃" : "🢁";
        container.appendChild(pipsContainer);
        container.appendChild(arrow);
    } else {
        container.className = "pip-grid";
        const pipMap = {
            1: [[2,2]],
            2: [[1,1],[3,3]],
            3: [[1,1],[2,2],[3,3]],
            4: [[1,1],[1,3],[3,1],[3,3]],
            5: [[1,1],[1,3],[2,2],[3,1],[3,3]],
            6: [[1,1],[1,2],[1,3],[3,1],[3,2],[3,3]]
        };
        pipMap[value].forEach(([x, y]) => {
            const pip = document.createElement("div");
            pip.className = "pip";
            pip.style.gridColumn = x;
            pip.style.gridRow = y;
            container.appendChild(pip);
        });
    }
    return container;
}

// ===== DIE CREATION =====
function createDie(id, type) {
    const wrapper = document.createElement("div");
    wrapper.className = `die-wrapper ${type} player${currentPlayer}`;
    wrapper.dataset.id = id;

    const cube = document.createElement("div");
    cube.className = "cube";

    const sides  = ["front","back","right","left","top","bottom"];
    const values = [1, 6, 3, 4, 2, 5];
    sides.forEach((side, i) => {
        const face = document.createElement("div");
        face.className = `face ${side}`;
        face.appendChild(createPips(values[i], type === "hilo"));
        cube.appendChild(face);
    });

    wrapper.appendChild(cube);
    diceTable.appendChild(wrapper);

    const tableRect = diceTable.getBoundingClientRect();
    const centerX  = tableRect.width / 2;
    const die = {
        id, type, wrapper, cube,
        x: centerX + rand(-100, 100) - 40,
        y: -100,
        vx: 0, vy: 0, angularV: 0,
        rotation: { x: rand(0,360), y: rand(0,360), z: rand(0,360) },
        value: 1, zone: "table", settled: true, isCollided: false, settleFrames: 0
    };

    wrapper.addEventListener("mousedown", (e) => startDrag(e, die));
    dice.push(die);
    return die;
}

// ===== DRAG AND DROP =====
function startDrag(e, die) {
    // No dragging before the first roll
    if (rollsThisTurn === 0) return;
    // No dragging while dice are in the air
    if (diceAreFlying) return;

    draggedDie = die;
    die.wrapper.classList.add("dragging");

    const rect = die.wrapper.getBoundingClientRect();
    die.wrapper.style.left = rect.left + "px";
    die.wrapper.style.top  = rect.top  + "px";
    die.wrapper.style.zIndex = "10000";

    document.getElementById("app").appendChild(die.wrapper);
}

document.addEventListener("mousemove", (e) => {
    if (!draggedDie) return;
    draggedDie.wrapper.style.left = (e.clientX - 40) + "px";
    draggedDie.wrapper.style.top  = (e.clientY - 40) + "px";
});

document.addEventListener("mouseup", (e) => {
    if (!draggedDie) return;
    const die = draggedDie;
    die.wrapper.classList.remove("dragging");

    const stackRect = stackArea.getBoundingClientRect();
    const bankRect  = bankArea.getBoundingClientRect();
    const tableRect = diceTable.getBoundingClientRect();
    const y = e.clientY;

    // --- figure out where the mouse landed ---
    let desiredZone = "table"; // default fallback (scoreboard / controls / sidebars)
    if (y >= stackRect.top && y <= stackRect.bottom)  desiredZone = "stack";
    else if (y >= bankRect.top && y <= bankRect.bottom) desiredZone = "bank";
    else if (y >= tableRect.top && y <= tableRect.bottom) desiredZone = "table";

    // --- LEVEL RULE: after a roll has happened, no die may move DOWN a level ---
    const currentLevel  = ZONE_LEVEL[die.zone];
    const desiredLevel  = ZONE_LEVEL[desiredZone];
    const finalZone     = (desiredLevel >= currentLevel) ? desiredZone : die.zone;

    // --- place it ---
    die.zone = finalZone;
    const target = finalZone === "stack" ? stackArea
                 : finalZone === "bank"  ? bankArea
                 : diceTable;

    target.appendChild(die.wrapper);
    const parentRect = target.getBoundingClientRect();
    die.x = e.clientX - parentRect.left - 40;
    die.y = e.clientY - parentRect.top  - 40;

    if (finalZone === "table") {
        die.x = Math.max(0, Math.min(die.x, tableRect.width  - 85));
        die.y = Math.max(0, Math.min(die.y, tableRect.height - 85));
        wakeDie(die);
    }

    die.wrapper.style.left   = die.x + "px";
    die.wrapper.style.top    = die.y + "px";
    die.wrapper.style.zIndex = "";

    draggedDie = null;
    updateStackTotal();
    checkEndTurnAvailable();
});

// ===== ROLL =====
function rollDice() {
    if (rollsThisTurn >= MAX_ROLLS) return;

    // Need at least one number die on the table to actually roll
    const tableNumbers = dice.filter(d => d.zone === "table" && d.type === "number");
    if (tableNumbers.length === 0) return;

    // After the first roll, must have committed at least one number die upward
    if (rollsThisTurn > 0) {
        const committed = dice.filter(d => (d.zone === "stack" || d.zone === "bank") && d.type === "number");
        if (committed.length === 0) {
            alert("You must move at least one die to the bank or stack before rolling again!");
            return;
        }
    }

    rollsThisTurn++;
    rollsDisplay.textContent = rollsThisTurn;
    diceAreFlying = true;

    dice.forEach(die => {
        if (die.zone !== "table") return;
        wakeDie(die);
        die.value = Math.floor(Math.random() * 6) + 1;
        highlightFaceByValue(die);
        die.vx = rand(-10, 10);
        die.vy = rand(-18, -12);
        die.angularV = rand(-20, 20);
    });

    if (!animationFrame) animate();
    rollBtn.disabled = rollsThisTurn >= MAX_ROLLS;
}

// ===== PHYSICS LOOP =====
function animate() {
    let stillMoving = false;
    const tableRect = diceTable.getBoundingClientRect();

    dice.forEach(die => {
        if (die.zone !== "table" || die.settled) return;
        stillMoving = true;

        die.vy += GRAVITY;
        die.x  += die.vx;
        die.y  += die.vy;
        die.vx *= FRICTION;

        // push away from other table dice
        dice.forEach(other => {
            if (other === die || other.zone !== "table") return;
            const dx   = die.x - other.x;
            const dy   = die.y - other.y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            if (dist < 75) {
                const angle = Math.atan2(dy, dx);
                die.vx += Math.cos(angle) * 0.8;
                die.vy += Math.sin(angle) * 0.8;
            }
        });

        // floor / walls
        if (die.y > tableRect.height - 85) {
            die.y = tableRect.height - 85;
            die.vy *= -BOUNCE_DAMPING;
            die.isCollided = true;
        }
        if (die.x < 0 || die.x > tableRect.width - 85) {
            die.vx *= -BOUNCE_DAMPING;
            die.x = die.x < 0 ? 0 : tableRect.width - 85;
        }

        // rotation
        if (die.isCollided) {
            const target = FLAT_ROTATIONS[die.value];
            die.rotation.x += (target.x - die.rotation.x) * 0.12;
            die.rotation.y += (target.y - die.rotation.y) * 0.12;
            die.rotation.z += (0     - die.rotation.z)     * 0.12;
            die.angularV *= 0.8;
        } else {
            die.rotation.x += die.angularV;
            die.rotation.y += die.angularV;
            die.rotation.z += die.angularV;
        }

        // settle check
        if (Math.abs(die.vx) < MIN_VELOCITY && Math.abs(die.vy) < 1 && die.isCollided) {
            die.settleFrames++;
            if (die.settleFrames > 30) {
                die.settled = true;
                die.vx = 0; die.vy = 0;
            }
        }

        die.wrapper.style.left = die.x + "px";
        die.wrapper.style.top  = die.y + "px";
        die.cube.style.transform = `rotateX(${die.rotation.x}deg) rotateY(${die.rotation.y}deg) rotateZ(${die.rotation.z}deg)`;
    });

    if (stillMoving) {
        animationFrame = requestAnimationFrame(animate);
    } else {
        animationFrame = null;
        diceAreFlying  = false;   // unlock dragging
        checkEndTurnAvailable();
    }
}

// ===== END-TURN HELPERS =====
function moveBankedDiceToStack() {
    return new Promise((resolve) => {
        const bankedDice = dice.filter(d => d.zone === "bank");
        if (bankedDice.length === 0) { resolve(); return; }

        const stackAreaRect = stackArea.getBoundingClientRect();
        const maxY = stackAreaRect.height * 0.5;

        bankedDice.forEach((die) => {
            const currentRect = die.wrapper.getBoundingClientRect();
            const targetX = currentRect.left - stackAreaRect.left;
            const finalY  = Math.min(maxY, (stackAreaRect.height - 80) * 0.5);

            die.zone = "stack";
            stackArea.appendChild(die.wrapper);

            const startX = currentRect.left - stackAreaRect.left;
            const startY = currentRect.top  - stackAreaRect.top;

            die.wrapper.style.transition = "none";
            die.wrapper.style.left = startX + "px";
            die.wrapper.style.top  = startY + "px";
            die.x = startX; die.y = startY;

            die.wrapper.offsetHeight; // reflow

            die.wrapper.style.transition = "left 0.6s ease-out, top 0.6s ease-out";
            die.wrapper.style.left = targetX + "px";
            die.wrapper.style.top  = finalY  + "px";
            die.x = targetX; die.y = finalY;
        });

        setTimeout(() => {
            bankedDice.forEach(d => { d.wrapper.style.transition = ""; });
            updateStackTotal();
            resolve();
        }, 650);
    });
}

function checkEndTurnAvailable() {
    const tableNumbers    = dice.filter(d => d.zone === "table" && d.type === "number");
    const committedNumbers = dice.filter(d => (d.zone === "stack" || d.zone === "bank") && d.type === "number");
    endTurnBtn.disabled = rollsThisTurn === 0 || tableNumbers.length > 0 || committedNumbers.length === 0;
}

// ===== END TURN / SCORING =====
async function endTurn() {
    endTurnBtn.disabled = true;
    rollBtn.disabled    = true;
    await moveBankedDiceToStack();

    const hiLoDie    = dice.find(d => d.type === "hilo");
    const numberDice = dice.filter(d => d.zone === "stack" && d.type === "number");
    const values     = numberDice.map(d => d.value);

    let finalScore = 0;
    if (isStraight(values)) {
        finalScore = 10;
    } else {
        const diceSum = values.reduce((s, v) => s + v, 0);
        const isHi    = hiLoDie.value >= 4;
        const pips    = HILO_PIPS[hiLoDie.value];

        if      (isHi  && HI_BASE[diceSum] !== undefined) finalScore = HI_BASE[diceSum] * pips;
        else if (!isHi && LO_BASE[diceSum] !== undefined) finalScore = LO_BASE[diceSum] * pips;
        else finalScore = 1;
    }

    // update score
    if (currentPlayer === 1) { scores.p1 += finalScore; p1ScoreDisplay.textContent = scores.p1; }
    else                     { scores.p2 += finalScore; p2ScoreDisplay.textContent = scores.p2; }

    // log
    const log = document.getElementById(`p${currentPlayer}-history`);
    const li  = document.createElement("li");
    li.textContent = `Sum ${values.reduce((a,b)=>a+b,0)} (${hiLoDie.value >= 4 ? 'HI' : 'LO'}): +${finalScore}`;
    log.prepend(li);

    const isWinner = scores.p1 >= 100 || scores.p2 >= 100;
    showScorePopup(values, HILO_DISPLAY[hiLoDie.value], finalScore, isWinner);
}

// ===== SCORE POPUP =====
function showScorePopup(values, hiLo, final, isWinner) {
    const popup = document.createElement("div");
    popup.id = "score-popup";
    popup.classList.add(`player${currentPlayer}-popup`);
    const sum = values.reduce((s, v) => s + v, 0);

    popup.innerHTML = `
        <h2>Player ${currentPlayer}</h2>
        <div class="score-detail">Dice: ${values.slice().sort((a,b)=>a-b).join(', ')}</div>
        ${isStraight(values)
            ? '<div class="score-detail">🎯 STRAIGHT! 🎯</div>'
            : `<div class="score-detail">Sum: ${sum}</div>`}
        <div class="score-detail">Hi/Lo: ${hiLo}</div>
        <div class="final-score">+${final} pts</div>
        <button onclick="${isWinner ? 'showWinnerScreen()' : 'nextTurn()'}">${isWinner ? '🏆 See Winner!' : 'Continue'}</button>
    `;
    document.body.appendChild(popup);
    setTimeout(() => popup.classList.add("show"), 50);
}

// ===== NEXT TURN =====
function nextTurn() {
    const p = document.getElementById("score-popup");
    if (p) p.remove();

    currentPlayer = currentPlayer === 1 ? 2 : 1;
    document.querySelectorAll(".player").forEach((el, i) => el.classList.toggle("active", i + 1 === currentPlayer));

    dice.forEach(d => d.wrapper.remove());
    dice = [];
    rollsThisTurn  = 0;
    diceAreFlying  = false;
    rollsDisplay.textContent = "0";

    stackTotal.textContent = "0";
    stackTotal.classList.remove("visible","player1","player2");
    updateTableHighlight(0);

    initTurnDice();
    rollBtn.disabled    = false;
    endTurnBtn.disabled = true;
}

function initTurnDice() {
    for (let i = 0; i < NUMBER_DICE; i++) createDie(i, "number");
    createDie("hilo", "hilo");
}

// ===== WINNER SCREEN + FIREWORKS =====
function showWinnerScreen() {
    // Remove round popup
    const p = document.getElementById("score-popup");
    if (p) p.remove();

    const winner      = scores.p1 >= 100 ? 1 : 2;
    const loser       = winner === 1 ? 2 : 1;
    const winnerColor = winner === 1 ? "#fbbf24" : "#60a5fa";

    // --- fireworks canvas (full-screen, behind the box) ---
    const canvas = document.createElement("canvas");
    canvas.id    = "fireworks-canvas";
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    document.body.appendChild(canvas);
    const ctx = canvas.getContext("2d");

    // --- winner overlay ---
    const overlay = document.createElement("div");
    overlay.id = "winner-overlay";
    overlay.innerHTML = `
        <div id="winner-box">
            <div class="winner-trophy">🏆</div>
            <h1 class="winner-title" style="color:${winnerColor}; text-shadow: 0 0 30px ${winnerColor};">
                PLAYER ${winner} WINS!
            </h1>
            <div class="winner-final-score" style="color:${winnerColor}; text-shadow: 0 0 20px ${winnerColor};">
                ${scores[`p${winner}`]} points
            </div>
            <div class="winner-scoreboard">
                <div class="winner-player ${winner===1?'winner-active':''}">
                    <span class="wp-label">Player 1</span>
                    <span class="wp-score" style="${winner===1?'color:#fbbf24':''}">${scores.p1}</span>
                </div>
                <div class="winner-vs">vs</div>
                <div class="winner-player ${winner===2?'winner-active':''}">
                    <span class="wp-label">Player 2</span>
                    <span class="wp-score" style="${winner===2?'color:#60a5fa':''}">${scores.p2}</span>
                </div>
            </div>
            <button onclick="location.reload()">Play Again</button>
        </div>
    `;
    document.body.appendChild(overlay);
    // trigger CSS show
    requestAnimationFrame(() => overlay.classList.add("show"));

    // ===== PARTICLE SYSTEM =====
    const PALETTE = ["#fbbf24","#60a5fa","#a855f7","#f43f5e","#34d399","#fb923c","#fff","#fde68a","#bfdbfe"];
    let particles = [];

    class Spark {
        constructor(x, y) {
            this.x = x;
            this.y = y;
            const angle = Math.random() * Math.PI * 2;
            const speed = 1.5 + Math.random() * 3.5;
            this.vx    = Math.cos(angle) * speed;
            this.vy    = Math.sin(angle) * speed;
            this.life  = 1;
            this.decay = 0.006 + Math.random() * 0.018;
            this.size  = 2 + Math.random() * 3;
            this.color = PALETTE[Math.floor(Math.random() * PALETTE.length)];
        }
        update() {
            this.x  += this.vx;
            this.y  += this.vy;
            this.vy += 0.045;          // gravity
            this.vx *= 0.995;          // slight air drag
            this.life -= this.decay;
        }
        draw() {
            ctx.save();
            ctx.globalAlpha = Math.max(0, this.life);
            ctx.fillStyle   = this.color;
            ctx.shadowBlur  = 8;
            ctx.shadowColor = this.color;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size * this.life, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }
    }

    function burst(x, y, count) {
        for (let i = 0; i < count; i++) particles.push(new Spark(x, y));
    }

    let lastLaunch = 0;
    let fwAnimId;

    function fwLoop(t) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // launch a new firework every 350-700ms at random upper positions
        if (t - lastLaunch > 350 + Math.random() * 350) {
            burst(
                80 + Math.random() * (canvas.width  - 160),
                60 + Math.random() * (canvas.height * 0.38),
                50 + Math.floor(Math.random() * 40)
            );
            lastLaunch = t;
        }

        for (let i = particles.length - 1; i >= 0; i--) {
            particles[i].update();
            particles[i].draw();
            if (particles[i].life <= 0) particles.splice(i, 1);
        }
        fwAnimId = requestAnimationFrame(fwLoop);
    }

    // immediate triple burst so it doesn't feel empty
    burst(canvas.width * 0.25, canvas.height * 0.25, 60);
    burst(canvas.width * 0.75, canvas.height * 0.20, 55);
    burst(canvas.width * 0.50, canvas.height * 0.35, 65);
    fwAnimId = requestAnimationFrame(fwLoop);

    // store so Play Again reload cleans up (not strictly needed but tidy)
    window._fwAnimId = fwAnimId;
}

// ===== BOOT =====
rollBtn.addEventListener("click", rollDice);
endTurnBtn.addEventListener("click", endTurn);
initTurnDice();