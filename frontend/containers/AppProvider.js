import React, { Component, Children } from "react";
import PropTypes from "prop-types";
import update from "immutability-helper";
import _ from "lodash";


export default class AppProvider extends Component {

  state = { apps: [], calibrations: {}, profilings: {}, interferences: {} }

  static childContextTypes = {
    store: PropTypes.object,
    actions: PropTypes.object
  }

  getChildContext() {
    return {
      store: this.state,
      actions: {
        getApps: ::this.getApps,
        fetchCalibration: ::this.fetchCalibration,
        fetchProfiling: ::this.fetchProfiling,
        fetchInterference: ::this.fetchInterference,
        fetchAppInfo: ::this.fetchAppInfo
      }
    };
  }

  async getApps() {
    let res = await fetch(`/api/apps`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
    this.setState({
      apps: _.mapValues(data, (app, _id) => _.assign({}, this.state.apps[_id], app))
    });
  }

  async fetchAppInfo(appId) {
    let res = await fetch(`/api/apps/${appId}`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
    this.setState({
      apps: update(
        this.state.apps,
        _.fromPairs([[ appId, { $set: data } ]])
      )
    });
  }

  async fetchCalibration(appId) {
    let res = await fetch(`/api/apps/${appId}/calibration`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
    this.setState({
      calibrations: update(
        this.state.calibrations,
        _.fromPairs([[appId, {$set: data}]])
      )
    });
  }

  async fetchProfiling(appId) {
    let res = await fetch(`/api/apps/${appId}/profiling`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
    this.setState({
      profilings: update(
        this.state.profilings,
        _.fromPairs([[appId, {$set: data}]])
      )
    });
  }

  async fetchInterference(appId) {
    let res = await fetch(`/api/apps/${appId}/interference`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
    this.setState({
      interferences: update(
        this.state.interferences,
        _.fromPairs([[appId, {$set: data}]])
      )
    });
  }

  render() {
    return Children.only(this.props.children);
  }

}
