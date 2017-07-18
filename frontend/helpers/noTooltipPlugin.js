export default {
  afterInit: ({ tooltip }) => {
    tooltip.draw = () => {};
  }
}
