import React, { Component } from "react";
import ReactEcharts from "echarts-for-react";
import _ from "lodash";


export default class ProfilingChart extends Component {

  componentWillReceiveProps(props) {
    if (!_.isEqual(props.data, this.props.data)) {
      const originalSeries = this.chart.getOption().series;
      let newOption = this.makeOptions(props.data);
      originalSeries.forEach(series => {
        if (!_.includes(_.map(newOption.series, "name"), series.name)) {
          newOption.series.push({
            name: series.name,
            data: null,
            markLine: null
          });
        }
      });
      this.chart.setOption(newOption);
    }
  }

  makeOptions(data) {
    let options = { series: [] };

    if (data !== null) {
      options = {
        xAxis: {
          type: "value",
          name: "Load Intensity"
        },
        yAxis: {
          name: data.sloMetric,
          type: "value"
        },
        tooltip: {
          trigger: "axis"
        },
        legend: {
          data: _.keys(data.testResult)
        },
        series: _.concat(..._.map(data.testResult, (points, benchmark) => [
          {
            name: benchmark,
            type: "line",
            symbol: "circle",
            lineStyle: {
              normal: {
                width: 3
              }
            },
            data: points.map(res => [res.intensity, res.mean]),
            markLine: {
              data: points.map(res => [
                {
                  coord: [ res.intensity, res.percentile_10 ],
                  symbolSize: 2
                },
                {
                  coord: [ res.intensity, res.percentile_90 ],
                  symbol: "circle",
                  symbolSize: 2,
                  lineStyle: {
                    normal: { width: 2, type: "solid", opacity: 0.5 }
                  }
                }
              ])
            }
          }
        ]))
      }
    }
    return options;
  }

  onChartReady(chart) {
    this.chart = chart;
  }

  render() {
    return <ReactEcharts
      style={{height: "500px", paddingLeft: "256px"}}
      option={{ series: [] }}
      onChartReady={::this.onChartReady}
      showLoading={this.props.loading}
    />;
  }
}
