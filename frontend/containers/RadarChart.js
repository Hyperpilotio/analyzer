import React, { Component } from "react";
import RadarChartComponent from "../components/RadarChart";


export default class RadarChart extends Component {

  state = { data: null, loading: true };

  async fetchData(profilingId) {
    // const res = await fetch(`/api/radar-data/${profilingId}`);
    // const data = await res.json();
    const data = {
      radarChartData: {
        benchmark: ["cpu", "memCap", "memBw", "l3", "l2", "iperf"],
        score: [55, 78, 79, 60, 89, 85]
      }
    };
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
    return <RadarChartComponent {...this.state} />
  }

}
