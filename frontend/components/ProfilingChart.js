import React from "react";
import ChartWithLoading from "./ChartWithLoading";
import { Line } from "react-chartjs-2";
import { colors } from "./util";
import "./chart-plugins";
import _ from "lodash";


export default ChartWithLoading( ({ data }) => (
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
      },
      plugins: {
        profiling: true
      }
    }}
  />
) )
