var webpack = require('webpack');  
module.exports = {  
  entry: [
    "babel-polyfill",
    "./js/app.js"
  ],
  output: {
    path: __dirname + '/dist',
    filename: "bundle.js"
  },
  devtool: 'inline-source-map',
  module: {
    loaders: [
      {
        test: /\.js?$/,
        loader: 'babel-loader',
        query: {
          presets: ['es2015', 'react', 'stage-3'],
        },
        exclude: /node_modules/
      }
    ]
  },
  plugins: [
  ]
};
