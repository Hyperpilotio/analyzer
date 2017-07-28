import React, { Component } from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import ProfilingChartComponent from "../components/ProfilingChart";


export default class ProfilingChart extends Component {

  state = { data: null, loading: true };

  async fetchData(appId, serviceName) {
    if (!_.has(this.props.profilings, `${appId}-${serviceName}`)) {
      await this.props.actions.fetchProfiling(appId, serviceName)
    }
    this.setState({
      data: this.props.profilings[`${appId}-${serviceName}`],
      loading: false
    });
  }

  componentDidMount() {
    this.fetchData(this.props.appId, this.props.serviceName);
  }

  componentWillReceiveProps(props) {
    if (props.appId !== this.props.appId || props.serviceName !== this.props.serviceName) {
      this.setState({loading: true});
      this.fetchData(props.appId, props.serviceName);
    }
  }

  render() {
    return <ProfilingChartComponent {...this.state} />
  }

}
module.exports = ProfilingChart;
