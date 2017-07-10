import React from "react";
import ChartWithLoading from "../helpers/ChartWithLoading";
import { Line } from "react-chartjs-2";
import "../helpers/chart-plugins";
import noTooltipPlugin from "../helpers/noTooltipPlugin";
import finalIntensityPlugin from "../helpers/finalIntensityPlugin";
import calibrationTooltipPlugin from "../helpers/calibrationTooltipPlugin";
import yAxisGridLinesPlugin from "../helpers/yAxisGridLinesPlugin";
import drawBackgroundPlugin from "../helpers/drawBackgroundPlugin";
import tooltipBarPlugin from "../helpers/tooltipBarPlugin";
import drawLabelsPlugin from "../helpers/drawLabelsPlugin";

export default ChartWithLoading( ({ data }) => (
  <Line
    data={{
      datasets: [
        {
          label: "mean",
          data: data.testResult.map(
            point => ({ x: point.loadIntensity, y: point.mean })
          ),
          borderColor: "#5677fa",
          borderWidth: 2,
          backgroundColor: "rgba(86, 119, 250, 0.08)",
          pointBackgroundColor: "#5677fa",
          pointBorderColor: "#fff",
          pointBorderWidth: 1,
          pointRadius: 4,
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: "#5677fa",
          pointHoverRadius: 5
        },
        // Add hidden min and max datasets to make getting data for tooltips easier
        ...["min", "max"].map(metric => ({
          data: data.testResult.map(
            point => ({ x: point.loadIntensity, y: point[metric] })
          ),
          label: metric,
          showLine: false,
          pointRadius: 0,
          pointHoverRadius: 0
        }))
      ]
    }}
    options={{
      layout: {
        padding: {
          top: 100
        }
      },
      legend: {
        display: false
      },
      scales: {
        xAxes: [{
          type: "linear",
          ticks: {
            fontColor: "#e5e6e8",
            display: true
          },
          scaleLabel: {
            labelString: "Load Intensity"
          }
        }],
        yAxes: [{
          color: "#eef0fa",
          scaleLabel: {
            labelString: "Throughput"
          }
        }]
      },
      plugins: {
        finalIntensity: {
          value: data.finalResult.loadIntensity,
          fillStyle: "rgba(140, 177, 250, 0.2)"
        }
      }
    }}
    plugins={[
      drawBackgroundPlugin,
      tooltipBarPlugin,
      finalIntensityPlugin,
      calibrationTooltipPlugin,
      yAxisGridLinesPlugin,
      drawLabelsPlugin,
      noTooltipPlugin
    ]}
  />
) )
