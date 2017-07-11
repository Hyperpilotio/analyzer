import React from "react";
import MetricScoreChart from "./MetricScoreChart";
import redisLogo from "../assets/images/asset_redis_logo.svg";
import mongoLogo from "../assets/images/asset_mongoDB_logo.svg";
import kafkaLogo from "../assets/images/asset_kafka_logo.svg";


export default () => (
  <div className="container autopilot">
    <div className="columns">

      <article className="column">
        <h3>Current app placement</h3>
        <div className="app-placement">
          <header>
            <section>
              <h4>Node 1</h4>
              <div className="containers-on-node">
                <div className="running-container danger">
                  <img src={redisLogo} />
                  <span>Redis</span>
                </div>
                <div className="running-container danger">
                  <img src={mongoLogo} />
                  <span>MongoDB</span>
                </div>
              </div>
            </section>
            <section>
              <h4>Node 2</h4>
              <div className="containers-on-node">
                <div className="running-container">
                  <img src={kafkaLogo} />
                  <span>Kafka</span>
                </div>
              </div>
            </section>
          </header>
          <footer>
            <section>
              <span className="info-key">Interfering: </span>
              <span className="info-value stat">2</span>
            </section>
            <section>
              <span className="info-key">Intensity: </span>
              <span className="info-value danger badge">High</span>
            </section>
          </footer>
        </div>
      </article>

      <article className="column">
        <h3>Recommended app placement</h3>
        <div className="app-placement">
          <header>
            <section>
              <h4>Node 1</h4>
              <div className="containers-on-node">
                <div className="running-container">
                  <img src={redisLogo} />
                  <span>Redis</span>
                </div>
              </div>
            </section>
            <section>
              <h4>Node 2</h4>
              <div className="containers-on-node">
                <div className="running-container">
                  <img src={mongoLogo} />
                  <span>MongoDB</span>
                </div>
                <div className="running-container">
                  <img src={kafkaLogo} />
                  <span>Kafka</span>
                </div>
              </div>
            </section>
          </header>
          <footer className="only-button">
            <a className="primary-button" href="#">Apply Recommendation</a>
          </footer>
        </div>
      </article>
    </div>

    <div className="columns autopilot">
      <article className="column">
        <h3>Current QoS Score</h3>

        <section>
          <span className="app-title">
            <img src={redisLogo} />
            <h4>Redis</h4>
          </span>
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
        </section>

        <section>
          <span className="app-title">
            <img src={mongoLogo} />
            <h4>MongoDB</h4>
          </span>
          <div className="score-chart-box">
            <header>
              <span className="left">Throughput</span>
              <div className="right columns">
                <div className="column status-indicator">
                  <div className="key-stat">338</div>
                  <div className="key-stat-label">Current</div>
                </div>
                <div className="column status-indicator">
                  <div className="key-stat success">500</div>
                  <div className="key-stat-label">Target</div>
                </div>
              </div>
            </header>
            <main>
              <MetricScoreChart name="Throughput" thresholdColor="#7ed321" />
            </main>
          </div>
        </section>

        <section>
          <span className="app-title">
            <img src={kafkaLogo} />
            <h4>Kafka</h4>
          </span>
          <div className="score-chart-box">
            <header>
              <span className="left">Throughput</span>
              <div className="right columns">
                <div className="column status-indicator">
                  <div className="key-stat">254</div>
                  <div className="key-stat-label">Current</div>
                </div>
                <div className="column status-indicator">
                  <div className="key-stat success">500</div>
                  <div className="key-stat-label">Target</div>
                </div>
              </div>
            </header>
            <main>
              <MetricScoreChart name="Throughput" thresholdColor="#7ed321" />
            </main>
          </div>
        </section>

      </article>

      <article className="column">
        <h3>Optimized QoS Score</h3>
        <div className="run-optimizer-mask">
          <p>Apply recommendation to see enhanced QoS metric</p>
          <a className="primary-button" href="#">Apply Recommendation</a>
        </div>
      </article>
    </div>
  </div>
)
