import React from "react";
import ChartWithLoading from "./ChartWithLoading";
import { Radar } from "react-chartjs-2";
import "./chart-plugins";

export default ChartWithLoading( ({ data }) => (
  <Radar
    data={{
      labels: data.radarChartData.benchmark,
      datasets: [{
        label: "Score",
        data: data.radarChartData.score
      }]
    }}
    options={{
      layout: {
        padding: { left: 20, top: 20, right: 20, bottom: 20 }
      },
      scale: {
        ticks: {
          min: 0,
          max: 100,
          stepSize: 20,
          fontSize: 8,
        },
        gridLines: {
          display: true
        }
      }
    }}
  />
) )
