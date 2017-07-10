import React from "react";
import HyperPilotLogo from "../assets/images/asset_hyperpilot_nav_logo.svg";
import MainMenuIcon from "../assets/images/icon_main_menu.svg";
import UserIcon from "../assets/images/icon_user.svg";


export default ({ history }) => (
  <div className="userauth">
  <div>
    <nav className="navbar">
    </nav>
  </div>

    <div className="authBox">
      <div className="userinput">
          <input type="text"  name="username" placeholder="username"/>
          <input type="text"  name="password" placeholder="password"/>
      </div>

    </div>


  </div>
)
