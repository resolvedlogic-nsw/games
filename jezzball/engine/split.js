import { findRegionAt, splitRegion } from "./regions.js";

export let currentSplit = null;
export const splitFailed = { flag: false };

export function clearSplitFlags() {
  currentSplit = null;
  splitFailed.flag = false;
}

export function startSplitAt(x, y, orientation, regions) {
  const region = findRegionAt(x, y);
  if (!region || region.captured) return;

  currentSplit = {
    regionId: region.id,
    x,
    y,
    orientation,
    progress1: 0,
    progress2: 0,
    speed: 400,
    completed: false
  };
}

function circleIntersectsSegment(cx, cy, r, x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) {
    const dist2 = (cx - x1) ** 2 + (cy - y1) ** 2;
    return dist2 <= r * r;
  }
  let t = ((cx - x1) * dx + (cy - y1) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  const px = x1 + t * dx;
  const py = y1 + t * dy;
  const dist2 = (cx - px) ** 2 + (cy - py) ** 2;
  return dist2 <= r * r;
}

export function updateSplit(dt, balls, regions) {
  if (!currentSplit) return;

  const s = currentSplit;
  const region = regions.find(r => r.id === s.regionId);
  if (!region || region.captured) {
    currentSplit = null;
    return;
  }

  const grow = s.speed * dt;

  if (s.orientation === "vertical") {
    s.progress1 -= grow;
    s.progress2 += grow;

    let y1 = s.y + s.progress1;
    let y2 = s.y + s.progress2;

    if (y1 < region.y) y1 = region.y;
    if (y2 > region.y + region.h) y2 = region.y + region.h;

    for (const b of balls) {
      if (b.regionId !== region.id) continue;
      if (circleIntersectsSegment(b.x, b.y, b.r, s.x, y1, s.x, y2)) {
        splitFailed.flag = true;
        currentSplit = null;
        return;
      }
    }

    if (y1 <= region.y && y2 >= region.y + region.h) {
      splitRegion(region, s);
      currentSplit.completed = true;
    }
  } else {
    s.progress1 -= grow;
    s.progress2 += grow;

    let x1 = s.x + s.progress1;
    let x2 = s.x + s.progress2;

    if (x1 < region.x) x1 = region.x;
    if (x2 > region.x + region.w) x2 = region.x + region.w;

    for (const b of balls) {
      if (b.regionId !== region.id) continue;
      if (circleIntersectsSegment(b.x, b.y, b.r, x1, s.y, x2, s.y)) {
        splitFailed.flag = true;
        currentSplit = null;
        return;
      }
    }

    if (x1 <= region.x && x2 >= region.x + region.w) {
      splitRegion(region, s);
      currentSplit.completed = true;
    }
  }
}
