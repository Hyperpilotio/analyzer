import React, { Component } from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import AppPageComponent from "../components/AppPage";


export default class AppPage extends Component {

  static contextTypes = {
    store: PropTypes.object,
    actions: PropTypes.object
  }

  state = { data: null, loading: true }

  async fetchData(appId) {
    if (_.keys(this.context.store.apps[appId]).length <= 1) {
      await this.context.actions.fetchAppInfo(appId)
    }
    this.setState({
      data: this.context.store.apps[appId],
      loading: false
    });
  }

  componentDidMount() {
    this.fetchData(this.props.match.params.appId);
  }

  componentWillReceiveProps(props) {
    if (props.match.params.appId !== this.props.match.params.appId) {
      this.setState({loading: true});
      this.fetchData(props.match.params.appId);
    }
  }

  render() {
    return <AppPageComponent appId={this.props.match.params.appId} {...this.state} />;
  }

}
