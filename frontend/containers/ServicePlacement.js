import React, { Component } from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import ServicePlacementComponent from "../components/ServicePlacement";


export default class ServicePlacement extends Component {

  static contextTypes = {
    myStore: PropTypes.object,
    actions: PropTypes.object
  }

  state = { placement: null, loading: true }

  constructor(props) {
    super(props);
    if (props.recommended) {
      this.placementObject = "context.myStore.recommendations.placement";
    } else {
      this.placementObject = "context.myStore.cluster";
    }
  }

  async fetchData() {
    if (_.isEmpty(_.get(this, this.placementObject))) {
      await this.context.actions.fetchServicePlacement(this.props.recommended);
    }
    this.setState({
      placement: _.get(this, this.placementObject),
      loading: false
    });
  }

  componentDidMount() {
    this.setState({ placement: _.get(this, this.placementObject) });
    this.fetchData();
  }

  render() {
    return <ServicePlacementComponent {...this.props} {...this.state} />
  }

}
