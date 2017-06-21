import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import ReactEcharts from "echarts-for-react";
import ReactDOM from "react-dom";


class CalibrationChart extends Component {

  constructor() {
    super();
    this.state = { option: {series: []} };
  }

  onChartReady(chart) {
    this.chart = chart;
  }

  async componentDidMount() {
    const res = await fetch("/api/single-app/calibration-data/59406aa9e3fd9e5094db7f3b");
    const data = await res.json();
    this.setState({ option: {
      tooltip: {
        trigger: "axis",
        formatter: (params) => {
          params = params[0];
          return `Load Intesity: ${params.axisValue}<br />${params.marker} ${params.data[1].toFixed(2)}`;
        }
      },
      xAxis: {
        type: "value"
      },
      yAxis: {
        type: "value",
        min: 10000,
        max: 50000
      },
      series: [
        {
          name: "throughput",
          type: "line",
          data: data.map(row => [row.loadIntensity, row.mean])
        }
      ]
    } });
    this.chart.hideLoading();
  }

  render() {
    return <ReactEcharts style={{height: "500px"}} onChartReady={this.onChartReady.bind(this)} option={this.state.option} showLoading={true} />;
  }

}


ReactDOM.render(<CalibrationChart />, document.getElementById("react-root"));
