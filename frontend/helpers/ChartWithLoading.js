import Spinner from "react-spinkit";
import React from "react";

// ChartWithLoading is a component composer
export default ChartComponent => (
  ({ data, loading }) => {
    return <div className="chart-container">
      { data && <ChartComponent data={data} /> }
      { loading && <Spinner fadeIn="quarter" name="ball-grid-pulse" /> }
    </div>
  }
)
