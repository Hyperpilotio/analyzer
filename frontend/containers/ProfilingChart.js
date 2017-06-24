import React, { Component } from "react";
import ProfilingChartComponent from "../components/ProfilingChart";


export default class ProfilingChart extends Component {

  state = { data: null, loading: true };

  async fetchData(profilingId) {
    const res = await fetch(`/api/single-app/profiling-data/${profilingId}`);
    const data = await res.json();
    this.setState({ data, loading: false });
  }

  componentDidMount() {
    this.fetchData(this.props.profilingId);
  }

  componentWillReceiveProps(props) {
    if (props.profilingId !== this.props.profilingId) {
      this.setState({loading: true});
      this.fetchData(props.profilingId);
    }
  }

  render() {
    return <ProfilingChartComponent {...this.state} />
  }

}
