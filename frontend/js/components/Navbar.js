import React, { Component } from "react";
import { Link } from "react-router-dom";
import Drawer from "material-ui/Drawer";
import MenuItem from "material-ui/MenuItem";
import _ from "lodash";


export default ({ availableApps }) => (
  <Drawer open>
    {availableApps.calibration.map(item => (
      <Link to={`/calibration/${item._id}`}
            style={{color: "black", textDecoration: "none"}}>
        <MenuItem key={item._id}>
          {item.appName} ({_.truncate(item._id, { length: 12 })})
        </MenuItem>
      </Link>
    ))}
  </Drawer>
)
