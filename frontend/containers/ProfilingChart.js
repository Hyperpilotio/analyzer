import React, { Component } from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import ProfilingChartComponent from "../components/ProfilingChart";


export default class ProfilingChart extends Component {

  static contextTypes = {
    store: PropTypes.object,
    actions: PropTypes.object
  }

  state = { data: null, loading: true };

  async fetchData(appId) {
    if (_.isUndefined(_.get(this.context.store.profilings, appId))) {
      await this.context.actions.fetchProfiling(appId)
    }
    this.setState({
      data: this.context.store.profilings[appId],
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
    return <ProfilingChartComponent {...this.state} />
  }

}
