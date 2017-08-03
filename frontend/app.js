import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Switch, Route, Redirect, hasHistory, Link } from "react-router-dom";
import ReactDOM from "react-dom";
import HeaderNav from "./components/HeaderNav";
import AutopilotPage from "./components/AutopilotPage";
import UserAuth from "./components/UserAuth";
import PropTypes from "prop-types";
import { render } from 'react-dom';
import { Provider, connect } from 'react-redux';
import { appStore, mapStateToProps, mapDispatchToProps } from './containers/AppReducer';
import CSSTransitionGroup from 'react-transition-group/CSSTransitionGroup'

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
  click(page){
  }

  render() {
    console.log(this.tranNm);
    return (
      <Router key="router" history={hasHistory}>
        <Switch>
          <Route key="route_user_auth" path="/login" component={UserAuth} />
          <Route key="route_root" path="/" children={({ location }) => (
            <div>
              <HeaderNav key="header_nav" onClick={this.click}/>
              <CSSTransitionGroup key="route_css_transition" 
                 transitionName="upper"
                 transitionEnterTimeout={500}
                 transitionLeaveTimeout={500}>
                <Switch key={location.key} location={location} >
                  <Route location={location} key={location.key + "_1"} path="/dashboard" component={DashboardHome}  />
                  <Route location={location} key={location.key + "_2"} path="/autopilot" component={AutopilotPage} />
                  <Route location={location} key={location.key + "_0"} path="/apps/:appId" component={AppPage} />
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

