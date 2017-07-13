import { Chart } from "react-chartjs-2";
import _ from "lodash";
// Importing styles to ensure the font is loaded
import "../styles/index.sass";


Chart.defaults.global.animation.duration = 1000;
Chart.defaults.global.defaultFontFamily = "WorkSans";
Chart.defaults.global.tooltips.mode = "x-axis";
Chart.defaults.global.hover.mode = "x-axis";
Chart.defaults.global.hover.intersect = false;
Chart.defaults.global.legend.display = false;
Chart.defaults.global.maintainAspectRatio = false;
Chart.defaults.global.elements.line.tension = 0;
Chart.defaults.scale.gridLines.drawBorder = false;
Chart.defaults.scale.gridLines.display = false;
Chart.defaults.scale.ticks.display = false;


Chart.defaults.global.tooltips.custom = function(tooltip) {
  // Store currently hovered data points
  if (!_.isUndefined(tooltip.dataPoints)) {
    this.currentPoints = tooltip.dataPoints;
  }
};
