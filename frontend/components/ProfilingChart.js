import React, { PureComponent } from "react";
import { Line } from "react-chartjs-2";
import _ from "lodash";
import chartWithLoading from "../helpers/chartWithLoading";
import { benchmarkColors } from "../helpers/util";
import profilingTooltipPlugin from "../helpers/profilingTooltipPlugin";
import yAxisGridLinesPlugin from "../helpers/yAxisGridLinesPlugin";
import drawBackgroundPlugin from "../helpers/drawBackgroundPlugin";
import tooltipBarPlugin from "../helpers/tooltipBarPlugin";
import confidenceIntervalPlugin from "../helpers/confidenceIntervalPlugin";
import drawLabelsPlugin from "../helpers/drawLabelsPlugin";
import noTooltipPlugin from "../helpers/noTooltipPlugin";


class ProfilingChart extends PureComponent {

  state = { highlightedBenchmark: null }

  constructor(props) {
    super(props);
    this.benchmarks = _.sortBy(_.keys(props.data.results));
  }

  componentDidUpdate() {
    // HACK: Put the highlighted line in the front
    // react-chartjs-2 does a shallow diff & update to the chart when there's
    // an update to the datasets, but if there's a change in the order of
    // datasets (through modifying component's data prop), react-chartjs-2
    // wouldn't catch that. However, directly calling Chart.js' update method
    // would catch that change.
    const { highlightedBenchmark } = this.state;
    const chart = this.refs.chart.chart_instance;

    let datasets = chart.config.data.datasets.map(dataset => {
      if (dataset.highlighted === false) {
        dataset.borderColor = "rgba(238, 240, 250, 0.7)";
        dataset.pointHoverRadius = 0;
      }
    })

    datasets = _.sortBy(
      chart.config.data.datasets,
      dataset => (
        // highlighted line should be placed at 0 in the datasets array
        dataset.label === highlightedBenchmark
          ? -Infinity
          : _.indexOf(this.benchmarks, dataset.label)
      )
    );

    chart.config.data.datasets = datasets;
    chart.update();

  }

  getData() {
    const { highlightedBenchmark } = this.state;
    const { results } = this.props.data;

    let datasets = _.entries(results).map(([benchmark, points], i) => ({
      label: benchmark,
      highlighted: _.includes([benchmark, null], highlightedBenchmark),
      onlyHighlighted: highlightedBenchmark === benchmark,
      displayIndex: i, // Indicating position / ordering of legend
      data: points.map(row => ({
        x: row.intensity,
        y: row.mean,
        top: row.percentile_90,
        bottom: row.percentile_10
      })),
      fill: false,
      borderColor: benchmarkColors[benchmark],
      pointRadius: 0,
      pointHoverBorderColor: "#5677fa",
      pointHoverBackgroundColor:  "#fff",
      pointHoverRadius: 5
    }));

    return { datasets, highlightedBenchmark };
  }

  getOptions() {
    const component = this;
    return {
      layout: { padding: { top: 140 } },
      hover: {
        onHover(event) {

          // If a hover happens when a line is selected, don't do anything
          if (event.type !== "click" && component.state.selected)
            return;

          const yPos = event.layerY;
          // Calculate x position from the right
          const xPos = this.chartArea.right - event.layerX;

          if (yPos > 0 && yPos < 60) {
            // Break the loop and return whenever it finds the hovered area
            for (let i = 0; i < this.data.datasets.length; i++) {
              // See ../helpers/profilingTooltipPlugin.js for the calculation of legend positions
              if (xPos > (15 + 120 * i) && xPos < (15 + 120 * (i + 1))) {
                let benchmarkIndex = this.data.datasets.length - i - 1;
                let newState = {};
                let hoveredBenchmark = component.benchmarks[benchmarkIndex];

                if (event.type !== "click") {
                  // Normal hover handling
                  newState.highlightedBenchmark = hoveredBenchmark;

                } else {

                  if (!component.state.selected) {
                    // Freeze the highlight of one benchmark after clicking
                    newState.selected = true;
                    newState.highlightedBenchmark = hoveredBenchmark;
                  } else {

                    // Deselect if clicking on the selected benchmark
                    if (hoveredBenchmark === component.state.highlightedBenchmark) {
                      newState.selected = false;
                    } else {
                      newState.highlightedBenchmark = hoveredBenchmark;
                    }
                  }
                }

                component.setState(newState);
                return;
              }
            }
          }
          // Reset hover state if nothing matched
          if (event.type === "click") {
            component.setState({ highlightedBenchmark: null, selected: false });
          } else if (!component.state.selected) {
            component.setState({ highlightedBenchmark: null });
          }
        }
      },
      scales: {
        xAxes: [{
          type: "linear",
          ticks: {
            fontColor: "#e5e6e8",
            display: true,
            min: 0,
            max: 110,
            stepSize: 25,
            callback: x => x === 110 ? null : x
          },
        }],
        yAxes: [{
          color: "#eef0fa",
          scaleLabel: {
            labelString: "QoS Value"
          }
        }]
      }
    }
  }

  render() {
    return <Line
      ref="chart"
      data={this.getData()}
      options={this.getOptions()}
      plugins={[
        drawBackgroundPlugin,
        yAxisGridLinesPlugin,
        drawLabelsPlugin,
        noTooltipPlugin,
        confidenceIntervalPlugin,
        tooltipBarPlugin,
        profilingTooltipPlugin
      ]} />;
  }

}

export default chartWithLoading(ProfilingChart)
