import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Switch, Route, Redirect } from "react-router-dom";
import ReactDOM from "react-dom";
import HeaderNav from "./components/HeaderNav";
import DashboardHome from "./components/DashboardHome";
import AutopilotPage from "./components/AutopilotPage";
import AppPage from "./containers/AppPage";
import UserAuth from "./components/UserAuth";
//import AppProvider from "./containers/AppProvider";
import PropTypes from "prop-types";
import { render } from 'react-dom';
import { Provider, connect } from 'react-redux';
import { appStore } from './containers/AppReducer'

let AppProvider = require("./containers/AppProvider");
class App extends Component {
  constructor(props) {
     super(props);
  }
    
  static contextTypes = {
    actions: PropTypes.object,
    myStore: PropTypes.object
  }

  componentDidMount() {
    if (_.keys(this.context.myStore.apps).length === 0)
      this.context.actions.getApps();
  }

  render() {
    return (
      <Router>

        <Switch>
          <Route path="/login" component={UserAuth} />
          <Route path="/" children={({ history }) => (
            <div>
              <HeaderNav history={history} />
              <Switch>
                <Route path="/dashboard" component={DashboardHome} />
                <Route path="/autopilot" component={AutopilotPage} />
                <Route path="/apps/:appId" component={AppPage} />
                <Redirect from="/" to="/dashboard" />
              </Switch>
            </div>
          )} />
        </Switch>

      </Router>
    );
  }
}

function mapStateToProps(state) {
    return {
        cluster: state.cluster,
        apps: state.apps,
        calibrations: state.calibrations,
        profilings: state.profilings,
        interferences: state.interferences,
        recommendations: state.recommendations
    };
}
function mapDispatchToProps(dispatch){
  return {
    setAllActions: function(actions){
      dispatch({type: 'SET_ACTIONS', actions: actions});
    }
  }
}

AppProvider = connect(mapStateToProps, mapDispatchToProps)(AppProvider);
//console.log(App);
ReactDOM.render(
  <Provider store={appStore}>
      <AppProvider>
          <App />
      </AppProvider>
  </Provider>,
  document.getElementById("react-root")
);


//App = connect()(App);

