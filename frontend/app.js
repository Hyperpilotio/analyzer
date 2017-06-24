import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Route } from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import ReactDOM from "react-dom";
import Navbar from "./containers/Navbar";
import CalibrationChart from "./containers/CalibrationChart";
import ProfilingChart from "./containers/ProfilingChart";
import _ from "lodash";

import injectTapEventPlugin from "react-tap-event-plugin";
injectTapEventPlugin();


class App extends Component {

  static Calibration = ({ match }) => (
    <CalibrationChart {...match.params} />
  )

  static Profiling = ({ match }) => (
    <ProfilingChart {...match.params} />
  )

  render() {
    return <Router>
      <MuiThemeProvider>
        <Route path="/" children={({ match, history }) => (
          <div>
            <Navbar history={history} />
            <Route path="/calibration/:calibrationId" component={App.Calibration} />
            <Route path="/profiling/:profilingId" component={App.Profiling} />
          </div>
        )} />
      </MuiThemeProvider>
    </Router>;
  }
}


ReactDOM.render(<App />, document.getElementById("react-root"));
