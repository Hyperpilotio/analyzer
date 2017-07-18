export default {
  beforeDraw: ({ scale }) => {
    // Adjusting margin for point labels in a hacky way
    scale._pointLabelSizes.forEach(size => {
      size.h = 18;
    });
  }
}
