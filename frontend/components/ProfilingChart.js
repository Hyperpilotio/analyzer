import React, { Component } from "react";
import { Line } from "react-chartjs-2";
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
        }
      }}
    />;
  }
  return <div className="main-container">{lineChartElement}</div>;
}


// export default class ProfilingChart extends Component {

//   confidenceIntervalsHidden = false

//   componentWillReceiveProps(props) {
//     if (!_.isEqual(props.data, this.props.data)) {
//       const originalSeries = this.chart.getOption().series;
//       let newOption = this.makeOptions(props.data);
//       originalSeries.forEach(series => {
//         if (!_.includes(_.map(newOption.series, "name"), series.name)) {
//           newOption.series.push({
//             name: series.name,
//             data: null,
//             markLine: null
//           });
//         }
//       });
//       this.chart.setOption(newOption);
//     }
//   }

//   makeOptions(data) {
//     let options = { series: [] };
//     const flattenedResults = _.flatMap(data.testResult);
//     const minValue = _.min(_.map(flattenedResults, "percentile_10"));
//     const maxValue = _.max(_.map(flattenedResults, "percentile_90"));
//     const yAxisMin = _.max([0, (minValue - (maxValue - minValue) * 0.1).toPrecision(2)]);

//     if (data !== null) {
//       options = {
//         title: {
//           text: "Profiling Results",
//           subtext: `App: ${data.appName}, Service: ${data.serviceInTest}, Load Tester: ${data.loadTester}, App Capacity: ${data.appCapacity}`,
//           left: "center"
//         },
//         toolbox: {
//           feature: {
//             myTogglePercentiles: {
//               title: "Toggle CIs          ",
//               icon: `path://${iconPathCI}`,
//               onclick: () => {
//                 let newOpacity = 0;
//                 if (this.confidenceIntervalsHidden)
//                   newOpacity = 0.5;
//                 this.chart.setOption({
//                   series: this.props.data.benchmarks.map(benchmark => ({
//                     name: benchmark,
//                     markLine: {
//                       lineStyle: {
//                         normal: { opacity: newOpacity }
//                       }
//                     }
//                   }))
//                 });
//                 this.confidenceIntervalsHidden = !this.confidenceIntervalsHidden;
//               }
//             }
//           }
//         },
//         xAxis: {
//           type: "value",
//           name: "Load Intensity"
//         },
//         yAxis: {
//           name: data.sloMetric,
//           type: "value",
//           min: yAxisMin
//         },
//         tooltip: {
//           trigger: "axis",
//           axisPointer: {
//             type: "cross"
//           },
//           formatter: params => {
//             const intensity = params[0].axisValue;
//             const markers = _.join(params.map(series => `
//               <div style="float: left">
//                 ${series.marker} ${series.seriesName}
//               </div>
//               <div style="margin-left: 5px; float: right">
//                 ${series.data[1].toFixed(2)}
//               </div>
//               <div style="clear: both"></div>
//             `));
//             return `Load Intensity: ${intensity}<br />${markers}`;
//           }
//         },
//         legend: {
//           data: _.keys(data.testResult),
//           top: "bottom"
//         },
//         series: _.map(data.testResult, (points, benchmark) => ({
//           name: benchmark,
//           type: "line",
//           symbol: "circle",
//           lineStyle: {
//             normal: {
//               width: 3
//             }
//           },
//           data: points.map(res => [res.intensity, res.mean]),
//           markLine: {
//             data: points.map(res => [
//               {
//                 coord: [ res.intensity, res.percentile_10 ],
//                 symbolSize: 2
//               },
//               {
//                 coord: [ res.intensity, res.percentile_90 ],
//                 symbol: "circle",
//                 symbolSize: 2
//               }
//             ]),
//             lineStyle: {
//               normal: {
//                 width: 2,
//                 type: "solid",
//                 opacity: this.confidenceIntervalsHidden ? 0 : 0.5
//               }
//             }
//           }
//         }))
//       }
//     }
//     return options;
//   }

//   onChartReady(chart) {
//     this.chart = chart;
//   }

//   render() {
//     return <ReactEcharts
//       style={{height: "500px", paddingLeft: "256px"}}
//       option={{ series: [] }}
//       onChartReady={::this.onChartReady}
//       showLoading={this.props.loading}
//     />;
//   }
// }
