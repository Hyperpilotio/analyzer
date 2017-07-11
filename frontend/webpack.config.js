const webpack = require("webpack");
const ExtractTextPlugin = require("extract-text-webpack-plugin");
const WebpackCleanupPlugin = require("webpack-cleanup-plugin");

const extractSass = new ExtractTextPlugin({
  filename: "[hash].bundle.css",
  disable: process.env.NODE_ENV !== "production"
});


let config = module.exports = {
  entry: [
    "babel-polyfill",
    "./app.js",
    "./styles/index.sass"
  ],
  output: {
    path: __dirname + "/dist",
    filename: "[hash].bundle.js",
    publicPath: "/dist/"
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
        test: /\.s[ca]ss|css$/,
        use: extractSass.extract({
          fallback: "style-loader",
          use: [
            "css-loader", "sass-loader",
            {
              loader: "resolve-url-loader",
              query: {
                silent: true
              }
            }
          ]
        })
      },
      {
        test: /\.(jpe?g|png|gif|svg|ttf|woff|woff2)$/i,
        loader: "file-loader"
      }
    ]
  },
  plugins: [
    new WebpackCleanupPlugin(),
    new webpack.DefinePlugin({
      "process.env": {
        NODE_ENV: JSON.stringify(process.env.NODE_ENV),
        REACT_SPINKIT_NO_STYLES: "true"
      }
    }),
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


if (process.env.NODE_ENV === "production") {
  config.plugins.push(new webpack.optimize.UglifyJsPlugin({
    comments: false
  }));
}
