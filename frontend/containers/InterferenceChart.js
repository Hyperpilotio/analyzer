import React, { Component } from "react";
import InterferenceChartComponent from "../components/InterferenceChart";


export default class InterferenceChart extends Component {

  state = { data: null, loading: true };

  async fetchData(profilingId) {
    const res = await fetch(`/api/radar-data/${profilingId}`);
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
    return <InterferenceChartComponent {...this.state} />
  }

}
