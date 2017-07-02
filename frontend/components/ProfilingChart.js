import React, { Component } from "react";
import { Line } from "react-chartjs-2";
import CircularProgress from "material-ui/CircularProgress";
import "./chart-plugins";
import _ from "lodash";


export default ({ data, loading }) => {
  let lineChartElement;
  if (data !== null) {
    let flattenedResults = _.flatMap(data.testResult);
    lineChartElement = <Line
      data={{
        datasets: _.map(data.testResult, (points, benchmark) => ({
          label: benchmark,
          data: points.map(row => ({ x: row.intensity, y: row.mean })),
          xAxisID: "x-axis",
          fill: false,
          lineTension: 0
        }))
      }}
      options={{
        scales: {
          xAxes: [{
            id: "x-axis",
            type: "linear",
            ticks: {
              min: 0,
              max: 110,
              stepSize: 25,
              callback: x => x === 110 ? null : x
            }
          }],
          yAxes: [{
            type: "linear",
            ticks: {
              suggestedMin: _.min(_.map(flattenedResults, "percentile_10")),
              suggestedMax: _.max(_.map(flattenedResults, "percentile_90"))
            }
          }]
        },
        tooltips: {
          mode: "label",
          intersect: false,
          callbacks: {
            title: items => `Intensity: ${items[0].xLabel}`,
            label: (item, { datasets }) => (
              `${datasets[item.datasetIndex].label}: ${item.yLabel.toFixed(2)}`
            )
          }
        },
        plugins: {
          confidenceIntervals: {
            datasets: _.map(data.testResult, (points, benchmark) => ({
              data: _.map(points, point => ({
                x: point.intensity,
                top: point.percentile_10,
                bottom: point.percentile_90
              }))
            }))
          }
        }
      }}
    />;
  }

  let divForLoading;
  if (loading)
    divForLoading = <div className="loading-container"><CircularProgress /></div>;

  return <div className="main-container">{lineChartElement}{divForLoading}</div>;
}
