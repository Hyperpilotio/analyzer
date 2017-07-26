import React, { Component } from "react";
import { Link } from "react-router-dom";
import KeyInfo from "./KeyInfo";
import redisLogo from "../assets/images/asset_redis_logo.svg";
import mongoLogo from "../assets/images/asset_mongoDB_logo.svg";
import kafkaLogo from "../assets/images/asset_kafka_logo.svg";
import gridIcon from "../assets/images/icon_grid_view.svg";
import listIcon from "../assets/images/icon_list_view.svg";
import PropTypes from "prop-types";
import { Provider, connect } from 'react-redux';
import { bindActionCreators } from 'redux';

function textClick(){
    return {
        type:'FETCH_CALIBRATION'
    }
}


class ApplicationItem extends Component{
    constructor(props) {
        super(props);
        console.log(props);
        this.handleClick = this.handleClick.bind(this);
    }

    handleClick(){
        this.props.actions.textClick();
    }
    render() {
        return (
            <article>
                <aside><img src={redisLogo} /></aside>
                <section>
                    <header>
                        <h1>{ this.props.name }</h1>
                        <p>ID: { this.props._id }</p>
                        <p>Services: { _.join(this.props.serviceNames, ", ") }</p>
                     </header>
                     <footer><Link to={`/apps/${this.props._id}/`} onClick={this.handleClick}>Analysis Workflow</Link></footer>
                </section>
                <mark className="right"><div className="danger badge" /></mark>
            </article>
        );
    }
}
function mapStateToProps(state) {
    return {
        cluster: state.cluster,
        apps: state.apps,
        calibrations: state.calibrations,
        profilings: state.profilings,
        interferences: state.interferences,
        recommendations: state.recommendations,
        action: state.action,
        actions: state.actions
    };
}
ApplicationItem = connect(mapStateToProps)(ApplicationItem);


//const ApplicationItem = ({ _id, name, serviceNames }) => (
//  <article>
//    <aside><img src={redisLogo} /></aside>
//    <section>
//      <header>
//        <h1>{ name }</h1>
//        <p>ID: { _id }</p>
//        <p>Services: { _.join(serviceNames, ", ") }</p>
//      </header>
//      <footer><Link to={`/apps/${_id}/`}>Analysis Workflow</Link></footer>
//    </section>
//    <mark className="right"><div className="danger badge" /></mark>
//  </article>
//)


export default class DashboardHome extends Component {

  static contextTypes = {
    myStore: PropTypes.object,
    actions: PropTypes.object
  };

  render() {
    const { apps } = this.context.myStore;
    return <div className="dashboard">

      <KeyInfo>
        <div className="left columns with-divider">
          <div className="column info-list">
            <div className="info-section">
              <span className="info-key">Cluster manager</span>
              <span className="info-value">Kubernetes</span>
            </div>
            <div className="info-section">
              <span className="info-key">Service</span>
              <span className="info-value">Walmart Chatbot</span>
            </div>
          </div>
          <div className="column info-list with-divider">
            <div className="info-section">
              <div className="info-key">Current Status</div>
              <div className="info-value status-indicator-list">
                <div className="columns">
                  <div className="column status-indicator">
                    <div>
                      <div className="key-stat">35</div>
                      <div className="key-stat-label">apps</div>
                    </div>
                    <span className="badge success">Healthy</span>
                  </div>
                  <div className="column status-indicator">
                    <div>
                      <div className="key-stat">12</div>
                      <div className="key-stat-label">Interfering</div>
                    </div>
                    <span className="badge danger">High</span>
                  </div>
                  <div className="column status-indicator">
                    <div>
                      <div className="key-stat">36.5%</div>
                      <div className="key-stat-label">average QoS rate</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="right columns">
          <Link to="/autopilot" className="primary-button">See Recommendation</Link>
        </div>
      </KeyInfo>

      <div className="container">
        <div className="display-controls">
          <span className="list-view">
            <img height="30" src={listIcon} />
          </span>
          <span className="grid-view">
            <img height="30" src={gridIcon} />
          </span>
        </div>

        <div className="apps-display">
          <h3>Apps</h3>
          <div className="apps-container">

            { _.map( apps, (doc, _id) => {
             return (
              <ApplicationItem key={_id} _id={_id} {...doc}  />
            )} ) }

          </div>
        </div>
      </div>
    </div>;
  }
}
