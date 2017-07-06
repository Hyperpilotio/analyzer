import { Chart } from "react-chartjs-2";
import _ from "lodash";
import { numberWithCommas } from "./util";


Chart.defaults.global.animation.duration = 500;
Chart.defaults.global.defaultFont = "WorkSans";


// Error Bars for Calibration Line Chart
Chart.plugins.register({
  afterDatasetsDraw: ({ ctx, options, scales, data }) => {
    if (options.plugins.errorBars) {
      const xScale = scales["x-axis"];
      const yScale = scales["y-axis-0"];
      // The horizontal little bar is 1% of the whole graph
      const errorBarWidth = (xScale.right - xScale.left) / 100 / 2;
      ctx.lineWidth = 2;
      ctx.strokeStyle = options.plugins.errorBars.strokeStyle || options.elements.line.borderColor;

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


// Final Intensity Marking Area
Chart.plugins.register({
  afterDatasetsDraw: ({ ctx, options, scales }) => {
    if (options.plugins.finalIntensity) {
      const xScale = scales["x-axis"];
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


// Confidence Intervals for Profiling Line Chart
Chart.plugins.register({
  afterDatasetsDraw: ({ ctx, chart, options, scales, data }) => {
    if (options.plugins.confidenceIntervals) {
      const xScale = scales["x-axis"];
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

Chart.plugins.register({
  afterDraw: ({ ctx, options, scales }) => {
    let yScale = scales["y-axis-0"];
    let xScale = scales["x-axis"];
    let xPos = xScale.getPixelForTick(0);
    ctx.fillStyle = "#e5e6e8";
    for (let i = 0; i < yScale.ticks.length - 1; i ++) {
      let yPos = yScale.getPixelForTick(i) + 20;
      ctx.fillText(numberWithCommas(yScale.ticks[i]), xPos, yPos);
    }
  }
});
