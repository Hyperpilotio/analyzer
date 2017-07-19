import React from "react";
import PropTypes from "prop-types";
import { Switch, Route, Redirect } from "react-router";
import { NavLink, Link } from "react-router-dom";
import KeyInfo from "./KeyInfo";
import redisLogo from "../assets/images/asset_redis_logo.svg";
import CalibrationChart from "../containers/CalibrationChart";
import ProfilingChart from "../containers/ProfilingChart";
import InterferenceChart from "../containers/InterferenceChart";
import MetricScoreChart from "./MetricScoreChart";
import _ from "lodash";

// For cross-app interference chart, use random dataset for now
import CrossAppInterfChart from "./CrossAppInterfChart";

export default ({ appId, data, loading }) => (
  <div className="app-page-body">

    <KeyInfo>
      <div className="left app-identity">
        <div className="name-and-icon">
          <img src={redisLogo} width="45" />
          <h1>{ _.get(data, "name", "Loading...") }</h1>
        </div>
        <span className="app-id muted badge">{ appId }</span>
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
            <span className="info-value">{ loading ? "Loading..." : data.type }</span>
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
        <NavLink to={`/apps/${appId}/calibration`} className="nav-item" activeClassName="selected">
          Calibration
        </NavLink>
        <NavLink to={`/apps/${appId}/profiling`} className="nav-item" activeClassName="selected">
          Profiling
        </NavLink>
      </div>
    </nav>

    <div className="container">
      <Switch>
        <Route path="/apps/:appId/calibration" render={({ match }) => (
          <CalibrationChart appId={match.params.appId} />
        )} />
        <Route path="/apps/:appId/profiling" render={({ match }) => (
          <ProfilingChart appId={match.params.appId} />
        )} />
        <Redirect to="calibration" />
      </Switch>
      <div className="radar-charts columns">
        <div className="column">
          <h3 className="title">Interference Score</h3>
          <InterferenceChart appId={appId} />
        </div>
        <div className="qos-metrics column">
          <h3 className="title">QoS Metrics</h3>
          <div className="score-chart-box">
            <header>
              <span className="left">Latency</span>
              <div className="right columns">
                <div className="column status-indicator">
                  <div className="key-stat">245</div>
                  <div className="key-stat-label">Current</div>
                </div>
                <div className="column status-indicator">
                  <div className="key-stat danger">500</div>
                  <div className="key-stat-label">Target</div>
                </div>
              </div>
            </header>
            <main>
              <MetricScoreChart name="Latency" thresholdColor="#ff8686" />
            </main>
          </div>
          <div className="run-optimizer-mask">
            <p>Apply recommendation to see enhanced QoS metric</p>
            <Link to="/autopilot/after" className="primary-button">Apply Recommendation</Link>
          </div>
        </div>
      </div>

    </div>

  </div>
)
