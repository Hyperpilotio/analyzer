import React from "react";
import { Line } from "react-chartjs-2";
import _ from "lodash";
import chartWithLoading from "../helpers/chartWithLoading";
import { colors } from "../helpers/util";
import profilingTooltipPlugin from "../helpers/profilingTooltipPlugin";
import yAxisGridLinesPlugin from "../helpers/yAxisGridLinesPlugin";
import drawBackgroundPlugin from "../helpers/drawBackgroundPlugin";
import tooltipBarPlugin from "../helpers/tooltipBarPlugin";
import drawLabelsPlugin from "../helpers/drawLabelsPlugin";
import noTooltipPlugin from "../helpers/noTooltipPlugin";


export default chartWithLoading( ({ data }) => (
  <Line
    data={{
      datasets: _.entries(data.testResult).map(([benchmark, points], i) => ({
        label: benchmark,
        data: points.map(row => ({ x: row.intensity, y: row.mean })),
        fill: false,
        borderColor: colors[i],
        pointRadius: 0,
        pointHoverBorderColor: "#5677fa",
        pointHoverBackgroundColor:  "#fff",
        pointHoverRadius: 5
      }))
    }}
    options={{
      layout: {
        padding: {
          top: 80
        }
      },
      scales: {
        xAxes: [{
          type: "linear",
          ticks: {
            fontColor: "#e5e6e8",
            display: true,
            min: 0,
            max: 110,
            stepSize: 25,
            callback: x => x === 110 ? null : x
          },
        }],
        yAxes: [{
          color: "#eef0fa",
          scaleLabel: {
            labelString: "QoS Value"
          }
        }]
      }
    }}
    plugins={[
      drawBackgroundPlugin,
      yAxisGridLinesPlugin,
      drawLabelsPlugin,
      noTooltipPlugin,
      tooltipBarPlugin,
      profilingTooltipPlugin
    ]}
  />
) )
