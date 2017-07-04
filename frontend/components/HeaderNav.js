import React from "react";

export default () => (
  <div>
    <nav className="navbar">
      <div className="container">

        {/* HyperPilot icon */}
        <div className="nav-left">
          <div className="navbar-item">
            <img className="brand" src="http://placehold.it/40/40" />
          </div>
        </div>

        {/* Search bar */}
        <div className="nav-center">
          <div className="navbar-item">
            <input type="search" placeholder="Jump to apps, status, services..." />
          </div>
        </div>

        {/* Menu and account icon */}
        <div className="nav-right nav-sublist">
          <div className="navbar-item">
            <img className="menu-icon" src="http://placehold.it/40/40" />
          </div>
          <div className="navbar-item">
            <img className="user-icon" src="http://placehold.it/40/40" />
          </div>
        </div>

      </div>
    </nav>

    <div className="divider" />

    {/* Header */}
    <div className="header">
      <div className="container">
        <div className="current-location">Organization name</div>
        <button className="settings-button">
          <span className="placehold-settings-icon" /> Settings
        </button>
      </div>
    </div>
  </div>
)