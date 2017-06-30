import React, { Component } from "react";
import { Line } from "react-chartjs-2";
import _ from "lodash";


class LineWithErrorBars extends Component {

  static errorBarsPlugin = {
    afterDatasetsDraw: ({ chart, ctx, options, scales, data }) => {
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
  }

  render() {
    return (
      <Line
        plugins={_
          .get(this.props, "plugins", [])
          .concat([LineWithErrorBars.errorBarsPlugin])}
        {..._.omit(this.props, "plugins")} />
    );
  }
}

export default ({ data, loading }) => {
  let element = <div>loading</div>;
  if (!loading) {
    element = <LineWithErrorBars
      data={{
        datasets: [{
          label: "Calibration",
          data: data.testResult.map(
            point => ({ x: point.loadIntensity, y: point.mean })
          ),
          xAxisID: "x-axis"
        }]
      }}
      options={{
        scales: {
          xAxes: [{
            id: "x-axis",
            type: "linear"
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
            strokeStyle: "rgba(0,0,0,0.4)"
          }
        }
      }}
    />;
  }
  return <div className="main-container">{element}</div>;
}
