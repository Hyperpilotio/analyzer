import React, { Component, Children } from "react";
import update from "immutability-helper";
import { createStore} from 'redux';
import _ from "lodash";

var initialState = {
  cluster: {},
    apps: {},
    calibrations: {},
    profilings: {},
    interferences: {},
    recommendations: {}
};
function reducer(state, action){
  switch(action.type){
    case 'GET_APPS':
      return Object.assign({}, state, getApps);

    case 'FETCH_SERVICE_PLACEMENT':
      return Object.assign({}, state, fetchServicePlacement);

    default:
      return getApps;
  }
}

let store = createStore(reducer, initialState);
export {store};

  
//  getStore() {
//    return {
//      store: this.state,
//      actions: {
//        getApps: ::this.getApps,
//        fetchServicePlacement: ::this.fetchServicePlacement,
//        fetchCalibration: ::this.fetchCalibration,
//        fetchProfiling: ::this.fetchProfiling,
//        fetchInterference: ::this.fetchInterference,
//        fetchAppInfo: ::this.fetchAppInfo
//      }
//    };
//  }

  async function getApps() {
    let res = await fetch(`/api/apps`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
//    this.setState({
//      apps: _.mapValues(data, (app, _id) => _.assign({}, this.state.apps[_id], app))
//    });
  }

  async function fetchServicePlacement(recommended = false) {
    let res = await fetch(`/api/cluster${ recommended ? "/recommended" : "" }`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
    if (recommended) {
//      this.setState({
//        recommendations: update(this.state.recommendations, { placement: { $set: data } })
//      });
    } else {
//      this.setState({ cluster: data });
    }
  }

  async function fetchAppInfo(appId) {
    let res = await fetch(`/api/apps/${appId}`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
//    this.setState({
//      apps: update(
//        this.state.apps,
//        _.fromPairs([[ appId, { $set: data } ]])
//      )
//    });
  }

  async function fetchCalibration(appId) {
    let res = await fetch(`/api/apps/${appId}/calibration`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
//    this.setState({
//      calibrations: update(
//        this.state.calibrations,
//        _.fromPairs([[appId, {$set: data}]])
//      )
//    });
  }

  async function fetchProfiling(appId, serviceName) {
    let res = await fetch(`/api/apps/${appId}/services/${serviceName}/profiling`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
    this.setState({
      profilings: update(
        this.state.profilings,
        _.fromPairs([[`${appId}-${serviceName}`, {$set: data}]])
      )
    });
  }

  async function fetchInterference(appId, serviceName) {
    let res = await fetch(`/api/apps/${appId}/services/${serviceName}/interference`);
    if (!res.ok) {
      console.error("Unexpected error for", res);
      return;
    }
    let data = await res.json();
//    this.setState({
//      interferences: update(
//        this.state.interferences,
//        _.fromPairs([[`${appId}-${serviceName}`, {$set: data}]])
//      )
//    });
  } 

