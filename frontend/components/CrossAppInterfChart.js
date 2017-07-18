import React from "react";
import chartWithLoading from "../helpers/chartWithLoading";
import { Radar } from "react-chartjs-2";
import _ from "lodash";
import interferenceTooltipPlugin from "../helpers/interferenceTooltipPlugin";
import drawBackgroundPlugin from "../helpers/drawBackgroundPlugin";
import adjustRadarLabelPlugin from "../helpers/adjustRadarLabelPlugin";
import noTooltipPlugin from "../helpers/noTooltipPlugin";

export default chartWithLoading( ({ data }) => (
  <Radar
    data={{
      labels: ["l2", "l3", "iperf", "memBw", "memCap", "cpu"],
      datasets: [
        {
          label: "MongoDB",
          data: _.range(6).map(() => _.random(100)),
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
        },
        {
          label: "Kafka",
          data: _.range(6).map(() => _.random(100)),
          borderColor: "#b8e986",
          borderWidth: 1,
          backgroundColor: "rgba(184, 233, 134, 0.19)",
          pointRadius: 4,
          pointBackgroundColor: "#b8e986",
          pointBorderColor: "#fff",
          pointBorderWidth: 1,
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: "#b8e986",
          pointHoverRadius: 5
        }
      ]
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
