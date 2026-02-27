import { chartData } from "./util.js";

/* Graph the releases and commits */
Papa.parse("data/releases.csv", {
  download: true,
  dynamicTyping: true,
  header: false,
  complete: function (data) {
    chartData(data.data, "releases-and-commits-table");
  },
});
