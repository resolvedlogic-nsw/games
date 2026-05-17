export let regions = [];

let nextRegionId = 1;

export function initRegions(w, h) {
  regions = [{
    id: nextRegionId++,
    x: 0,
    y: 0,
    w,
    h,
    area: w * h,
    hasBall: true,
    captured: false
  }];
}

export function findRegionAt(x, y) {
  return regions.find(r =>
    x >= r.x && x <= r.x + r.w &&
    y >= r.y && y <= r.y + r.h &&
    !r.captured
  ) || null;
}

export function splitRegion(region, split) {
  const r = region;

  if (split.orientation === "vertical") {
    const x = split.x;
    if (x <= r.x + 5 || x >= r.x + r.w - 5) return;

    const left = {
      id: nextRegionId++,
      x: r.x,
      y: r.y,
      w: x - r.x,
      h: r.h,
      area: (x - r.x) * r.h,
      hasBall: false,
      captured: false
    };

    const right = {
      id: nextRegionId++,
      x: x,
      y: r.y,
      w: r.x + r.w - x,
      h: r.h,
      area: (r.x + r.w - x) * r.h,
      hasBall: false,
      captured: false
    };

    regions = [
      ...regions.filter(rr => rr.id !== r.id),
      left,
      right
    ];
  }

  if (split.orientation === "horizontal") {
    const y = split.y;
    if (y <= r.y + 5 || y >= r.y + r.h - 5) return;

    const top = {
      id: nextRegionId++,
      x: r.x,
      y: r.y,
      w: r.w,
      h: y - r.y,
      area: r.w * (y - r.y),
      hasBall: false,
      captured: false
    };

    const bottom = {
      id: nextRegionId++,
      x: r.x,
      y: y,
      w: r.w,
      h: r.y + r.h - y,
      area: r.w * (r.y + r.h - y),
      hasBall: false,
      captured: false
    };

    regions = [
      ...regions.filter(rr => rr.id !== r.id),
      top,
      bottom
    ];
  }
}
