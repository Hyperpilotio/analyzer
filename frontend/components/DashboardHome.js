import React from "react";
import KeyInfo from "./KeyInfo";
import redisLogo from "../assets/images/redis.png";
import mongoLogo from "../assets/images/mongo.png";


export default () => (
  <div className="dashboard">
    <KeyInfo />
    <div className="container">
      <div className="display-controls">
        <span className="list-view">
          <img height="30" src="http://placehold.it/30x30" />
        </span>
        <span className="grid-view">
          <img height="30" src="http://placehold.it/30x30" />
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
              <footer><a href="#">Analysis Workflow</a></footer>
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

        </div>
      </div>
    </div>
  </div>
)
