import { Chart } from "react-chartjs-2";
import _ from "lodash";
// Importing styles to ensure the font is loaded
import "../styles/index.sass";


Chart.defaults.global.animation.duration = 1000;
Chart.defaults.global.defaultFontFamily = "WorkSans";
Chart.defaults.global.tooltips.mode = "x-axis";
Chart.defaults.global.hover.mode = "x-axis";
Chart.defaults.global.hover.intersect = false;
Chart.defaults.global.legend.display = false;
Chart.defaults.global.maintainAspectRatio = false;
Chart.defaults.global.elements.line.tension = 0;
Chart.defaults.scale.gridLines.drawBorder = false;
Chart.defaults.scale.gridLines.display = false;
Chart.defaults.scale.ticks.display = false;


Chart.defaults.global.tooltips.custom = function(tooltip) {
  // Store currently hovered data points
  if (!_.isUndefined(tooltip.dataPoints)) {
    this.currentPoints = tooltip.dataPoints;
  }
}


/////////////////// Currently unused plugins below ///////////////////

// Error Bars for Calibration Line Chart
Chart.plugins.register({
  afterDatasetsDraw: ({ ctx, options, scales, data }) => {
    if (options.plugins.errorBars) {
      const xScale = scales["x-axis-0"];
      const yScale = scales["y-axis-0"];
      // The horizontal little bar is 1% of the whole graph
      const errorBarWidth = (xScale.right - xScale.left) / 100 / 2;
      ctx.lineWidth = 2;
      ctx.strokeStyle = options.plugins.errorBars.strokeStyle;

      for (let fraction of ["top", "bottom"]) {
        if (options.plugins.errorBars[fraction]) {
          for (let [index, point] of _.entries(options.plugins.errorBars[fraction])) {
            // Calculate pixel points
            let pointX = xScale.getPixelForValue(point.x);
            let pointY = yScale.getPixelForValue(point.y);
            let meanPoint = data.datasets[0].data[index];
            let meanPointX = xScale.getPixelForValue(meanPoint.x);
            let meanPointY = yScale.getPixelForValue(meanPoint.y);
            // Draw the bar from the mean point to the min/max point
            ctx.beginPath();
            ctx.moveTo(meanPointX, meanPointY);
            ctx.lineTo(pointX, pointY);
            ctx.stroke();
            // Draw the horizontal bar
            ctx.beginPath();
            ctx.moveTo(pointX - errorBarWidth, pointY);
            ctx.lineTo(pointX + errorBarWidth, pointY);
            ctx.stroke();
          }
        }
      }
    }
  }
});


// Confidence Intervals for Profiling Line Chart
Chart.plugins.register({
  afterDatasetsDraw: ({ ctx, chart, options, scales, data }) => {
    if (options.plugins.confidenceIntervals) {
      const xScale = scales["x-axis-0"];
      const yScale = scales["y-axis-0"];
      // Each benchmarks drawn as different datasets
      for (let dataset of options.plugins.confidenceIntervals.datasets) {
        ctx.strokeStyle = dataset.strokeStyle || options.elements.line.borderColor;
        ctx.lineWidth = dataset.lineWidth || options.elements.line.borderWidth;

        for (let point of dataset.data) {
          const pointX = xScale.getPixelForValue(point.x);
          const bottomY = yScale.getPixelForValue(point.bottom);
          const topY = yScale.getPixelForValue(point.top);
          // Stroke confidence interval
          ctx.beginPath();
          ctx.moveTo(pointX, bottomY);
          ctx.lineTo(pointX, topY);
          ctx.stroke();
        }
      }
    }
  }
});
