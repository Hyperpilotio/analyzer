import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Route, Link } from "react-router-dom";
import ReactEcharts from "echarts-for-react";
import ReactDOM from "react-dom";

class App extends Component {
  render() {
    return <Router>
      <div>
        <Route exact={true} path="/" render={() => <Link to="/calibration/59406aa9e3fd9e5094db7f3b">Redis</Link>} />
        <Route path="/calibration/:calibrationId" component={Calibration} />
      </div>
    </Router>;
  }
}

const Calibration = ({ match }) => (
  <CalibrationChart calibrationId={match.params.calibrationId} />
);

class CalibrationChart extends Component {

  constructor(props) {
    super(props);
    this.state = { option: {series: []} };
  }

  onChartReady(chart) {
    this.chart = chart;
  }

  renderErrorBar(params, api) {
    let xValue = api.value(0);
    let [xCoord, minPoint] = api.coord([xValue, api.value(1)]);
    let [_, maxPoint] = api.coord([xValue, api.value(2)]);

    let style = api.style({
      stroke: api.visual("color")
    });

    return {
      type: "group",
      children: [
        {
          type: "line",
          shape: {
            x1: xCoord, y1: minPoint,
            x2: xCoord, y2: maxPoint
          },
          style: style
        },
        {
          type: "line",
          shape: {
            x1: xCoord - 5, y1: maxPoint,
            x2: xCoord + 5, y2: maxPoint
          },
          style: style
        },
        {
          type: "line",
          shape: {
            x1: xCoord - 5, y1: minPoint,
            x2: xCoord + 5, y2: minPoint
          },
          style: style
        }
      ]
    };
  }

  async componentDidMount() {
    const { calibrationId } = this.props;
    const res = await fetch(`/api/single-app/calibration-data/${calibrationId}`);
    const data = await res.json();
    const minValue = Math.min(...data.map(row => row.min));
    const maxValue = Math.max(...data.map(row => row.max));
    const minX = Math.min(...data.map(row => row.loadIntensity));
    const maxX = Math.max(...data.map(row => row.loadIntensity));
    this.setState({ option: {
      title: {
        text: "Calibration Results",
        subtext: "App: redis, Load Tester: redis-bench",
        left: "center"
      },
      tooltip: {
        trigger: "axis",
        formatter: (params) => {
          let mean = params[0];
          let minMax = params[1];
          return `Load Intesity: ${mean.axisValue}<br />
                  ${mean.marker} Throughput:<br />
                  Mean: ${mean.data[1].toFixed(2)}<br />
                  Min: ${minMax.data[1]}<br />
                  Max: ${minMax.data[2]}`;
        }
      },
      xAxis: [{
        type: "value",
        name: "Load Intensity",
        min: minX - (maxX - minX) * 0.1,
        max: maxX + (maxX - minX) * 0.1
      }],
      yAxis: [{
        name: "Throughput",
        type: "value",
        min: (minValue - (maxValue - minValue) * 0.1).toPrecision(2),
        max: (maxValue + (maxValue - minValue) * 0.1).toPrecision(2)
      }],
      series: [
        {
          name: "throughput",
          type: "line",
          data: data.map(row => [row.loadIntensity, row.mean]),
          markArea: {
            data: [
              [{name: "Final Intensity", xAxis: 39.5}, {xAxis: 42.5}]
            ]
          }
        },
        {
          name: "minmax",
          type: "custom",
          data: data.map(row => [row.loadIntensity, row.min, row.max]),
          renderItem: this.renderErrorBar,
          itemStyle: {
            normal: {
              borderWidth: 1.5
            }
          }
        }
      ]
    } });
    this.chart.hideLoading();
  }

  render() {
    return (
      <ReactEcharts
        style={{height: "500px"}}
        onChartReady={this.onChartReady.bind(this)}
        option={this.state.option}
        showLoading={true} />
    );
  }

}


ReactDOM.render(<App />, document.getElementById("react-root"));
