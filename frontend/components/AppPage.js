import React from "react";
import { Switch, Route, Redirect } from "react-router";
import { NavLink } from "react-router-dom";
import KeyInfo from "./KeyInfo";
import redisLogo from "../assets/images/asset_redis_logo.svg";
import CalibrationChart from "../containers/CalibrationChart";
import ProfilingChart from "../containers/ProfilingChart";
import InterferenceChart from "../containers/InterferenceChart";

export default ({ match }) => (
  <div className="app-page-body">

    <KeyInfo>
      <div className="left app-identity">
        <div className="name-and-icon">
          <img src={redisLogo} width="45" />
          <h1>Redis</h1>
        </div>
        <span className="app-id muted badge">59306145e3fd9e5094db04e6</span>
      </div>
      <div className="right columns">
        <div className="column info-list">
          <div className="info-section">
            <span className="info-key">Cluster Manager</span>
            <span className="info-value">Kubernetes</span>
          </div>
          <div className="info-section">
            <span className="info-key">Interfering severity</span>
            <div className="info-value"><span className="danger badge small">High</span></div>
          </div>
        </div>
        <div className="column info-list">
          <div className="info-section">
            <span className="info-key">Service</span>
            <span className="info-value">Walmart Chatbot</span>
          </div>
          <div className="info-section">
            <span className="info-key">App type</span>
            <span className="info-value">Workload</span>
          </div>
        </div>
        <div className="column info-list">
          <div className="info-section">
            <span className="info-key">Service ID</span>
            <span className="info-value">XEDHS-123DS2S</span>
          </div>
          <div className="info-section">
            <span className="info-key">Group name</span>
            <span className="info-value">sample-webapp-target-group</span>
          </div>
        </div>
      </div>
    </KeyInfo>

    <nav className="subnav">
      <div className="container">
        <NavLink to={`/apps/${match.params.appId}/calibration`} className="nav-item" activeClassName="selected">
          Calibration
        </NavLink>
        <NavLink to={`/apps/${match.params.appId}/profiling`} className="nav-item" activeClassName="selected">
          Profiling
        </NavLink>
      </div>
    </nav>

    <div className="container">
      <Switch>
        <Route path="/apps/:appId/calibration" render={() => (
          <CalibrationChart calibrationId="595f6008e3fd9e5094deb2c0" />
        )} />
        <Route path="/apps/:appId/profiling" render={() => (
          <ProfilingChart profilingId="59606286e3fd9e5094deb389" />
        )} />
        <Redirect to="calibration" />
      </Switch>
      <div className="radar-charts columns">
        <div className="column">
          <h3 className="title">Interference Score</h3>
          <InterferenceChart />
        </div>
        <div className="column">
          <h3 className="title">Cross-app Interference</h3>
          <div className="chart-container"></div>
        </div>
      </div>

    </div>

  </div>
)
