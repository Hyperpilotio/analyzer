import React from "react";

export default () => (
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
            <div className="info-value status-indicator-list">
              <div className="columns">
                <div className="column status-indicator">
                  <div>
                    <div className="key-stat">35</div>
                    <div className="key-stat-label">apps</div>
                  </div>
                  <span className="badge success">Healthy</span>
                </div>
                <div className="column status-indicator">
                  <div>
                    <div className="key-stat">12</div>
                    <div className="key-stat-label">apps</div>
                  </div>
                  <span className="badge danger">Interfering</span>
                </div>
                <div className="column status-indicator">
                  <div>
                    <div className="key-stat">36.5%</div>
                    <div className="key-stat-label">average QoS rate</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="right run-optimizer">
        <button>Run Optimizer</button>
      </div>
    </div>
  </div>
);
