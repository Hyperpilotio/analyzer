import React from "react";
import _ from "lodash";
import redisLogo from "../assets/images/asset_redis_logo.svg";

const Node = ({ id, instanceType, services }) => (
  <section>
    <h4>Node { id }</h4>
    <div className="services-on-node">
      { services.map( service => (
        <div key={service} className="running-service">
          <img src={redisLogo} />
          <span>{ service.task }</span>
        </div>
      ) ) }
    </div>
  </section>
)

export default ({ className, title, footer, placement, loading }) => (
  <article className={className}>
    <h3>{ title }</h3>
    <div className="service-placement">
      <header>
        { loading ? "Loading..." : placement.clusterDefinition.nodes.map(node => (
          <Node {...node} services={ _.filter(placement.nodeMapping, ["id", node.id]) } />
        )) }
      </header>
      { footer }
    </div>
  </article>
)
