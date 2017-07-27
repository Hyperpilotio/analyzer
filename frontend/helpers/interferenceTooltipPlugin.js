import _ from "lodash";

export default {
  afterDraw: ({ ctx, chart, chartArea, scale, tooltip }) => {
    ctx.save();

    // Draw tooltip content at the top-right corner
    ctx.textAlign = "right";
    _.each(tooltip.currentPoints, (point, i, all) => {
      let dataset = chart.data.datasets[point.datasetIndex];

      // Use smaller text if it's cross-app interference chart
      if (all.length > 1)
        ctx.font = "bold 18px WorkSans";
      else
        ctx.font = "bold 25px WorkSans";

      ctx.fillStyle = dataset.borderColor;

      // Fill multi-line text if it's cross-app interference chart
      let text = `${Number(point.yLabel.toFixed(2))}%`;
      if (all.length > 1)
        text = `${dataset.label}: ${text}`;

      ctx.fillText(text, chartArea.right, chartArea.top + 30 * i);

      // Add benchmark name if it's reaching the last element
      if (i === all.length - 1) {
        ctx.font = "lighter 15px WorkSans";
        ctx.fillStyle = "#b9bacb";
        ctx.fillText(
          scale.pointLabels[tooltip.currentPoints[0].index],
          chartArea.right,
          chartArea.top + (tooltip.currentPoints.length - 1) * 30 + 30
        );
      }
    });

    ctx.restore();
  }
}
