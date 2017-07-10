import React from "react";
import { Line } from "react-chartjs-2";
import _ from "lodash";
import "chartjs-plugin-annotation";
import "../helpers/chart-plugins";
import drawBackgroundPlugin from "../helpers/drawBackgroundPlugin";

export default ({ name, thresholdColor }) => (
  <Line
    data={{
      datasets: [{
        label: name,
        data: _.range(50).map((__, x) => ({x, y: _.random(1000)})),
        steppedLine: true,
        pointRadius: 0,
        borderWidth: 1,
        borderColor: "#8cb1fa",
        backgroundColor: "rgba(140, 177, 250, 0.5)"
      }]
    }}
    options={{
      layout: {
        padding: { left: -10, right: -10, top: -10, bottom: -10 }
      },
      scales: {
        xAxes: [{
          type: "linear"
        }]
      },
      tooltips: {
        callbacks: {
          title: () => {}
        }
      },
      annotation: {
        annotations: [{
          scaleID: "y-axis-0",
          type: "line",
          mode: "horizontal",
          value: 500,
          borderColor: thresholdColor
        }]
      }
    }}
    plugins={[drawBackgroundPlugin]}
  />
)
