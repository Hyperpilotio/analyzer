import React from "react";
import KeyInfo from "./KeyInfo";


export default () => (
  <div className="dashboard">
    <KeyInfo />
    <div className="container">
      <div className="display-controls">
        <span className="list-view">
          <img src="http://placehold.it/30x30" />
        </span>
        <span className="grid-view">
          <img src="http://placehold.it/30x30" />
        </span>
      </div>
    </div>
  </div>
)
