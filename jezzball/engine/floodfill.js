export function floodAssign(balls, regions) {
  for (const r of regions) {
    r.hasBall = false;
  }

  for (const b of balls) {
    const r = regions.find(rr =>
      b.x >= rr.x && b.x <= rr.x + rr.w &&
      b.y >= rr.y && b.y <= rr.y + rr.h
    );
    if (r) {
      r.hasBall = true;
      b.regionId = r.id;
    }
  }

  for (const r of regions) {
    if (!r.hasBall) {
      r.captured = true;
    }
  }
}
