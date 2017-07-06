import React from "react";
import { Line } from "react-chartjs-2";
import "./chart-plugins";
// import CircularProgress from "material-ui/CircularProgress";
import _ from "lodash";


export default ({ data, loading }) => {
  let lineChartElement;
  if (data !== null) {
    lineChartElement = <Line
      height={500}
      data={{
        datasets: [{
          label: "Calibration",
          data: data.testResult.map(
            point => ({ x: point.loadIntensity, y: point.mean })
          ),
          xAxisID: "x-axis",
          lineTension: 0,
          borderColor: "#5677fa",
          borderWidth: 2,
          backgroundColor: "rgba(86, 119, 250, 0.08)",
          pointBackgroundColor: "#5677fa",
          pointBorderColor: "#fff",
          pointBorderWidth: 1,
          pointRadius: 4,
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: "#5677fa"
        }]
      }}
      options={{
        maintainAspectRatio: false,
        layout: {
          padding: {
            top: 50,
          }
        },
        legend: {
          display: false
        },
        scales: {
          xAxes: [{
            id: "x-axis",
            type: "linear",
            gridLines: {
              display: false
            }
          }],
          yAxes: [{
            color: "#eef0fa",
            gridLines: {
              drawBorder: false
            },
            ticks: {
              display: false
            }
          }]
        },
        tooltips: {
          enabled: false
        },
        hover: {
          mode: "x-axis"
        },
        plugins: {
          finalIntensity: {
            value: data.finalIntensity,
            fillStyle: "rgba(140, 177, 250, 0.2)"
          }
        },
        ticks: {
          callbacks: {
            beforeBuildTicks: function() {
              console.log(arguments);
            }
          }
        }
      }}
    />;
  }

  let divForLoading;
  if (loading)
    divForLoading = "Loading";
    // divForLoading = <div className="loading-container"><CircularProgress /></div>;

  return <div className="chart-container">{lineChartElement}{divForLoading}</div>;
}
