import _ from "lodash";
import { numberWithCommas } from "./util";

export default {
  afterDraw: ({ tooltip, ctx }) => {
    ctx.save();
    ctx.textBaseline = "top";
    // Draw tooltip
    const vm = tooltip._view;
    if (!_.isUndefined(tooltip.currentPoints)) {
      let [mean, min, max] = tooltip.currentPoints;

      ctx.textAlign = vm.xAlign;

      let texts = [
        { style: "important", text: mean.xLabel, label: "Load intensity" },
        {
          style: "important",
          text: numberWithCommas(Number(mean.yLabel.toFixed(2))),
          label: "Mean"
        },
        {
          style: "secondary",
          text: numberWithCommas(Number(min.yLabel.toFixed(2))),
          label: "Min"
        },
        {
          style: "secondary",
          text: numberWithCommas(Number(max.yLabel.toFixed(2))),
          label: "Max"
        }
      ];

      let xPos = mean.x + (vm.xAlign === "left" ? 15 : -15)

      texts.forEach(({ style, text, label }, i) => {
        if (style === "important") {
          ctx.font = "bold 20px WorkSans";
          ctx.fillStyle = "#5677fa";
        } else if (style === "secondary") {
          ctx.font = "bold 16px WorkSans";
          ctx.fillStyle = "#606175";
        }

        // Draw individual staticstic
        let yPos = 5 + 40 * i;
        ctx.fillText(text, xPos, yPos);

        ctx.font = "lighter 10px WorkSans";
        ctx.fillStyle = "#b9bacb";
        // Draw label for statistics
        yPos += 20 + (style === "important") * 5
        ctx.fillText(label, xPos, yPos);
      });

    }
    ctx.restore();
  }
}
