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
      let dataset = datasets[point.datasetIndex];
      let displayIndex = dataset.displayIndex;
      let offset = 30 + (tooltipPoints.length - displayIndex - 1) * 120;

      // Write statistic
      ctx.fillStyle = dataset.borderColor;
      ctx.font = "bold 20px WorkSans";
      ctx.fillText(
        numberWithCommas(point.yLabel.toFixed(2)),
        chartArea.right - offset,
        20
      );

      // Write benchmark name
      ctx.fillStyle = dataset.highlighted ? "#606175" : "#b9bacb";
      ctx.font = "lighter 10px WorkSans";
      ctx.fillText( dataset.label, chartArea.right - offset, 50 );
    }

    ctx.restore();
  }
}
