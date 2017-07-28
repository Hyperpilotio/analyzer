import React, { Component, Children } from "react";
import update from "immutability-helper";
import { createStore } from 'redux';
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
    return state;
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


let appStore = createStore(
  reducer, initialState,
  window.__REDUX_DEVTOOLS_EXTENSION__ && window.__REDUX_DEVTOOLS_EXTENSION__()
);
export {appStore, mapStateToProps, mapDispatchToProps};


