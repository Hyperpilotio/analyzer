import React, { Component, Children } from "react";
import PropTypes from "prop-types";


export default class AppProvider extends Component {

  state = { apps: [] }

  static childContextTypes = {
    store: PropTypes.object,
    actions: PropTypes.object
  }

  getChildContext() {
    return {
      store: this.state,
      actions: { getApps: ::this.getApps }
    };
  }

  async getApps() {
    let res = await fetch("/api/apps");
    let data = await res.json();
    this.setState(data);
  }

  render() {
    return Children.only(this.props.children);
  }

}
