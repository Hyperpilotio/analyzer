import React from "react";
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
            <a className="primary-button" href="#">Run Optimizer</a>
          </footer>
        </div>
      </article>
    </div>
  </div>
)
