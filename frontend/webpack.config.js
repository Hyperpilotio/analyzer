const webpack = require("webpack");
const ExtractTextPlugin = require("extract-text-webpack-plugin");
const WebpackCleanupPlugin = require("webpack-cleanup-plugin");
const GitRevisionPlugin = require('git-revision-webpack-plugin')

const extractSass = new ExtractTextPlugin({
  filename: "[hash].bundle.css",
  disable: process.env.NODE_ENV !== "production"
});

const gitRevisionPlugin = new GitRevisionPlugin()


let config = module.exports = {
  entry: [
    "babel-polyfill",
    "webpack-dev-server/client?http://localhost:3000",
    "webpack/hot/only-dev-server",
    "react-hot-loader/patch",
    "./index.js",
    "./styles/index.sass"
  ],
  output: {
    path: __dirname + "/dist",
    filename: "[hash].bundle.js",
    publicPath: "/dist/"
  },
  devtool: "inline-source-map",
  module: {
    rules: [
      {
        test: /\.js?$/,
        loader: "babel-loader",
        query: {
          presets: ["es2015", "react", "stage-0"],
          plugins: ["react-hot-loader/babel"]
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
    new webpack.HotModuleReplacementPlugin(),
    new webpack.DefinePlugin({
      "process.env": {
        NODE_ENV: JSON.stringify(process.env.NODE_ENV),
        REACT_SPINKIT_NO_STYLES: "true",
        GIT_COMMIT: JSON.stringify(gitRevisionPlugin.commithash())
      }
    }),
    extractSass,
    function() {
      this.plugin("done", stats => {
        const data = stats.toJson();
        let outputStats;
        if (process.env.NODE_ENV === "production") {
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
        require("fs").writeFileSync(
          __dirname + "/dist/stats.json",
          JSON.stringify(outputStats)
        );
      });
    }
  ],
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


if (process.env.NODE_ENV === "production") {
  config.plugins.push(new webpack.optimize.UglifyJsPlugin({
    comments: false
  }));
}
