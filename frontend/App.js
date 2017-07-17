import React, { Component } from "react";
import { BrowserRouter as Router, Switch, Route, Redirect } from "react-router-dom";
import HeaderNav from "./components/HeaderNav";
import DashboardHome from "./components/DashboardHome";
import AutopilotPage from "./components/AutopilotPage";
import AppPage from "./containers/AppPage";
import UserAuth from "./components/UserAuth";
import AppProvider from "./containers/AppProvider";
import PropTypes from "prop-types";


class App extends Component {

  static contextTypes = {
    actions: PropTypes.object,
    store: PropTypes.object
  }

  componentDidMount() {
    if (_.keys(this.context.store.apps).length === 0)
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


export default () => (
  <AppProvider>
    <App />
  </AppProvider>
)
