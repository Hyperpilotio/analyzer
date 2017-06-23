import "babel-polyfill";
import "whatwg-fetch";
import React, { Component } from "react";
import { BrowserRouter as Router, Route } from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import ReactDOM from "react-dom";
import Navbar from "./containers/Navbar";
import CalibrationChart from "./containers/CalibrationChart";
import _ from "lodash";

import injectTapEventPlugin from "react-tap-event-plugin";
injectTapEventPlugin();


class App extends Component {

  static Calibration = ({ match }) => (
    <CalibrationChart calibrationId={match.params.calibrationId} />
  )

  render() {
    return <Router>
      <MuiThemeProvider>
        <div>
          <Navbar />
          <Route path="/calibration/:calibrationId" component={App.Calibration} />
        </div>
      </MuiThemeProvider>
    </Router>;
  }
}


ReactDOM.render(<App />, document.getElementById("react-root"));
