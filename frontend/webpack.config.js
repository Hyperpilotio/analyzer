const webpack = require("webpack");
const ExtractTextPlugin = require("extract-text-webpack-plugin");
const WebpackCleanupPlugin = require("webpack-cleanup-plugin");
const GitRevisionPlugin = require('git-revision-webpack-plugin')
const fs = require("fs");
const _ = require("lodash");

const IS_PROD = process.env.NODE_ENV === "production";

const extractSass = new ExtractTextPlugin({
  filename: "[hash].bundle.css",
  disable: !IS_PROD
});

const gitRevisionPlugin = new GitRevisionPlugin()


let config = module.exports = {
  entry: _.filter([
    "whatwg-fetch",
    "babel-polyfill",
    IS_PROD ? null : "webpack-dev-server/client?http://localhost:3000",
    IS_PROD ? null : "webpack/hot/only-dev-server",
    IS_PROD ? null : "react-hot-loader/patch",
    "./index.js",
    "./styles/index.sass"
  ]),
  output: {
    path: __dirname + "/dist",
    filename: "[hash].bundle.js",
    publicPath: "/dist/"
  },
  devtool: IS_PROD ? "source-map" : "eval",
  module: {
    rules: [
      {
        test: /\.js?$/,
        loader: "babel-loader",
        query: {
          presets: ["es2015", "react", "stage-0"],
          plugins: _.filter([
            IS_PROD ? null : "react-hot-loader/babel"
          ])
        },
        exclude: /node_modules/
      },
      {
        test: /\.s[ca]ss|css$/,
        use: extractSass.extract({
          fallback: "style-loader",
          use: [
            {
              loader: "css-loader",
              query: {
                minimize: IS_PROD
              }
            },
            "sass-loader",
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
  plugins: _.filter([
    new WebpackCleanupPlugin(),
    new webpack.DefinePlugin({
      "process.env": {
        NODE_ENV: JSON.stringify(process.env.NODE_ENV),
        REACT_SPINKIT_NO_STYLES: "true",
        GIT_COMMIT: JSON.stringify(gitRevisionPlugin.commithash())
      }
    }),
    extractSass,
    IS_PROD ? null : new webpack.HotModuleReplacementPlugin(),
    !IS_PROD ? null : new webpack.optimize.UglifyJsPlugin({ comments: false }),
    function() {
      this.plugin("done", stats => {
        const data = stats.toJson();
        let outputStats;
        if (IS_PROD) {
          outputStats = {
            main: data.assetsByChunkName.main[0],
            css: data.assetsByChunkName.main[1]
          };
        } else {
          if (typeof data.assetsByChunkName.main === "string") {
            outputStats = { main: data.assetsByChunkName.main };
          } else {
            outputStats = { main: data.assetsByChunkName.main[0] };
          }
        }
        if (!fs.existsSync(__dirname + "/dist")) {
          fs.mkdirSync(__dirname + "/dist");
        }
        fs.writeFileSync(
          __dirname + "/dist/stats.json",
          JSON.stringify(outputStats)
        );
      });
    }
  ]),
  devServer: {
    hot: true,
    historyApiFallback: true,
    contentBase: "./dist/",
    host: "localhost",
    port: 3000,
    proxy: {
      "*": "http://localhost:5000"
    }
  }
};
