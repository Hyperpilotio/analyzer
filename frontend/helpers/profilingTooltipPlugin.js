import { numberWithCommas } from "./util";

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
      let offset = 30 + (datasets.length - displayIndex - 1) * 120;
      let xPos = chartArea.right - offset;
      let dataPoint = dataset.data[point.index] || {y: NaN, top: NaN, bottom: NaN};

      // Write statistic
      ctx.fillStyle = dataset.borderColor;
      ctx.font = "bold 20px WorkSans";
      ctx.fillText( numberWithCommas(dataPoint.y.toFixed(2)), xPos, 20 );

      // Write benchmark name
      ctx.fillStyle = dataset.highlighted ? "#606175" : "#b9bacb";
      ctx.font = "lighter 10px WorkSans";
      ctx.fillText( dataset.label, xPos, 50 );

      if (dataset.onlyHighlighted) {
        // Draw 10th and 90th percentile stats
        ctx.fillStyle = "#606175";
        ctx.font = "lighter 16px WorkSans";
        ctx.fillText( numberWithCommas(dataPoint.bottom.toFixed(2)), xPos, 65 );
        ctx.fillText( numberWithCommas(dataPoint.top.toFixed(2)), xPos, 105 );

        // Draw 10th and 90th percentile labels
        ctx.fillStyle = "#b9bacb";
        ctx.font = "lighter 12px WorkSans";
        ctx.fillText("10th percentile", xPos, 85);
        ctx.fillText("90th percentile", xPos, 125);
      }
    }

    ctx.restore();
  }
}
