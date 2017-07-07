import { Chart } from "react-chartjs-2";
import _ from "lodash";
import { numberWithCommas } from "./util";


Chart.defaults.global.animation.duration = 500;
Chart.defaults.global.defaultFontFamily = "WorkSans";
Chart.defaults.global.tooltips.mode = "x-axis";
Chart.defaults.global.hover.mode = "x-axis";
Chart.defaults.global.hover.intersect = false;
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


Chart.plugins.register({
  afterInit: chart => {
    chart.tooltip.draw = function() {};
  },

  beforeDraw: ({ ctx, chart, scales }) => {
    ctx.fillStyle = "#f7f9fc";
    ctx.fillRect(0, 0, chart.width, chart.chartArea.bottom);

    let yScale = scales["y-axis-0"];
    let xScale = scales["x-axis-0"];
    // Draw grid lines
    ctx.strokeStyle = yScale.options.color;
    ctx.beginPath();
    for (let tick of yScale.ticksAsNumbers) {
      let yPos = yScale.getPixelForValue(tick);
      ctx.moveTo(0, yPos);
      ctx.lineTo(chart.width, yPos);
    }
    ctx.stroke();

    // Draw vertical tooltip bar
    if (_.size(chart.tooltip.currentPoints) >= 1) {
      ctx.strokeStyle = "#8cb1fa";
      const point = chart.tooltip.currentPoints[0];
      ctx.beginPath();
      ctx.moveTo(point.x, 0);
      ctx.lineTo(point.x, chart.chartArea.bottom);
      ctx.stroke();
    }

  },

  afterDraw: ({ chart, ctx, options, scales }) => {

    ctx.save();

    // Draw ticks
    let yScale = scales["y-axis-0"];
    let xScale = scales["x-axis-0"];
    let xPos = xScale.getPixelForTick(0);
    ctx.fillStyle = "#e5e6e8";
    for (let i = 0; i < yScale.ticks.length - 1; i ++) {
      let yPos = yScale.getPixelForTick(i) + 20;
      ctx.fillText(numberWithCommas(yScale.ticks[i]), xPos, yPos);
    }

    // Draw y-axis title
    ctx.fillStyle = "#b9bacb";
    ctx.font = "14px WorkSans";
    ctx.fillText(yScale.options.scaleLabel.labelString, xPos, 25);

    // Draw x-axis title
    const xLabel = xScale.options.scaleLabel.labelString;
    xPos = xScale.right - ctx.measureText(xLabel).width;
    ctx.fillText(xLabel, xPos, yScale.bottom - 15);

    ctx.restore();
  }
});


// Final Intensity Marking Area
Chart.plugins.register({
  beforeDatasetsDraw: ({ ctx, options, scales }) => {
    if (options.plugins.finalIntensity) {
      const xScale = scales["x-axis-0"];
      const yScale = scales["y-axis-0"];
      const intensityAreaWidth = (xScale.right - xScale.left) / 40;
      const pointX = xScale.getPixelForValue(options.plugins.finalIntensity.value);

      if (options.plugins.finalIntensity.fillStyle)
        ctx.fillStyle = options.plugins.finalIntensity.fillStyle;

      ctx.fillRect(
        pointX - intensityAreaWidth / 2, // upper-left x
        0, // upper-left y
        intensityAreaWidth, // width
        yScale.bottom // height
      );
    }
  }
});


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
