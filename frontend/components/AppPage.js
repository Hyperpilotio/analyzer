import React from "react";
import KeyInfo from "./KeyInfo";
import redisLogo from "../assets/images/asset_redis_logo.svg";

export default ({ children, match }) => (
  <div>

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
            <div className="info-value"><span className="danger badge">High</span></div>
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
    { children }
  </div>
)
