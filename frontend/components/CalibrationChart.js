import React, { Component } from "react";
import { Chart, Line } from "react-chartjs-2";
import CircularProgress from "material-ui/CircularProgress";
import _ from "lodash";


Chart.plugins.register({
  afterDatasetsDraw: ({ ctx, options, scales, data, ...props }) => {
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

Chart.plugins.register({
  afterDatasetsDraw: ({ ctx, options, scales, data }) => {
    if (options.plugins.finalIntensity) {
      const xScale = scales["x-axis"];
      const yScale = scales["y-axis-0"];
      const intensityAreaWidth = (xScale.right - xScale.left) / 40;
      const pointX = xScale.getPixelForValue(options.plugins.finalIntensity.value);

      if (options.plugins.finalIntensity.fillStyle)
        ctx.fillStyle = options.plugins.finalIntensity.fillStyle;

      ctx.fillRect(
        pointX - intensityAreaWidth / 2, // upper-left x
        yScale.top, // upper-left y
        intensityAreaWidth, // width
        yScale.bottom - yScale.top // height
      );
    }
  }
});


export default ({ data, loading }) => {
  let lineChartElement;
  if (data !== null) {
    lineChartElement = <Line
      data={{
        datasets: [{
          label: "Calibration",
          data: data.testResult.map(
            point => ({ x: point.loadIntensity, y: point.mean })
          ),
          xAxisID: "x-axis",
          lineTension: 0
        }]
      }}
      options={{
        scales: {
          xAxes: [{
            id: "x-axis",
            type: "linear"
          }],
          yAxes: [{
            type: "linear",
            ticks: {
              suggestedMin: _.min(_.map(data.testResult, "min")),
              suggestedMax: _.max(_.map(data.testResult, "max"))
            }
          }]
        },
        tooltips: {
          intersect: false
        },
        plugins: {
          errorBars: {
            top: data.testResult.map(
              point => ({ x: point.loadIntensity, y: point.max })
            ),
            bottom: data.testResult.map(
              point => ({ x: point.loadIntensity, y: point.min })
            ),
            strokeStyle: "rgba(0,0,255,0.4)"
          },
          finalIntensity: {
            value: data.finalIntensity,
            fillStyle: "rgba(255,0,0,0.3)"
          }
        }
      }}
    />;
  }

  let divForLoading;
  if (loading) {
    divForLoading = <div className="loading-container"><CircularProgress /></div>
  }
  return <div className="main-container">{lineChartElement}{divForLoading}</div>;
}
