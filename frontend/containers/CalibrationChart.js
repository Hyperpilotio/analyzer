import React, { Component } from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import CalibrationChartComponent from "../components/CalibrationChart";


export default class CalibrationChart extends Component {

  state = { data: null, loading: true }

  async fetchData(appId) {
    if (_.isUndefined(_.get(this.props.calibrations, appId))) {
      await this.props.actions.fetchCalibration(appId)
    }
    this.setState({
      data: this.props.calibrations[appId],
      loading: false
    });
  }

  componentDidMount() {
    this.fetchData(this.props.appId);
  }

  componentWillReceiveProps(props) {
    if (props.appId !== this.props.appId) {
      this.setState({loading: true});
      this.fetchData(props.appId);
    }
  }

  render() {
    return <CalibrationChartComponent {...this.state} />
  }
}
module.exports = CalibrationChart;
