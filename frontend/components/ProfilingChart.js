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
            data: null
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
        series: _.map(data.testResult, (points, benchmark) => ({
          name: benchmark,
          type: "line",
          data: points.map(res => [res.intensity, res.mean])
        }))
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
