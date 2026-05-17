import { findRegionAt } from "./regions.js";

export let balls = [];

export function initBalls(count, regions) {
  balls = [];
  const main = regions[0];

  for (let i = 0; i < count; i++) {
    const r = 10;
    const x = main.x + r + Math.random() * (main.w - 2 * r);
    const y = main.y + r + Math.random() * (main.h - 2 * r);
    const angle = Math.random() * Math.PI * 2;
    const speed = 180 + Math.random() * 80;

    balls.push({
      x,
      y,
      r,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      regionId: main.id,
      spin: Math.random() * Math.PI * 2,
      spinSpeed: (Math.random() * 1 + 0.5) * (Math.random() < 0.5 ? -1 : 1)
    });
  }
}

export function updateBalls(dt, regions) {
  for (const b of balls) {
    const region = regions.find(r => r.id === b.regionId && !r.captured) ||
                   findRegionAt(b.x, b.y) ||
                   regions[0];

    b.regionId = region.id;

    b.x += b.vx * dt;
    b.y += b.vy * dt;

    if (b.x - b.r < region.x) {
      b.x = region.x + b.r;
      b.vx *= -1;
    }
    if (b.x + b.r > region.x + region.w) {
      b.x = region.x + region.w - b.r;
      b.vx *= -1;
    }
    if (b.y - b.r < region.y) {
      b.y = region.y + b.r;
      b.vy *= -1;
    }
    if (b.y + b.r > region.y + region.h) {
      b.y = region.y + region.h - b.r;
      b.vy *= -1;
    }

    b.spin += b.spinSpeed * dt;
  }
}
