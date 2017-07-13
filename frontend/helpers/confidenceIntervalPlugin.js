export default {
  afterDatasetDraw: ({ ctx, chart, config, options, scales }) => {
    ctx.save();
    const xScale = scales["x-axis-0"];
    const yScale = scales["y-axis-0"];
    for (let dataset of config.data.datasets) {
      if (dataset.onlyHighlighted) {

        ctx.strokeStyle = dataset.borderColor;
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let point of dataset.data) {
          const pointX = xScale.getPixelForValue(point.x);
          const bottomY = yScale.getPixelForValue(point.bottom);
          const topY = yScale.getPixelForValue(point.top);
          ctx.moveTo(pointX, bottomY);
          ctx.lineTo(pointX, topY);
          ctx.moveTo(pointX - 3, bottomY);
          ctx.lineTo(pointX + 3, bottomY);
          ctx.moveTo(pointX - 3, topY);
          ctx.lineTo(pointX + 3, topY);
        }
        ctx.stroke();
        break;
      }
    }
    ctx.restore();
  }
}
