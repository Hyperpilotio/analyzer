import React, { Component } from "react";
import ReactEcharts from "echarts-for-react";
import _ from "lodash";


export default class ProfilingChart extends Component {

  componentWillReceiveProps(props) {
    if (!_.isEqual(props.data, this.props.data)) {
      this.chart.clear();
      this.chart.setOption(this.makeOptions(props.data));
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
