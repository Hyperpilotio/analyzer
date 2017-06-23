import React, { Component } from "react";
import NavbarComponent from "../components/Navbar";


export default class Navbar extends Component {

  state = {
    apps: { calibration: [], profiling: [], validation: [] },
    loading: true
  }

  async fetchData() {
    const res = await fetch("/api/available-apps");
    const apps = await res.json();
    this.setState({ apps, loading: false });
  }

  componentDidMount() {
    this.fetchData();
  }

  render() {
    const { history } = this.props;
    return <NavbarComponent
      selectedItem={history.location.pathname}
      selectItem={(e, path) => history.push(path)}
      loading={this.state.loading}
      availableApps={this.state.apps} />
  }
}
