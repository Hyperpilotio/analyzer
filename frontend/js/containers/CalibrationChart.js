import React, { Component } from "react";
import CalibrationChartComponent from "../components/CalibrationChart";
import _ from "lodash";


export default class CalibrationChart extends Component {

  state = { data: null, loading: true };

  async fetchData(calibrationId) {
    const res = await fetch(`/api/single-app/calibration-data/${calibrationId}`);
    const data = await res.json();
    this.setState({ data, loading: false });
  }

  componentDidMount() {
    this.fetchData(this.props.calibrationId);
  }

  componentWillReceiveProps(props) {
    if (props.calibrationId !== this.props.calibrationId) {
      this.setState({loading: true});
      this.fetchData(props.calibrationId);
    }
  }

  render() {
    return <CalibrationChartComponent {...this.state} />
  }

}
