import React, { Component } from "react";
import PropTypes from "prop-types";
import InterferenceChartComponent from "../components/InterferenceChart";


export default class InterferenceChart extends Component {

  static contextTypes = {
    store: PropTypes.object,
    actions: PropTypes.object
  }

  state = { data: null, loading: true };

  async fetchData(appId) {
    if (_.isUndefined(_.get(this.context.store.interferences, appId))) {
      await this.context.actions.fetchInterference(appId);
    }
    this.setState({
      data: this.context.store.interferences[appId],
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
    return <InterferenceChartComponent {...this.state} />
  }

}
