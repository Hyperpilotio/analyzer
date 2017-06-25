import React, { Component } from "react";
import ReactEcharts from "echarts-for-react";
import _ from "lodash";


export default class ProfilingChart extends Component {

  componentWillReceiveProps(props) {
    if (!_.isEqual(props.data, this.props.data)) {
      const originalSeries = this.chart.getOption().series;
      let newOption = ProfilingChart.makeOptions(props.data);
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

  static makeOptions(data) {
    let options = { series: [] };
    const flattenedResults = _.flatMap(data.testResult);
    const minValue = _.min(_.map(flattenedResults, "percentile_10"));
    const maxValue = _.max(_.map(flattenedResults, "percentile_90"));
    const yAxisMin = _.max([0, (minValue - (maxValue - minValue) * 0.1).toPrecision(2)]);

    if (data !== null) {
      options = {
        xAxis: {
          type: "value",
          name: "Load Intensity"
        },
        yAxis: {
          name: data.sloMetric,
          type: "value",
          min: yAxisMin
        },
        tooltip: {
          trigger: "axis",
          axisPointer: {
            type: "cross"
          },
          formatter: params => {
            let intensity = params[0].axisValue;
            let s = `Load Intensity: ${intensity}<br />`
            for (let series of params) {
              s += `${series.marker} ${series.seriesName} ${series.data[1].toFixed(2)}<br />`
            }
            return s;
          }
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
