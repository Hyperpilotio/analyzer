import { AppContainer } from 'react-hot-loader';
import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';


const rootEl = document.getElementById("react-root");
const render = Component =>
  ReactDOM.render(
    <AppContainer>
      <Component />
    </AppContainer>,
    rootEl
  );

render(App);
if (module.hot) {
  module.hot.accept("./App", () => {
    const App = require("./App").default;
    render(App);
  });
}
