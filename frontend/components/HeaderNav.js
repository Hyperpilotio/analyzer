import React from "react";
import HyperPilotLogo from "../assets/images/asset_hyperpilot_nav_logo.svg";
import MainMenuIcon from "../assets/images/icon_main_menu.svg";
import UserIcon from "../assets/images/icon_user.svg";
import { NavLink } from "react-router-dom";



export default ({ history }) => (
  <div>
    <nav className="navbar">
      <div className="container">

        {/* HyperPilot icon */}
        <div className="left">
          <div className="navbar-item">
            <img className="brand" src={HyperPilotLogo} />
          </div>
        </div>

        {/* Search bar */}
        <div className="center">
          <div className="navbar-item">
            <input type="search" placeholder="Jump to apps, status, services..." />
          </div>
        </div>

        {/* Menu and account icon */}
        <div className="right nav-sublist">
          <div className="navbar-item">
            <img className="menu-icon" src={MainMenuIcon} />
          </div>
          <div className="navbar-item">
            <img className="user-icon" src={UserIcon} />
          </div>
        </div>

      </div>
    </nav>

    {/* Header */}
    <div className="header">
      <div className="container">
        <div className="current-location">Organization name</div>
        <a href="#" className="badge info settings-button">
          <span className="placehold-settings-icon" /> Settings
        </a>
      </div>
    </div>

    {/* Subnav */}
    <nav className="subnav">
      <div className="container">
        <NavLink to="/dashboard" className="nav-item" activeClassName="selected">
          Dashboard
        </NavLink>
        <NavLink to="/autopilot" className="nav-item" activeClassName="selected">
          Autopilot
        </NavLink>
        <NavLink to="/apps" className="nav-item" activeClassName="selected">
          Apps
        </NavLink>
        <NavLink to="/services" className="nav-item" activeClassName="selected">
          Services
        </NavLink>
      </div>
    </nav>
  </div>
)
