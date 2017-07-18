// Final Intensity Marking Area

export default {
  beforeDatasetsDraw: ({ ctx, options, scales }) => {
    const xScale = scales["x-axis-0"];
    const yScale = scales["y-axis-0"];
    const intensityAreaWidth = (xScale.right - xScale.left) / 40;
    const pointX = xScale.getPixelForValue(options.plugins.finalIntensity.value);

    if (options.plugins.finalIntensity.fillStyle)
      ctx.fillStyle = options.plugins.finalIntensity.fillStyle;

    ctx.fillRect(
      pointX - intensityAreaWidth / 2, // upper-left x
      0, // upper-left y
      intensityAreaWidth, // width
      yScale.bottom // height
    );
  }
}
