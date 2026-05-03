// ===== CONSTANTS =====
const DIE_SIZE = 80;
const NUMBER_DICE = 5;
const MAX_ROLLS = 5;
const GRAVITY = 0.6;
const BOUNCE_DAMPING = 0.55;
const FRICTION = 0.90;
const MIN_VELOCITY = 0.6;

// ===== HI/LO MAPPING =====
// Face value → display label. Matches createPips: value 1-3 = LO (↓), value 4-6 = HI (↑)
// Pip count = ((value - 1) % 3) + 1, so: 1→1, 2→2, 3→3, 4→1, 5→2, 6→3
const HILO_DISPLAY = {
    1: "1↓", 2: "2↓", 3: "3↓",
    4: "1↑", 5: "2↑", 6: "3↑"
};

const FLAT_ROTATIONS = {
    1: { x: 0,   y: 0,   z: 0 },   // Front (1)
    2: { x: -90, y: 0,   z: 0 },   // Top (2)
    3: { x: 0,   y: -90, z: 0 },   // Right (3)
    4: { x: 0,   y: 90,  z: 0 },   // Left (4)
    5: { x: 90,  y: 0,   z: 0 },   // Bottom (5)
    6: { x: 0,   y: 180, z: 0 }    // Back (6)
};

const VALUE_TO_FACE_CLASS = { 1: 'front', 2: 'top', 3: 'right', 4: 'left', 5: 'bottom', 6: 'back' };

// ===== DOM ELEMENTS =====
const diceTable = document.getElementById("dice-table");
const stackArea = document.getElementById("stack-area");
const bankArea = document.getElementById("bank-area");
const rollBtn = document.getElementById("rollBtn");
const endTurnBtn = document.getElementById("endTurnBtn");
const rollsDisplay = document.getElementById("rolls");
const p1ScoreDisplay = document.getElementById("p1score");
const p2ScoreDisplay = document.getElementById("p2score");
const stackTotal = document.getElementById("stack-total");

// ===== GAME STATE =====
let dice = [];
let rollsThisTurn = 0;
let currentPlayer = 1;
let scores = { p1: 0, p2: 0 };
let animationFrame = null;
let draggedDie = null;

// ===== SCORE CHART =====
// Base scores indexed by sum — HI range (22-30) and LO range (5-13)
const HI_BASE = { 22: 1, 23: 2, 24: 3, 25: 4, 26: 5, 27: 6, 28: 7, 29: 8, 30: 10 };
const LO_BASE = { 13: 1, 12: 2, 11: 3, 10: 4, 9: 5, 8: 6, 7: 7, 6: 8, 5: 10 };

// Pip count from the HiLo die value — matches createPips formula: ((value-1) % 3) + 1
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

function updateStackTotal() {
    const stackedDice = dice.filter(d => d.zone === "stack" && d.type === "number");
    const sum = stackedDice.reduce((total, die) => total + die.value, 0);
    
    stackTotal.textContent = sum;
    stackTotal.className = `stack-total player${currentPlayer}`;
    
    if (sum > 0) {
        stackTotal.classList.add("visible");
    } else {
        stackTotal.classList.remove("visible");
    }
}

