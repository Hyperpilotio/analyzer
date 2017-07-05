import React from "react";


export default () => (
  <div className="dashboard">
    <div className="key-info">
      <div className="container">
        <div className="left columns">
          <div className="column info-list">
            <div className="info-section">
              <span className="info-key">Cluster manager</span>
              <span className="info-value">Kubernetes</span>
            </div>
            <div className="info-section">
              <span className="info-key">Service</span>
              <span className="info-value">Walmart Chatbot</span>
            </div>
          </div>
          <div className="column info-list">
            <div className="info-section">
              <div className="info-key">Current Status</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
)
