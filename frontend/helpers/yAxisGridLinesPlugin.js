export default {
  beforeDraw: ({ ctx, scales, chart }) => {
    ctx.save();

    ctx.lineWidth = 1;
    let yScale = scales["y-axis-0"];
    // Draw grid lines
    ctx.strokeStyle = yScale.options.color;
    ctx.beginPath();
    for (let tick of yScale.ticksAsNumbers) {
      let yPos = yScale.getPixelForValue(tick);
      ctx.moveTo(0, yPos);
      ctx.lineTo(chart.width, yPos);
    }
    ctx.stroke();

    ctx.restore();
  }
}