// FIXED: Generate standard pips for regular dice, special layout for HiLo
function createPips(value, isHiLo) {
    const container = document.createElement("div");
    
    if (isHiLo) {
        // Special HiLo layout: pips on left, arrow on right
        container.className = "hilo-face-content";
        
        // Left side: 1-3 vertical pips
        const pipsContainer = document.createElement("div");
        pipsContainer.className = "hilo-dots";
        const numPips = ((value - 1) % 3) + 1; // Maps 1,4->1 | 2,5->2 | 3,6->3
        for (let i = 0; i < numPips; i++) {
            const pip = document.createElement("div");
            pip.className = "hilo-dot";
            pipsContainer.appendChild(pip);
        }
        
        // Right side: arrow (up for 4-6, down for 1-3)
        const arrow = document.createElement("div");
        arrow.className = "hilo-arrow";
        arrow.innerHTML = value <= 3 ? "🢃" : "🢁";
        
        container.appendChild(pipsContainer);
        container.appendChild(arrow);
    } else {
        // Standard dice pips
        container.className = "pip-grid";
        const pipMap = {
            1: [[2, 2]], 2: [[1, 1], [3, 3]], 3: [[1, 1], [2, 2], [3, 3]],
            4: [[1, 1], [1, 3], [3, 1], [3, 3]], 5: [[1, 1], [1, 3], [2, 2], [3, 1], [3, 3]],
            6: [[1, 1], [1, 2], [1, 3], [3, 1], [3, 2], [3, 3]]
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

function createDie(id, type) {
    const wrapper = document.createElement("div");
    wrapper.className = `die-wrapper ${type} player${currentPlayer}`;
    wrapper.dataset.id = id;

    const cube = document.createElement("div");
    cube.className = "cube";

    const sides = ["front", "back", "right", "left", "top", "bottom"];
    const values = [1, 6, 3, 4, 2, 5];
    sides.forEach((side, i) => {
        const face = document.createElement("div");
        face.className = `face ${side}`;
        face.appendChild(createPips(values[i], type === "hilo"));
        cube.appendChild(face);
    });

    wrapper.appendChild(cube);
    diceTable.appendChild(wrapper);

    // FIXED: Center dice in the table area
    const tableRect = diceTable.getBoundingClientRect();
    const centerX = tableRect.width / 2;
    const die = {
        id, type, wrapper, cube,
        x: centerX + rand(-100, 100) - 40, // Center with some randomness
        y: -100, 
        vx: 0, vy: 0, angularV: 0,
        rotation: { x: rand(0, 360), y: rand(0, 360), z: rand(0, 360) },
        value: 1, zone: "table", settled: true, isCollided: false, settleFrames: 0
    };

    wrapper.addEventListener("mousedown", (e) => startDrag(e, die));
    dice.push(die);
    return die;
}

// ===== DRAG AND DROP =====
function startDrag(e, die) {
    // No dragging at all until the first roll has happened
    if (rollsThisTurn === 0) return;

    // HiLo die is never manually dragged
    if (die.type === "hilo") return;

    // Once a die is in stack or bank, it's locked there
    if (die.zone === "stack" || die.zone === "bank") return;

    draggedDie = die;
    die.wrapper.classList.add("dragging");

    const rect = die.wrapper.getBoundingClientRect();
    die.wrapper.style.left = rect.left + "px";
    die.wrapper.style.top = rect.top + "px";
    die.wrapper.style.zIndex = "10000";
    
    document.getElementById("app").appendChild(die.wrapper);
}

document.addEventListener("mousemove", (e) => {
    if (!draggedDie) return;
    draggedDie.wrapper.style.left = (e.clientX - 40) + "px";
    draggedDie.wrapper.style.top = (e.clientY - 40) + "px";
});

document.addEventListener("mouseup", (e) => {
    if (!draggedDie) return;
    const die = draggedDie;
    die.wrapper.classList.remove("dragging");

    const stackRect = stackArea.getBoundingClientRect();
    const bankRect = bankArea.getBoundingClientRect();
    const tableRect = diceTable.getBoundingClientRect();
    const y = e.clientY;

    let target = diceTable;
    die.zone = "table";

    // Only assign to stack/bank if the drop is actually within those rects
    if (y >= stackRect.top && y <= stackRect.bottom) {
        target = stackArea;
        die.zone = "stack";
    } else if (y >= bankRect.top && y <= bankRect.bottom) {
        target = bankArea;
        die.zone = "bank";
    }
    // Anything else (scoreboard, controls, sidebars) falls through to table

    target.appendChild(die.wrapper);
    const parentRect = target.getBoundingClientRect();
    die.x = e.clientX - parentRect.left - 40;
    die.y = e.clientY - parentRect.top - 40;

    // If it landed back on table, clamp it inside the table bounds
    if (die.zone === "table") {
        die.x = Math.max(0, Math.min(die.x, tableRect.width - 85));
        die.y = Math.max(0, Math.min(die.y, tableRect.height - 85));
        wakeDie(die);
    }

    die.wrapper.style.left = die.x + "px";
    die.wrapper.style.top = die.y + "px";
    die.wrapper.style.zIndex = "";

    draggedDie = null;
    updateStackTotal();
    checkEndTurnAvailable();
});

// ===== ANIMATION =====
function rollDice() {
    if (rollsThisTurn >= MAX_ROLLS) return;
    
    // Must have at least one number die on the table to roll
    const tableDiceNumber = dice.filter(d => d.zone === "table" && d.type === "number");
    if (tableDiceNumber.length === 0) return;

    // After first roll, require at least one number die in stack before allowing next roll
    if (rollsThisTurn > 0) {
        const stackedNumberDice = dice.filter(d => d.zone === "stack" && d.type === "number");
        if (stackedNumberDice.length === 0) {
            alert("You must stack at least one die before rolling again!");
            return;
        }
    }
    
    rollsThisTurn++;
    rollsDisplay.textContent = rollsThisTurn;

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

function animate() {
    let stillMoving = false;
    const tableRect = diceTable.getBoundingClientRect();

    dice.forEach(die => {
        if (die.zone !== "table" || die.settled) return;
        stillMoving = true;

        die.vy += GRAVITY;
        die.x += die.vx;
        die.y += die.vy;
        die.vx *= FRICTION;

        dice.forEach(other => {
            if (other === die || other.zone !== "table") return;
            const dx = die.x - other.x;
            const dy = die.y - other.y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            if (dist < 75) {
                const angle = Math.atan2(dy, dx);
                die.vx += Math.cos(angle) * 0.8;
                die.vy += Math.sin(angle) * 0.8;
            }
        });

        if (die.y > tableRect.height - 85) {
            die.y = tableRect.height - 85;
            die.vy *= -BOUNCE_DAMPING;
            die.isCollided = true;
        }
        if (die.x < 0 || die.x > tableRect.width - 85) {
            die.vx *= -BOUNCE_DAMPING;
            die.x = die.x < 0 ? 0 : tableRect.width - 85;
        }

        if (die.isCollided) {
            const target = FLAT_ROTATIONS[die.value];
            die.rotation.x += (target.x - die.rotation.x) * 0.12;
            die.rotation.y += (target.y - die.rotation.y) * 0.12;
            die.rotation.z += (0 - die.rotation.z) * 0.12;
            die.angularV *= 0.8;
        } else {
            die.rotation.x += die.angularV;
            die.rotation.y += die.angularV;
            die.rotation.z += die.angularV;
        }

        if (Math.abs(die.vx) < MIN_VELOCITY && Math.abs(die.vy) < 1 && die.isCollided) {
            die.settleFrames++;
            if (die.settleFrames > 30) {
                die.settled = true;
                die.vx = 0; die.vy = 0;
            }
        }

        die.wrapper.style.left = die.x + "px";
        die.wrapper.style.top = die.y + "px";
        die.cube.style.transform = `rotateX(${die.rotation.x}deg) rotateY(${die.rotation.y}deg) rotateZ(${die.rotation.z}deg)`;
    });

    animationFrame = stillMoving ? requestAnimationFrame(animate) : null;
}

// ===== SCORING =====
function moveBankedDiceToStack() {
    return new Promise((resolve) => {
        const bankedDice = dice.filter(d => d.zone === "bank");
        
        if (bankedDice.length === 0) {
            resolve();
            return;
        }
        
        const stackAreaRect = stackArea.getBoundingClientRect();
        const maxY = stackAreaRect.height * 0.5; // Lock to 50% vertical max
        
        // Move each banked die
        bankedDice.forEach((die, index) => {
            // Get current position before moving
            const currentRect = die.wrapper.getBoundingClientRect();
            
            // Target X: same horizontal position relative to stack area
            const targetX = currentRect.left - stackAreaRect.left;
            // Target Y: centered vertically in stack area, clamped to 50%
            const finalY = Math.min(maxY, (stackAreaRect.height - 80) * 0.5);
            
            // Update zone and append to stack
            die.zone = "stack";
            stackArea.appendChild(die.wrapper);
            
            // Set starting position (where it currently is visually, relative to stack area)
            const startX = currentRect.left - stackAreaRect.left;
            const startY = currentRect.top - stackAreaRect.top;
            
            die.wrapper.style.transition = "none";
            die.wrapper.style.left = startX + "px";
            die.wrapper.style.top = startY + "px";
            die.x = startX;
            die.y = startY;
            
            // Force reflow
            die.wrapper.offsetHeight;
            
            // Now animate to target position
            die.wrapper.style.transition = "left 0.6s ease-out, top 0.6s ease-out";
            die.wrapper.style.left = targetX + "px";
            die.wrapper.style.top = finalY + "px";
            die.x = targetX;
            die.y = finalY;
        });
        
        // Update state and resolve after animation
        setTimeout(() => {
            bankedDice.forEach(die => {
                die.wrapper.style.transition = "";
            });
            updateStackTotal();
            resolve();
        }, 650);
    });
}

function checkEndTurnAvailable() {
    // Number dice still on the table (HiLo doesn't count — it can't be moved)
    const tableNumberDice = dice.filter(d => d.zone === "table" && d.type === "number");
    // At least one number die must be stacked (or banked, which will auto-move)
    const stackedOrBanked = dice.filter(d => (d.zone === "stack" || d.zone === "bank") && d.type === "number");
    // Must have rolled at least once
    endTurnBtn.disabled = rollsThisTurn === 0 || tableNumberDice.length > 0 || stackedOrBanked.length === 0;
}

async function endTurn() {
    // First, move any banked dice to stack
    await moveBankedDiceToStack();
    
    const stackedDice = dice.filter(d => d.zone === "stack");
    const hiLoDie = dice.find(d => d.type === "hilo");
    const numberDice = stackedDice.filter(d => d.type === "number");
    const values = numberDice.map(d => d.value);

    let finalScore = 0;
    if (isStraight(values)) {
        finalScore = 10;
    } else {
        const diceSum = values.reduce((sum, v) => sum + v, 0);
        const isHi = hiLoDie.value >= 4;       // HiLo die landed on 4,5,6 = HI direction
        const pips = HILO_PIPS[hiLoDie.value]; // 1, 2, or 3 pips

        if (isHi && HI_BASE[diceSum] !== undefined) {
            // HI direction + sum is in HI range: base × pips
            finalScore = HI_BASE[diceSum] * pips;
        } else if (!isHi && LO_BASE[diceSum] !== undefined) {
            // LO direction + sum is in LO range: base × pips
            finalScore = LO_BASE[diceSum] * pips;
        } else {
            // Direction doesn't match the sum range — just 1 point
            finalScore = 1;
        }
    }

    if (currentPlayer === 1) {
        scores.p1 += finalScore;
        p1ScoreDisplay.textContent = scores.p1;
    } else {
        scores.p2 += finalScore;
        p2ScoreDisplay.textContent = scores.p2;
    }

    const log = document.getElementById(`p${currentPlayer}-history`);
    const li = document.createElement("li");
    li.textContent = `Sum ${values.reduce((a,b)=>a+b,0)} (${hiLoDie.value >= 4 ? 'HI' : 'LO'}): +${finalScore}`;
    log.prepend(li);

    showScorePopup(values, HILO_DISPLAY[hiLoDie.value], finalScore);
}

function showScorePopup(values, hiLo, final) {
    const popup = document.createElement("div");
    popup.id = "score-popup";
    popup.classList.add(`player${currentPlayer}-popup`);
    const sum = values.reduce((s, v) => s + v, 0);
    popup.innerHTML = `
        <h2>Player ${currentPlayer}</h2>
        <div class="score-detail">Dice: ${values.sort().join(', ')}</div>
        ${isStraight(values) ? '<div class="score-detail">🎯 STRAIGHT! 🎯</div>' : `<div class="score-detail">Sum: ${sum}</div>`}
        <div class="score-detail">Hi/Lo: ${hiLo}</div>
        <div class="final-score">+${final} pts</div>
        <button onclick="nextTurn()">Continue</button>
    `;
    document.body.appendChild(popup);
    setTimeout(() => popup.classList.add("show"), 50);
}

function nextTurn() {
    const p = document.getElementById("score-popup");
    if (p) p.remove();

    if (scores.p1 >= 100 || scores.p2 >= 100) {
        alert(`Player ${scores.p1 >= 100 ? 1 : 2} wins!`);
        location.reload();
        return;
    }

    currentPlayer = currentPlayer === 1 ? 2 : 1;
    document.querySelectorAll(".player").forEach((p, i) => p.classList.toggle("active", i + 1 === currentPlayer));
    
    dice.forEach(d => d.wrapper.remove());
    dice = [];
    rollsThisTurn = 0;
    rollsDisplay.textContent = "0";
    
    // Reset stack total
    stackTotal.textContent = "0";
    stackTotal.classList.remove("visible", "player1", "player2");
    
    initTurnDice();
    rollBtn.disabled = false;
    endTurnBtn.disabled = true;
}

function initTurnDice() {
    for (let i = 0; i < NUMBER_DICE; i++) createDie(i, "number");
    createDie("hilo", "hilo");
}

rollBtn.addEventListener("click", rollDice);
endTurnBtn.addEventListener("click", endTurn);
initTurnDice();