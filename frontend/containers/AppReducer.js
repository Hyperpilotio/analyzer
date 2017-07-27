import React, { Component, Children } from "react";
import update from "immutability-helper";
import { createStore} from 'redux';
import _ from "lodash";
import AppProvider from './AppProvider';

var initialState = {
    cluster: {},
    apps: {},
    calibrations: {},
    profilings: {},
    interferences: {},
    recommendations: {}, 
    action: {},
    actions: {
        getApps: {},
        fetchServicePlacement: {},
        fetchCalibration: {},
        fetchProfiling: {},
        fetchInterference: {},
        fetchAppInfo: {}
    }
};
function reducer(state, action){
  switch(action.type){
    case 'GET_APPS':
      return Object.assign({}, state, {});

    case 'FETCH_SERVICE_PLACEMENT':
      return Object.assign({}, state, {});

    case 'FETCH_CALIBRATION':
      return Object.assign({}, state, {});
          
    case 'SET_ACTIONS':
      return Object.assign({}, state, {actions: action.actions});

    default:
      return Object.assign({}, state, {});
  }
}


function mapStateToProps(state) {
    return {
        cluster: state.cluster,
        apps: state.apps,
        calibrations: state.calibrations,
        profilings: state.profilings,
        interferences: state.interferences,
        recommendations: state.recommendations,
        action: state.recommendations,
        actions: state.actions

    };
}


let appStore = createStore(reducer, initialState);
export {appStore};


//
//  async getApps() {
//    let res = await fetch(`/api/apps`);
//    if (!res.ok) {
//      console.error("Unexpected error for", res);
//      return;
//    }
//    let data = await res.json();
//    initialState.apps = _.mapValues(data, (app, _id) => _.assign({}, this.state.apps[_id], app));
////    this.setState({
////      apps: _.mapValues(data, (app, _id) => _.assign({}, this.state.apps[_id], app))
////    });
//  }
//
//  async function fetchServicePlacement(recommended = false) {
//    let res = await fetch(`/api/cluster${ recommended ? "/recommended" : "" }`);
//    if (!res.ok) {
//      console.error("Unexpected error for", res);
//      return;
//    }
//    let data = await res.json();
//    if (recommended) {
////      this.setState({
////        recommendations: update(this.state.recommendations, { placement: { $set: data } })
////      });
//    } else {
////      this.setState({ cluster: data });
//    }
//  }
//
//  async function fetchAppInfo(appId) {
//    let res = await fetch(`/api/apps/${appId}`);
//    if (!res.ok) {
//      console.error("Unexpected error for", res);
//      return;
//    }
//    let data = await res.json();
////    this.setState({
////      apps: update(
////        this.state.apps,
////        _.fromPairs([[ appId, { $set: data } ]])
////      )
////    });
//  }
//
//  async function fetchCalibration(appId) {
//    let res = await fetch(`/api/apps/${appId}/calibration`);
//    if (!res.ok) {
//      console.error("Unexpected error for", res);
//      return;
//    }
//    let data = await res.json();
////    this.setState({
////      calibrations: update(
////        this.state.calibrations,
////        _.fromPairs([[appId, {$set: data}]])
////      )
////    });
//  }
//
//  async function fetchProfiling(appId, serviceName) {
//    let res = await fetch(`/api/apps/${appId}/services/${serviceName}/profiling`);
//    if (!res.ok) {
//      console.error("Unexpected error for", res);
//      return;
//    }
//    let data = await res.json();
//    this.setState({
//      profilings: update(
//        this.state.profilings,
//        _.fromPairs([[`${appId}-${serviceName}`, {$set: data}]])
//      )
//    });
//  }
//
//  async function fetchInterference(appId, serviceName) {
//    let res = await fetch(`/api/apps/${appId}/services/${serviceName}/interference`);
//    if (!res.ok) {
//      console.error("Unexpected error for", res);
//      return;
//    }
//    let data = await res.json();
////    this.setState({
////      interferences: update(
////        this.state.interferences,
////        _.fromPairs([[`${appId}-${serviceName}`, {$set: data}]])
////      )
////    });
//  } 
//
