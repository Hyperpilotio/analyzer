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
          data: data.radarChartData.score
        }]
      }}
    />;
  }
  return <div className="main-container">{radarChartElement}</div>;
}
