import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Switch, Route, Redirect } from "react-router-dom";
// import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import ReactDOM from "react-dom";
// import Navbar from "./containers/Navbar";
import HeaderNav from "./components/HeaderNav";
import DashboardHome from "./components/DashboardHome";
import LoginPage from "./components/LoginPage";
import AppPage from "./components/AppPage";
// import CalibrationChart from "./containers/CalibrationChart";
// import ProfilingChart from "./containers/ProfilingChart";
// import RadarChart from "./containers/RadarChart";
// import _ from "lodash";

// import injectTapEventPlugin from "react-tap-event-plugin";
// injectTapEventPlugin();


class App extends Component {

  // static Calibration = ({ match }) => (
  //   <CalibrationChart {...match.params} />
  // )

  // static Profiling = ({ match }) => (
  //   <div>
  //     <ProfilingChart {...match.params} />
  //     <RadarChart {...match.params} />
  //   </div>
  // )

  render() {
    return (
      <Router>
        <Switch>
          <Route path="/login" component={LoginPage} />
          <Route path="/" children={({ history }) => (
            <div>
              <HeaderNav history={history} />
              <Switch>
                <Route path="/dashboard" component={DashboardHome} />
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

ReactDOM.render(<App />, document.getElementById("react-root"));
