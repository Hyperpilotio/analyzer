var webpack = require('webpack');  
module.exports = {  
  entry: [
    "babel-polyfill",
    "./app.js"
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
          presets: ['es2015', 'react', 'stage-0'],
        },
        exclude: /node_modules/
      }
    ]
  },
  plugins: [
  ]
};
