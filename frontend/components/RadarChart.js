import React from "react";
import _ from "lodash";
import "./chart-plugins";
import { Radar } from "react-chartjs-2";


export default ({ data, loading }) => {
  let radarChartElement;
  if (data !== null) {
    radarChartElement = <Radar
      data={{
        labels: data.radarChartData.benchmark,
        datasets: [{
          label: "Score",
          data: data.radarChartData.score
        }, {
          label: "Tolerated Interference",
          data: data.radarChartData.tolerated_interference
        }]
      }}
      options={{
        scale: {
          ticks: {
            min: 0,
            max: 100,
            stepSize: 20,
            fontSize: 8,
          },
          pointLabels: {
            fontSize: 12
          }
        },
        tooltips: {
          mode: "label"
        }
      }}
    />;
  }
  return <div className="main-container">{radarChartElement}</div>;
}
