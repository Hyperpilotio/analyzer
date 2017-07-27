import _ from "lodash";

export default {
  beforeDraw: ({ ctx, chartArea, tooltip }) => {
    // Draw vertical tooltip bar
    if (_.size(tooltip.currentPoints) >= 1) {
      ctx.strokeStyle = "#8cb1fa";
      const point = tooltip.currentPoints[0];
      ctx.beginPath();
      ctx.moveTo(point.x, 0);
      ctx.lineTo(point.x, chartArea.bottom);
      ctx.stroke();
    }
  }
}
