import React from "react";
import { Line } from "react-chartjs-2";
import "./chart-plugins";
import CircularProgress from "material-ui/CircularProgress";
import _ from "lodash";


export default ({ data, loading }) => {
  let lineChartElement;
  if (data !== null) {
    lineChartElement = <Line
      data={{
        datasets: [{
          label: "Calibration",
          data: data.testResult.map(
            point => ({ x: point.loadIntensity, y: point.mean })
          ),
          xAxisID: "x-axis",
          lineTension: 0
        }]
      }}
      options={{
        scales: {
          xAxes: [{
            id: "x-axis",
            type: "linear"
          }],
          yAxes: [{
            type: "linear",
            ticks: {
              suggestedMin: _.min(_.map(data.testResult, "min")),
              suggestedMax: _.max(_.map(data.testResult, "max"))
            }
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
            strokeStyle: "rgba(0,0,255,0.4)"
          },
          finalIntensity: {
            value: data.finalIntensity,
            fillStyle: "rgba(255,0,0,0.3)"
          }
        }
      }}
    />;
  }

  let divForLoading;
  if (loading) {
    divForLoading = <div className="loading-container"><CircularProgress /></div>
  }
  return <div className="main-container">{lineChartElement}{divForLoading}</div>;
}
