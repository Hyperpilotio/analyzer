import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Switch, Route, Redirect, hasHistory, Link } from "react-router-dom";
import ReactDOM from "react-dom";
import HeaderNav from "./components/HeaderNav";
import AutopilotPage from "./components/AutopilotPage";
//import AppPage from "./containers/AppPage";
import UserAuth from "./components/UserAuth";
//import AppProvider from "./containers/AppProvider";
import PropTypes from "prop-types";
import { render } from 'react-dom';
import { Provider, connect } from 'react-redux';
import { appStore, mapStateToProps, mapDispatchToProps } from './containers/AppReducer';
import CSSTransitionGroup from 'react-transition-group/CSSTransitionGroup'

let transitionCSS = require("./styles/transition.scss");
console.log(transitionCSS);
//can not use import because it will be set as const variable
let AppProvider = require("./containers/AppProvider");
let DashboardHome = require("./components/DashboardHome");
let AppPage = require("./containers/AppPage");


DashboardHome = connect(mapStateToProps, mapDispatchToProps)(DashboardHome);
AppPage = connect(mapStateToProps, mapDispatchToProps)(AppPage);
class App extends Component {
  constructor(props) {
     super(props);
  }
    
  componentDidMount() {
    if (_.keys(this.props.apps).length === 0){
      this.props.actions.getApps();
    }
  }

  render() {
    return (
      <Router history={hasHistory}>
        <Switch>
          <Route path="/login" component={UserAuth} />
          <Route path="/" children={({ location }) => (
            <div>
              <HeaderNav/>
              <CSSTransitionGroup
                 transitionName="fade"
                 transitionEnterTimeout={5000}
                 transitionLeaveTimeout={5000}>
              <Switch key={location.key} >
                <Route key={location.key + "_one"} path="/dashboard" component={DashboardHome} />
                <Route key={location.key + "_two"} path="/autopilot" component={AutopilotPage} />
                <Route key={location.key + "_three"} path="/apps/:appId" component={AppPage} />
                <Redirect from="/" to="/dashboard" />
              </Switch>
              </CSSTransitionGroup>
            </div>
          )} />
        </Switch>

      </Router>
    );
  }
}


AppProvider = connect(mapStateToProps, mapDispatchToProps)(AppProvider);
App = connect(mapStateToProps, mapDispatchToProps)(App);
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

