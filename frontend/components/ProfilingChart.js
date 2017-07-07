import React, { PureComponent } from "react";
import { Line } from "react-chartjs-2";
import "./chart-plugins";
import _ from "lodash";


const colors = ["#c1ccf9", "#8cb1fa", "#acaecd", "#e5e6e8", "#78c1fa", "#6590e2"];

export default class ProfilingChart extends PureComponent {

  createLineChart(data) {
    let flattenedResults = _.flatMap(data.testResult);
    return <Line
      data={{
        datasets: _.entries(data.testResult).map(([benchmark, points], i) => ({
          label: benchmark,
          data: points.map(row => ({ x: row.intensity, y: row.mean })),
          fill: false,
          borderColor: colors[i],
          pointRadius: 0,
          pointHoverBorderColor: "#5677fa",
          pointHoverBackgroundColor:  "#fff",
          pointHoverRadius: 5
        }))
      }}
      options={{
        layout: {
          padding: {
            top: 80
          }
        },
        scales: {
          xAxes: [{
            type: "linear",
            ticks: {
              fontColor: "#e5e6e8",
              display: true,
              min: 0,
              max: 110,
              stepSize: 25,
              callback: x => x === 110 ? null : x
            },
          }],
          yAxes: [{
            color: "#eef0fa",
            scaleLabel: {
              labelString: "QoS Value"
            }
          }]
        }
      }}
    />;
  }

  render() {
    return (
      <div className="chart-container">
        { this.props.data && this.createLineChart(this.props.data) }
        { this.props.loading && "Loading" }
      </div>
    );
  }

}
