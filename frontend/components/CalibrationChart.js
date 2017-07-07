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
        }]
      }}
      options={{
        layout: {
          padding: {
            top: 80
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
            value: data.finalIntensity,
            fillStyle: "rgba(140, 177, 250, 0.2)"
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
