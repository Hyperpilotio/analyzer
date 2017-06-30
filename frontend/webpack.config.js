const ExtractTextPlugin = require("extract-text-webpack-plugin");
const WebpackCleanupPlugin = require("webpack-cleanup-plugin");

const extractSass = new ExtractTextPlugin({
  filename: "[hash].bundle.css",
  disable: process.env.NODE_ENV !== "production"
});


module.exports = {  
  entry: [
    "babel-polyfill",
    "./app.js",
    "./styles/index.scss"
  ],
  output: {
    path: __dirname + "/dist",
    filename: "[hash].bundle.js"
  },
  devtool: "inline-source-map",
  module: {
    loaders: [
      {
        test: /\.js?$/,
        loader: "babel-loader",
        query: {
          presets: ["es2015", "react", "stage-0"],
        },
        exclude: /node_modules/
      },
      {
        test: /\.s[ca]ss$/,
        use: extractSass.extract({
          fallback: "style-loader",
          use: ["css-loader", "sass-loader"]
        })
      }
    ]
  },
  plugins: [
    new WebpackCleanupPlugin(),
    extractSass,
    function() {
      this.plugin("done", stats => {
        const data = stats.toJson();
        let outputStats;
        if (typeof data.assetsByChunkName.main === "string") {
          outputStats = { main: data.assetsByChunkName.main };
        } else {
          outputStats = {
            main: data.assetsByChunkName.main[0],
            css: data.assetsByChunkName.main[1]
          };
        }
        require("fs").writeFileSync(
          __dirname + "/dist/stats.json",
          JSON.stringify(outputStats)
        );
      });
    }
  ]
};
