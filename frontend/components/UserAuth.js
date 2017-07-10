import React from "react";
import HyperPilotLogo from "../assets/images/asset_hyperpilot_nav_logo.svg";
import MainMenuIcon from "../assets/images/icon_main_menu.svg";
import UserIcon from "../assets/images/icon_user.svg";
import HyperPilotLogoLogin from "../assets/images/asset_hyperpilot_login_logo.svg";
import { NavLink } from "react-router-dom";


export default ({ history }) => (
  <div className="userauth">
  <div>
    <nav className="navbar">
    </nav>
  </div>

    <div className="auth-area">

    <div className= "login-info">

        <img className="brand-login" src={HyperPilotLogoLogin} />
        <div className ="demo-version">
        Demo v0.1
        </div>

    </div>

    <div className="auth-box">

      <div className="userinput">
          <input type="text"  name="username" placeholder="username"/>
          <input type="text"  name="password" placeholder="password"/>
      </div>

      <NavLink to="/dashboard" className="login-button">
        Log In
      </NavLink>


    </div>

  </div>
  </div>
)
