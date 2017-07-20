import React, { Component } from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import ServicePlacementComponent from "../components/ServicePlacement";


export default class ServicePlacement extends Component {

  static contextTypes = {
    store: PropTypes.object,
    actions: PropTypes.object
  }

  state = { placement: null, loading: true }

  async fetchData() {
    console.log(this.context.store.cluster);
    if (_.isEmpty(this.context.store.cluster)) {
      await this.context.actions.fetchClusterServices();
    }
    this.setState({
      placement: this.context.store.cluster,
      loading: false
    })
  }

  componentDidMount() {
    this.setState({ placement: this.context.store.cluster });
    this.fetchData();
  }

  render() {
    return <ServicePlacementComponent {...this.props} {...this.state} />
  }

}
