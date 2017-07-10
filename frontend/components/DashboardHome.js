import React from "react";
import { Link } from "react-router-dom";
import KeyInfo from "./KeyInfo";
import redisLogo from "../assets/images/asset_redis_logo.svg";
import mongoLogo from "../assets/images/asset_mongoDB_logo.svg";
import kafkaLogo from "../assets/images/asset_kafka_logo.svg";
import gridIcon from "../assets/images/icon_grid_view.svg";
import listIcon from "../assets/images/icon_list_view.svg";


export default () => (
  <div className="dashboard">

    <KeyInfo>
      <div className="left columns with-divider">
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
        <div className="column info-list with-divider">
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
                    <div className="key-stat-label">Interfering</div>
                  </div>
                  <span className="badge danger">High</span>
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
      <div className="right columns">
        <a className="primary-button" href="#">See Recommendation</a>
      </div>
    </KeyInfo>

    <div className="container">
      <div className="display-controls">
        <span className="list-view">
          <img height="30" src={listIcon} />
        </span>
        <span className="grid-view">
          <img height="30" src={gridIcon} />
        </span>
      </div>

      <div className="apps-display">
        <h3>Apps</h3>
        <div className="apps-container">

          <article>
            <aside><img src={redisLogo} /></aside>
            <section>
              <header>
                <h1>Redis</h1>
                <p>ID: 59306145e3fd9e5094db04e6</p>
                <p>More summary info</p>
              </header>
              <footer><Link to="/apps/59306145e3fd9e5094db04e6/">Analysis Workflow</Link></footer>
            </section>
            <mark className="right"><div className="danger badge" /></mark>
          </article>

          <article>
            <aside><img src={mongoLogo} /></aside>
            <section>
              <header>
                <h1>MongoDB</h1>
                <p>ID: 594077cd7be0c5ef6c6afcb8</p>
                <p>More summary info</p>
              </header>
              <footer><a href="#">Analysis Workflow</a></footer>
            </section>
            <mark className="right"><div className="danger badge" /></mark>
          </article>

          <article>
            <aside><img src={kafkaLogo} /></aside>
            <section>
              <header>
                <h1>Apache Kafka</h1>
                <p>ID: 59406aa9e3fd9e5094db7f3b</p>
                <p>More summary info</p>
              </header>
              <footer><a href="#">Analysis Workflow</a></footer>
            </section>
            <mark className="right"><div className="danger badge" /></mark>
          </article>

        </div>
      </div>
    </div>
  </div>
)
