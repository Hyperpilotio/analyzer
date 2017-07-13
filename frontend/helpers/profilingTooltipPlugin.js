import { numberWithCommas, colors } from "./util";

export default {
  afterDraw: ({ ctx, chart, chartArea, tooltip }) => {
    ctx.save();

    // Draw tooltip / legend for profiling charts
    ctx.textAlign = "right";
    ctx.textBaseline = "top";

    const tooltipPoints = tooltip.currentPoints || [];
    const { datasets } = chart.config.data;

    for (let point of tooltipPoints) {
      let displayIndex = datasets[point.datasetIndex].displayIndex;
      let offset = 30 + (tooltipPoints.length - displayIndex - 1) * 120;

      // Write statistic
      ctx.fillStyle = datasets[point.datasetIndex].borderColor;
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
        datasets[point.datasetIndex].label,
        chartArea.right - offset,
        50
      );
    }

    ctx.restore();
  }
}
