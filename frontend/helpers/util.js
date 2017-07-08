export const numberWithCommas = (x) => (
  x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
);

export const colors = ["#c1ccf9", "#8cb1fa", "#acaecd", "#e5e6e8", "#78c1fa", "#6590e2", "#606175"];
