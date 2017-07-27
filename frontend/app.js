import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Switch, Route, Redirect } from "react-router-dom";
import ReactDOM from "react-dom";
import HeaderNav from "./components/HeaderNav";
import AutopilotPage from "./components/AutopilotPage";
//import AppPage from "./containers/AppPage";
import UserAuth from "./components/UserAuth";
//import AppProvider from "./containers/AppProvider";
import PropTypes from "prop-types";
import { render } from 'react-dom';
import { Provider, connect } from 'react-redux';
import { appStore, mapStateToProps, mapDispatchToProps } from './containers/AppReducer'

//import will be set as const variable
let AppProvider = require("./containers/AppProvider");
let DashboardHome = require("./components/DashboardHome");
let AppPage = require("./containers/AppPage");


DashboardHome = connect(mapStateToProps, mapDispatchToProps)(DashboardHome);
AppPage = connect(mapStateToProps, mapDispatchToProps)(AppPage);
class App extends Component {
  constructor(props) {
     super(props);
  }
    
  static contextTypes = {
    actions: PropTypes.object,
    myStore: PropTypes.object
  }

  componentDidMount() {
    if (_.keys(this.context.myStore.apps).length === 0){
      this.props.actions.getApps();
    }
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

