import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Route, Link } from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import Drawer from "material-ui/Drawer";
import MenuItem from "material-ui/MenuItem";
import ReactEcharts from "echarts-for-react";
import ReactDOM from "react-dom";
import _ from "lodash";

import injectTapEventPlugin from "react-tap-event-plugin";
injectTapEventPlugin();

class App extends Component {
  render() {
    return <Router>
      <MuiThemeProvider>
        <div>
          <Navbar />
          <Route path="/calibration/:calibrationId" component={Calibration} />
        </div>
      </MuiThemeProvider>
    </Router>;
  }
}

class Navbar extends Component {

  constructor(props) {
    super(props);
    this.state = { calibration: [] };
  }

  async componentDidMount() {
    const res = await fetch("/api/available-apps");
    const data = await res.json();
    this.setState({ calibration: data.calibration });
  }

  render() {
    return (
      <Drawer open>
        {this.state.calibration.map((item, i) => (
          <MenuItem key={i}>
            <Link to={`/calibration/${item._id}`}
                  style={{color: "black", textDecoration: "none"}}>
              {item.appName} ({_.truncate(item._id, { length: 12 })})
            </Link>
          </MenuItem>
        ))}
      </Drawer>
    );
  }
}

const Calibration = ({ match }) => (
  <CalibrationChart calibrationId={match.params.calibrationId} />
);

class CalibrationChart extends Component {

  constructor(props) {
    super(props);
    this.state = { option: {series: []}, loading: true };
  }

  componentWillReceiveProps(props) {
    if (props.calibrationId !== this.props.calibrationId) {
      this.setState({loading: true});
      this.fetchData(props.calibrationId);
    }
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

  async fetchData(calibrationId) {
    const res = await fetch(`/api/single-app/calibration-data/${calibrationId}`);
    const data = await res.json();
    const results = data.testResult;

    const minValue = _.min(_.map(results, "min"));
    const maxValue = _.max(_.map(results, "max"));
    const minX = _.min(_.map(results, "loadIntensity"));
    const maxX = _.max(_.map(results, "loadIntensity"));

    const finalIntensityIndex = _.findIndex(results, {loadIntensity: data.finalIntensity});

    this.setState({
      option: {
        title: {
          text: "Calibration Results",
          subtext: `App: ${data.appName}, Load Tester: ${data.loadTester}, Final Intensity: ${data.finalIntensity}`,
          left: "center"
        },
        tooltip: {
          trigger: "axis",
          formatter: (params) => {
            let mean = params[0];
            let minMax = params[1];
            return `Load Intesity: ${mean.axisValue}<br />
                    ${mean.marker} ${data.qosMetrics[0]}:<br />
                    Mean: ${mean.data[1].toFixed(2)}<br />
                    Min: ${minMax.data[1]}<br />
                    Max: ${minMax.data[2]}`;
          }
        },
        xAxis: [{
          type: "value",
          name: "Load Intensity",
          min: (minX - (maxX - minX) * 0.1).toPrecision(2),
          max: (maxX + (maxX - minX) * 0.1).toPrecision(2)
        }],
        yAxis: [{
          name: data.qosMetrics[0],
          type: "value",
          min: (minValue - (maxValue - minValue) * 0.1).toPrecision(2),
          max: (maxValue + (maxValue - minValue) * 0.1).toPrecision(2)
        }],
        series: [
          {
            name: data.qosMetrics[0],
            type: "line",
            data: results.map(row => [row.loadIntensity, row.mean]),
            markArea: {
              data: [
                [
                  { name: "Final Intensity",
                    xAxis: data.finalIntensity - (data.finalIntensity - results[finalIntensityIndex - 1].loadIntensity) / 2 },
                  { xAxis: data.finalIntensity + (results[finalIntensityIndex + 1].loadIntensity - data.finalIntensity) / 2 }
                ]
              ]
            }
          },
          {
            name: "minmax",
            type: "custom",
            data: results.map(row => [row.loadIntensity, row.min, row.max]),
            renderItem: this.renderErrorBar,
            itemStyle: {
              normal: {
                borderWidth: 1.5,
                color: "#77bef7"
              }
            }
          }
        ]
      },
      loading: false
    });
  }

  componentDidMount() {
    this.fetchData(this.props.calibrationId);
  }

  render() {
    return (
      <ReactEcharts
        style={{height: "500px", paddingLeft: "256px"}}
        onChartReady={this.onChartReady.bind(this)}
        option={this.state.option}
        showLoading={this.state.loading} />
    );
  }

}


ReactDOM.render(<App />, document.getElementById("react-root"));
