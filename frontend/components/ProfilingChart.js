import React, { PureComponent } from "react";
import { Line } from "react-chartjs-2";
import _ from "lodash";
import chartWithLoading from "../helpers/chartWithLoading";
import { colors } from "../helpers/util";
import profilingTooltipPlugin from "../helpers/profilingTooltipPlugin";
import yAxisGridLinesPlugin from "../helpers/yAxisGridLinesPlugin";
import drawBackgroundPlugin from "../helpers/drawBackgroundPlugin";
import tooltipBarPlugin from "../helpers/tooltipBarPlugin";
import drawLabelsPlugin from "../helpers/drawLabelsPlugin";
import noTooltipPlugin from "../helpers/noTooltipPlugin";


class ProfilingChart extends PureComponent {

  state = { highlightedBenchmark: null }

  constructor(props) {
    super(props);
    this.benchmarks = _.sortBy(_.keys(props.data.testResult));
    this.colors = _.zipObject(
      this.benchmarks,
      colors.slice(0, this.benchmarks.length)
    );
  }

  componentDidUpdate() {
    // HACK: Put the highlighted line in the front
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
    const { testResult } = this.props.data;

    let datasets = _.entries(testResult).map(([benchmark, points], i) => ({
      label: benchmark,
      highlighted: _.includes([benchmark, null], highlightedBenchmark),
      displayIndex: i, // Indicating position / ordering of legend
      data: points.map(row => ({ x: row.intensity, y: row.mean })),
      fill: false,
      borderColor: this.colors[benchmark],
      pointRadius: 0,
      pointHoverBorderColor: "#5677fa",
      pointHoverBackgroundColor:  "#fff",
      pointHoverRadius: 5
    }));

    return { datasets };
  }

  getOptions() {
    const component = this;
    return {
      layout: { padding: { top: 80 } },
      hover: {
        onHover(event) {
          console.log(event.type);
          const yPos = event.layerY;
          // Calculate x position from the right
          const xPos = this.chartArea.right - event.layerX;

          if (yPos > 0 && yPos < 60) {
            // Break the loop and return whenever it finds the hovered area
            for (let i = 0; i < this.data.datasets.length; i++) {
              // See ../helpers/profilingTooltipPlugin.js for the calculation of legend positions
              if (xPos > (15 + 120 * i) && xPos < (15 + 120 * (i + 1))) {
                let benchmarkIndex = this.data.datasets.length - i - 1;
                component.setState({
                  highlightedBenchmark: component.benchmarks[benchmarkIndex]
                });
                return;
              }
            }
          }
          // Reset hover state if nothing matched
          component.setState({ highlightedBenchmark: null });
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
        tooltipBarPlugin,
        profilingTooltipPlugin
      ]} />;
  }

}

export default chartWithLoading(ProfilingChart)
