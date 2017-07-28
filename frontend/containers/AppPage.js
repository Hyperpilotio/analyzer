import React, { Component } from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import AppPageComponent from "../components/AppPage";


export default class AppPage extends Component {


  constructor(props) {
    super(props);
    this.appId = props.match.params.appId;
  }

  state = { data: null, loading: true }

  async fetchData(appId) {
    if (!_.has(this.props.apps[appId], "type")) {
      await this.props.actions.fetchAppInfo(appId)
    }
    this.setState({
      data: this.props.apps[appId],
      loading: false
    });
  }

  componentDidMount() {
    this.setState({ data: this.props.apps[this.appId] });
    this.fetchData(this.appId);
  }

  componentWillReceiveProps(props) {
    this.appId = props.match.params.appId;
    if (props.match.params.appId !== this.props.match.params.appId) {
      this.setState({loading: true});
      this.fetchData(props.match.params.appId);
    }
  }

  render() {
    return <AppPageComponent appId={this.appId} {...this.state} />;
  }

}
module.exports = AppPage;