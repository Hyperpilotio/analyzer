import _ from "lodash";

export default {
  beforeDraw: ({ ctx, chartArea, chart, options }) => {
    // Draw background
    ctx.fillStyle = "#f7f9fc";
    if (_.get(options, "plugins.background.fluid", false))
      ctx.fillRect(0, 0, chart.width, chart.height);
    else
      ctx.fillRect(0, 0, chart.width, chartArea.bottom);
  }
}
