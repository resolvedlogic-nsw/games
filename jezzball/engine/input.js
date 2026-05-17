import { startSplitAt } from "./split.js";
import { regions } from "./regions.js";

export function setupInput(canvas) {
  canvas.addEventListener("contextmenu", e => {
    e.preventDefault(); // disable context menu only on canvas
  });

  canvas.addEventListener("mousedown", e => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    let orientation;
    if (e.button === 0) {
      orientation = "vertical";   // left click
    } else if (e.button === 2) {
      orientation = "horizontal"; // right click
    } else {
      return;
    }

    startSplitAt(x, y, orientation, regions);
  });
}
