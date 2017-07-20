import React from "react";
import { Link, Route, Switch } from "react-router-dom";
import MetricScoreChart from "./MetricScoreChart";
import ServicePlacement from "../containers/ServicePlacement";
import redisLogo from "../assets/images/asset_redis_logo.svg";
import mongoLogo from "../assets/images/asset_mongoDB_logo.svg";
import kafkaLogo from "../assets/images/asset_kafka_logo.svg";


export default ({ placement }) => (
  <div className="container autopilot">
    <div className="columns">

      <ServicePlacement
        className="column"
        title="Current service placement"
        footer={
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
        } />

      <ServicePlacement
        className="column"
        title="Recommended service placement"
        footer={
          <footer>
            <Switch>
              <Route path="/autopilot/after">
                <p>Placement recommendation applied!</p>
              </Route>
              <Route path="/autopilot">
                <Link to="/autopilot/after" className="primary-button">
                  Apply Recommendation
                </Link>
              </Route>
            </Switch>
          </footer>
        } />
    </div>

    <div className="columns autopilot">
      <article className="column">
        <h3>Current QoS Score</h3>

        <section>
          <span className="service-name">
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
          <span className="service-name">
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
          <span className="service-name">
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

        <Switch>
          <Route path="/autopilot/after">
            <article className="column">
              <h3>QoS Score After Autopilot</h3>
              <section>
                <span className="service-name">
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
                <span className="service-name">
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
                <span className="service-name">
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

          </Route>

          <Route path="/autopilot/">
            <article className="column">
              <h3>QoS Score After Autopilot</h3>
              <div className="run-optimizer-mask">
                <p>Apply recommendation to see enhanced QoS metric</p>
                <Link to="/autopilot/after" className="primary-button">Apply Recommendation</Link>
              </div>
            </article>
          </Route>
        </Switch>
    </div>
  </div>
)
