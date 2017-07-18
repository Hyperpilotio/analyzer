export const numberWithCommas = (x) => (
  x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
);

export const benchmarkColors = {
  cpu: "#c1ccf9",
  fio: "#8cb1fa",
  iperf: "#acaecd",
  l2: "#e5e6e8",
  l3: "#78c1fa",
  memBw: "#6590e2",
  memCap: "#606175"
};
