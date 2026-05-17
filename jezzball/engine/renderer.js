function drawBall(ctx, b) {
  const r = b.r;

  ctx.save();
  ctx.translate(b.x, b.y);
  ctx.rotate(b.spin);

  const grad = ctx.createRadialGradient(-r * 0.3, -r * 0.3, r * 0.2, 0, 0, r);
  grad.addColorStop(0, "#ffdddd");
  grad.addColorStop(0.3, "#ff4444");
  grad.addColorStop(1, "#880000");

  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "rgba(255,255,255,0.8)";
  ctx.lineWidth = r * 0.25;
  ctx.beginPath();
  ctx.arc(0, 0, r * 0.6, -0.4, 0.4);
  ctx.stroke();

  ctx.restore();
}

export function render(ctx, w, h, regions, balls, currentSplit) {
  ctx.clearRect(0, 0, w, h);

  for (const r of regions) {
    ctx.fillStyle = r.captured ? "#001018" : "#003344";
    ctx.fillRect(r.x, r.y, r.w, r.h);

    ctx.strokeStyle = r.captured ? "#224455" : "#44aaff";
    ctx.lineWidth = 2;
    ctx.strokeRect(r.x, r.y, r.w, r.h);
  }

  for (const b of balls) {
    drawBall(ctx, b);
  }

  if (currentSplit) {
    const s = currentSplit;
    const region = regions.find(r => r.id === s.regionId);
    if (!region) return;

    ctx.strokeStyle = "#ff4444";
    ctx.lineWidth = 2;
    ctx.beginPath();

    if (s.orientation === "vertical") {
      let y1 = s.y + s.progress1;
      let y2 = s.y + s.progress2;
      if (y1 < region.y) y1 = region.y;
      if (y2 > region.y + region.h) y2 = region.y + region.h;
      ctx.moveTo(s.x, y1);
      ctx.lineTo(s.x, y2);
    } else {
      let x1 = s.x + s.progress1;
      let x2 = s.x + s.progress2;
      if (x1 < region.x) x1 = region.x;
      if (x2 > region.x + region.w) x2 = region.x + region.w;
      ctx.moveTo(x1, s.y);
      ctx.lineTo(x2, s.y);
    }

    ctx.stroke();
  }
}
