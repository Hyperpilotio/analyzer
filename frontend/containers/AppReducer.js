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
    case 'SET_STATE':
      return Object.assign({}, state, action.state);
    
    case 'SET_ACTIONS':
      return Object.assign({}, state, {actions: action.actions});

    case 'SET_APPS':
      return Object.assign({}, state, {apps: action.apps});

    case 'SET_CALIBRATIONS':
      return Object.assign({}, state, {calibrations: action.calibrations});
            
    case 'SET_RECOMMENDATIONS':
      return Object.assign({}, state, {recommendations: action.recommendations});
    
    case 'SET_CLUSTER':
      return Object.assign({}, state, {cluster: action.cluster});    
          
    case 'SET_PROFILINGS':
      return Object.assign({}, state, {profilings: action.profilings}); 
    
    case 'SET_INTERFERENCES':
      return Object.assign({}, state, {interferences: action.interferences}); 

    default:
      return Object.assign({}, state);
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
        action: state.action,
        actions: state.actions

    };
}

function mapDispatchToProps(dispatch){
  return {
    setAllActions: function(actions){
        dispatch({type: 'SET_ACTIONS', actions: actions});
    },
    setState: function(state){
        dispatch({type: 'SET_STATE', state: state});
    },
    setApps: function(apps){
        dispatch({type: 'SET_APPS', apps: apps});
    },
    setRecommendations: function(recommendations){
        dispatch({type: 'SET_RECOMMENDATIONS', recommendations: recommendations});
    }, 
    setCluster: function(cluster){
        dispatch({type: 'SET_CLUSTER', cluster: cluster});
    }, 
    setCalibrations: function(calibrations){
        dispatch({type: 'SET_CALIBRATIONS', calibrations: calibrations});
    },
    setProfilings: function(profilings){
        dispatch({type: 'SET_PROFILINGS', profilings: profilings});
    },
    setInterferences: function(interferences){
        dispatch({type: 'SET_INTERFERENCES', interferences: interferences});
    }
  };
}


let appStore = createStore(reducer, initialState);
export {appStore, mapStateToProps, mapDispatchToProps};


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
