const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

const TILE = 32;
const gravity = 0.05;
const thrustPower =  0.12;

let keys = {};
let gravityEnabled = false;

document.addEventListener("keydown", e => keys[e.code] = true);
document.addEventListener("keyup", e => keys[e.code] = false);
document.addEventListener("keydown", e => {if (e.code === "KeyG") gravityEnabled = !gravityEnabled;});
// Simple Minecraft-style tilemap
const map = [
  [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
  [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
  [1,0,2,2,0,0,2,2,0,0,0,0,0,0,0,2,2,0,0,0,0,2,2,0,1],
  [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
  [1,0,0,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0,0,3,3,3,0,0,1],

  // FIXED: 15 unique empty rows
  ...Array.from({length: 15}, () => 
      [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
  ),

  // bottom wall
  [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
];

let ship = {
    x: 200,
    y: 100,
    vx: 0,
    vy: 0,
    angle: -Math.PI / 2
};

function update() {
    // Rotate
    if (keys["ArrowLeft"]) ship.angle -= 0.05;
    if (keys["ArrowRight"]) ship.angle += 0.05;

    // Thrust
    if (keys["ArrowUp"]) {
        ship.vx += Math.cos(ship.angle) * thrustPower;
        ship.vy += Math.sin(ship.angle) * thrustPower;
    }

    // Gravity
    if (gravityEnabled) {
    ship.vy += gravity;
}

    // Move
    ship.x += ship.vx;
    ship.y += ship.vy;

    // Collision detection
    const tileX = Math.floor(ship.x / TILE);
    const tileY = Math.floor(ship.y / TILE);

    if (map[tileY] && map[tileY][tileX] !== 0) {
        if (map[tileY][tileX] === 3) {
            // Landing pad
            const speed = Math.hypot(ship.vx, ship.vy);
            const upright = Math.abs(ship.angle + Math.PI/2) < 0.2;

            if (speed < 1.5 && upright) {
                alert("Successful landing!");
            } else {
                alert("Crash!");
            }
        } else {
            alert("Crash!");
        }

        resetShip();
    }
}

function resetShip() {
    ship.x = 5 * TILE + TILE/2;
    ship.y = 5 * TILE + TILE/2;
    ship.vx = 0;
    ship.vy = 0;
    ship.angle = -Math.PI / 2;
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw tiles
    for (let y = 0; y < map.length; y++) {
        for (let x = 0; x < map[y].length; x++) {
            if (map[y][x] === 1) ctx.fillStyle = "#6b4f2a"; // dirt
            else if (map[y][x] === 2) ctx.fillStyle = "#777"; // stone
            else if (map[y][x] === 3) ctx.fillStyle = "#44ff44"; // landing pad
            else continue;

            ctx.fillRect(x*TILE, y*TILE, TILE, TILE);
        }
    }

    ctx.save();
    ctx.translate(ship.x, ship.y);

    // Rotate sprite so angle = -90° looks upright
    ctx.rotate(ship.angle + Math.PI/2);

    // Ship body (nose at top)
    ctx.fillStyle = "white";
    ctx.fillRect(-5, -10, 10, 20);

    // Flame at tail
    if (keys["ArrowUp"]) {
        ctx.fillStyle = "orange";
        ctx.fillRect(-3, 10, 6, 12);
    }

    ctx.restore();
}

function loop() {
    update();
    draw();
    requestAnimationFrame(loop);
}

loop();
