import React from "react";
import ReactEcharts from "echarts-for-react";
import _ from "lodash";


const renderErrorBar = (params, api) => {
  let xValue = api.value(0);
  let [xCoord, minPoint] = api.coord([xValue, api.value(1)]);
  let [_, maxPoint] = api.coord([xValue, api.value(2)]);

  let style = api.style({
    stroke: api.visual("color")
  });

  return {
    type: "group",
    children: [
      {
        type: "line",
        shape: {
          x1: xCoord, y1: minPoint,
          x2: xCoord, y2: maxPoint
        },
        style: style
      },
      {
        type: "line",
        shape: {
          x1: xCoord - 5, y1: maxPoint,
          x2: xCoord + 5, y2: maxPoint
        },
        style: style
      },
      {
        type: "line",
        shape: {
          x1: xCoord - 5, y1: minPoint,
          x2: xCoord + 5, y2: minPoint
        },
        style: style
      }
    ]
  };
};


export default ({ data, loading }) => {
  let options = { series: [] };

  if (data !== null) {
		const results = data.testResult;
		const minValue = _.min(_.map(results, "min"));
		const maxValue = _.max(_.map(results, "max"));
		const minX = _.min(_.map(results, "loadIntensity"));
		const maxX = _.max(_.map(results, "loadIntensity"));

		const finalIntensityIndex = _.findIndex(results, {loadIntensity: data.finalIntensity});

    options = {
      title: {
        text: "Calibration Results",
        subtext: `App: ${data.appName}, Load Tester: ${data.loadTester}, Final Intensity: ${data.finalIntensity}`,
        left: "center"
      },
      tooltip: {
        trigger: "axis",
        formatter: (params) => {
          let mean = params[0];
          let minMax = params[1];
          return `Load Intesity: ${mean.axisValue}<br />
                  ${mean.marker} ${data.qosMetrics[0]}:<br />
                  Mean: ${mean.data[1].toFixed(2)}<br />
                  Min: ${minMax.data[1]}<br />
                  Max: ${minMax.data[2]}`;
        }
      },
      xAxis: [{
        type: "value",
        name: "Load Intensity",
        min: _.max([(minX - (maxX - minX) * 0.1).toPrecision(2), 0]),
        max: (maxX + (maxX - minX) * 0.1).toPrecision(2)
      }],
      yAxis: [{
        name: data.qosMetrics[0],
        type: "value",
        min: _.max([0, (minValue - (maxValue - minValue) * 0.1).toPrecision(2)]),
        max: (maxValue + (maxValue - minValue) * 0.1).toPrecision(2)
      }],
      series: [
        {
          name: data.qosMetrics[0],
          type: "line",
          data: results.map(row => [row.loadIntensity, row.mean]),
          markArea: {
            label: {
              normal: {
                position: "bottom",
                offset: [0, 20]
              },
              emphasis: {
                position: "bottom",
                offset: [0, 20]
              }
            },
            data: [
              [
                { name: "Final Intensity",
                  xAxis: data.finalIntensity - (data.finalIntensity - results[finalIntensityIndex - 1].loadIntensity) / 4 },
                { xAxis: data.finalIntensity + (results[finalIntensityIndex + 1].loadIntensity - data.finalIntensity) / 4 }
              ]
            ]
          }
        },
        {
          name: "minmax",
          type: "custom",
          data: results.map(row => [row.loadIntensity, row.min, row.max]),
          renderItem: renderErrorBar,
          itemStyle: {
            normal: {
              borderWidth: 1.5,
              color: "#77bef7"
            }
          }
        }
      ]
    };
  }

  return <ReactEcharts
    style={{height: "500px", paddingLeft: "256px"}}
    option={options}
    showLoading={loading}
  />;
}
