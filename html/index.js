function makeChart(data) {
  console.log(data)

  var dates = data.map(function (d) {
    return d.Date;
  });
  var confirmedData = data.map(function (d) {
    return +d.Confirmed;
  });

  var chart = new Chart('chart', {
    type: "line",
    options: {
      responsive: true,
      maintainAspectRatio: false,
      legend: {
        display: false
      },
      scales: {
        y: {
          min: 0
        }
      },
    },
    data: {
      labels: dates,
      datasets: [
        {
          data: confirmedData
        }
      ]
    }
  });
}

Papa.parse("snapcraft-launchpad.csv", {
  download: true,
  dynamicTyping: true,
  header: true,
  complete: function (data) {
    makeChart(data.data)
  }
});
