import { Chart } from "react-chartjs-2";
import { numberWithCommas, colors } from "./util";
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


Chart.plugins.register({
  afterInit: chart => {
    chart.tooltip.draw = function() {};
  },

  beforeDraw: ({ ctx, chart, scales }) => {
    // Draw background
    ctx.fillStyle = "#f7f9fc";
    if (chart.config.type === "radar")
      ctx.fillRect(0, 0, chart.width, chart.height);
    else
      ctx.fillRect(0, 0, chart.width, chart.chartArea.bottom);

    if (chart.config.type === "line") {
      ctx.lineWidth = 1;
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
    }

  },

  afterDraw: ({ chart, ctx, options, scales }) => {

    ctx.save();

    if (chart.config.type === "line") {
      // Draw ticks
      let yScale = scales["y-axis-0"];
      let xScale = scales["x-axis-0"];
      let xPos = xScale.getPixelForTick(0);
      ctx.fillStyle = "#e5e6e8";
      ctx.textBaseline = "top";
      for (let i = 0; i < yScale.ticks.length - 1; i ++) {
        let yPos = yScale.getPixelForTick(i) + 5;
        ctx.fillText(numberWithCommas(yScale.ticks[i]), xPos, yPos);
      }

      // Draw y-axis title
      ctx.fillStyle = "#b9bacb";
      ctx.font = "14px WorkSans";
      ctx.fillText(yScale.options.scaleLabel.labelString, xPos, 10);

      // Draw x-axis title
      const xLabel = xScale.options.scaleLabel.labelString;
      xPos = xScale.right - ctx.measureText(xLabel).width;
      ctx.fillText(xLabel, xPos, yScale.bottom - 20);
    }

    if (options.plugins.calibration === true) {
      // Draw tooltip
      let xPos;
      const vm = chart.tooltip._view;
      if (!_.isUndefined(chart.tooltip.currentPoints)) {
        let [mean, min, max] = chart.tooltip.currentPoints;
        ctx.textAlign = vm.xAlign;

        let texts = [
          { style: "important", text: mean.xLabel, label: "Load intensity" },
          {
            style: "important",
            text: numberWithCommas(Number(mean.yLabel.toFixed(2))),
            label: "Mean"
          },
          { style: "secondary", text: min.yLabel, label: "Min" },
          { style: "secondary", text: max.yLabel, label: "Max" }
        ];

        if (vm.xAlign === "left")
          xPos = mean.x + 15;
        else
          xPos = mean.x - 15;

        texts.forEach(({ style, text, label }, i) => {
          if (style === "important") {
            ctx.font = "bold 20px WorkSans";
            ctx.fillStyle = "#5677fa";
          } else if (style === "secondary") {
            ctx.font = "bold 16px WorkSans";
            ctx.fillStyle = "#606175";
          }

          // Draw individual staticstic
          let yPos = 5 + 40 * i;
          ctx.fillText(text, xPos, yPos);

          ctx.font = "lighter 10px WorkSans";
          ctx.fillStyle = "#b9bacb";
          // Draw label for statistics
          yPos += 20 + (style === "important") * 5
          ctx.fillText(label, xPos, yPos);
        });

      }

    } else if (options.plugins.profiling === true) {
      // Draw tooltip / legend for profiling charts
      ctx.textAlign = "right";

      const tooltipPoints = chart.tooltip.currentPoints || [];
      for (let point of tooltipPoints) {
        let offset = 30;
        offset += (tooltipPoints.length - point.datasetIndex - 1) * 120;

        // Write statistic
        ctx.fillStyle = colors[point.datasetIndex];
        ctx.font = "bold 20px WorkSans";
        ctx.fillText(
          numberWithCommas(point.yLabel.toFixed(2)),
          chart.chartArea.right - offset,
          20
        );

        // Write benchmark name
        ctx.fillStyle = "#606175";
        ctx.font = "lighter 10px WorkSans";
        ctx.fillText(
          chart.config.data.datasets[point.datasetIndex].label,
          chart.chartArea.right - offset,
          50
        );
      }
    }

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
