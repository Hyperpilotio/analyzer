import React from "react";
import chartWithLoading from "../helpers/chartWithLoading";
import { Radar } from "react-chartjs-2";
import interferenceTooltipPlugin from "../helpers/interferenceTooltipPlugin";
import drawBackgroundPlugin from "../helpers/drawBackgroundPlugin";
import adjustRadarLabelPlugin from "../helpers/adjustRadarLabelPlugin";
import noTooltipPlugin from "../helpers/noTooltipPlugin";

export default chartWithLoading( ({ data }) => (
  <Radar
    data={{
      labels: data.radarChartData.benchmark,
      datasets: [{
        label: "Score",
        data: data.radarChartData.score,
        borderColor: "#5677fa",
        borderWidth: 1,
        backgroundColor: "rgba(86, 119, 250, 0.08)",
        pointRadius: 4,
        pointBackgroundColor: "#5677fa",
        pointBorderColor: "#fff",
        pointBorderWidth: 1,
        pointHoverBackgroundColor: "#fff",
        pointHoverBorderColor: "#5677fa",
        pointHoverRadius: 5
      }]
    }}
    options={{
      layout: {
        padding: { left: 20, top: 20, right: 20, bottom: 20 }
      },
      hover: {
        mode: "index",
        intersect: true
      },
      tooltips: {
        mode: "index",
        intersect: true
      },
      scale: {
        ticks: {
          min: 0,
          max: 100,
          stepSize: 20
        },
        pointLabels: {
          fontSize: 14,
          fontColor: "#606175"
        },
        gridLines: {
          display: true,
          color: "#e5e6e8"
        }
      },
      plugins: {
        background: {
          fluid: true
        }
      }
    }}
    plugins={[
      interferenceTooltipPlugin,
      drawBackgroundPlugin,
      adjustRadarLabelPlugin,
      noTooltipPlugin
    ]}
  />
) )
