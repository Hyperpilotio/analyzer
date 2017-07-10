import { numberWithCommas } from "./util";

export default {
  afterDraw: ({ ctx, scales }) => {
    ctx.save();

    // Draw ticks
    let yScale = scales["y-axis-0"];
    let xScale = scales["x-axis-0"];
    let xPos = xScale.getPixelForTick(0);
    ctx.fillStyle = "#e5e6e8";
    ctx.textBaseline = "top";
    for (let i = 0; i < yScale.ticks.length - 1; i ++) {
      let yPos = yScale.getPixelForTick(i) + 5;
      ctx.fillText(numberWithCommas(yScale.ticks[i]), xPos, yPos);
    }

    // Draw y-axis title
    ctx.fillStyle = "#b9bacb";
    ctx.font = "14px WorkSans";
    ctx.fillText(yScale.options.scaleLabel.labelString, xPos, 10);

    // Draw x-axis title
    const xLabel = xScale.options.scaleLabel.labelString;
    xPos = xScale.right - ctx.measureText(xLabel).width;
    ctx.fillText(xLabel, xPos, yScale.bottom - 20);

    ctx.restore();
  }
}
