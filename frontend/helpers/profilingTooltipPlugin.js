import { numberWithCommas, colors } from "./util";

export default {
  afterDraw: ({ ctx, chart, chartArea, tooltip }) => {
    ctx.save();

    // Draw tooltip / legend for profiling charts
    ctx.textAlign = "right";
    ctx.textBaseline = "top";

    const tooltipPoints = tooltip.currentPoints || [];
    for (let point of tooltipPoints) {
      let offset = 30;
      offset += (tooltipPoints.length - point.datasetIndex - 1) * 120;

      // Write statistic
      ctx.fillStyle = colors[point.datasetIndex];
      ctx.font = "bold 20px WorkSans";
      ctx.fillText(
        numberWithCommas(point.yLabel.toFixed(2)),
        chartArea.right - offset,
        20
      );

      // Write benchmark name
      ctx.fillStyle = "#606175";
      ctx.font = "lighter 10px WorkSans";
      ctx.fillText(
        chart.config.data.datasets[point.datasetIndex].label,
        chartArea.right - offset,
        50
      );
    }

    ctx.restore();
  }
}
