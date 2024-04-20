// Create a chart from CSV data
// Data will be inserted into the div with the given id
function chartData(data, id) {
  var div = document.getElementById(id);
  var table = document.createElement('table');
  var header_group = document.createElement("thead");
  var body_group = document.createElement("tbody");

  var is_header = true;
  var row_name = "th";

  // Iterate through the parsed data
  data.forEach(function(rowData) {
    // Create a row for each row of data
    if (rowData[0] === null) {
      return; // Skips the current iteration
    }
    var row = document.createElement('tr');

    // Iterate through the row's data and create cells
    rowData.forEach(function(cellData) {
      var cell = document.createElement(row_name);
      let text = cellData.toString()
      let attr = "u-align--right"
      if (text.startsWith("!")) {
        attr += " outdated"
        text = text.replace("!", "")
      } else if (text == "not used") {
        attr += " not-used"
      }
      cell.setAttribute("class", attr)

      var textNode = document.createTextNode(text);
      cell.appendChild(textNode);
      row.appendChild(cell);
    });

    // Add the row to the table
    if (is_header) {
      header_group.appendChild(row);
      is_header = false;
      row_name = "td";
    } else {
      body_group.appendChild(row);
    }

  });
  table.appendChild(header_group);
  table.appendChild(body_group);
  div.appendChild(table);

}


function graphIssues(project, data) {
  /*
    A bunch of javascript to create the following HTML:
    <div class="row--25-75">
      <div class="col">
        <p class="p-muted-heading"><project> issues</p>
      </div>
      <div class="col">
        <canvas id="<project>-issues" style="width: 70vw;"></canvas>
        <hr>
      </div>
    </div>
  */

  let previousElement = document.getElementById("releases-and-commits");
  let chartDiv = document.createElement("div");
  chartDiv.setAttribute("class", "row--25-75");
  let col1 = document.createElement("div");
  col1.setAttribute("class", "col");
  chartDiv.appendChild(col1);
  let title = document.createElement("p");
  title.setAttribute("class", "p-muted-heading");
  title.textContent = `${project}: open issues`;
  col1.appendChild(title);
  let col2 = document.createElement("div");
  col2.setAttribute("class", "col");
  chartDiv.appendChild(col2);
  let canvas = document.createElement("canvas");
  canvas.setAttribute("id", `${project}-issues`);
  canvas.setAttribute("style", "width: 70vw;");
  col2.appendChild(canvas);
  let hr = document.createElement("hr");
  col2.appendChild(hr);
  previousElement.parentNode.insertBefore(chartDiv, previousElement.nextSibling)
  const ctx = document.getElementById(`${project}-issues`);

  // load data from csv file into arrays
  var dates = data.map(function (d) {
    return d.date;
  });
  var issues = data.map(function (d) {
    return d.issues_avg;
  });
  var age = data.map(function (d) {
    return d.age;
  });

  // graph the data
  const myChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [{
        label: 'Open issues',
        data: issues,
      }]
    },
    options: {
      elements: {
        point: {
          radius: 0
        },
        line: {
          borderColor: '#000000',
        }
      },
      responsive: true,
      plugins: {
        legend: {
          display: false,
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            precision: 0
          }
        }
      }
    }
  });
}

let projects = [
    "all-projects",
    "charmcraft",
    "rockcraft",
    "snapcraft",
    "craft-application",
    "craft-archives",
    "craft-cli",
    "craft-grammar",
    "craft-parts",
    "craft-providers",
    "craft-store",
    "starbase",
];


Papa.parse("data/app-deps.csv", {
  download: true,
  dynamicTyping: true,
  header: false,
  complete: function (data) {
    chartData(data.data, "libs-and-apps-table")
  }
});


Papa.parse("data/releases.csv", {
  download: true,
  dynamicTyping: true,
  header: false,
  complete: function (data) {
    chartData(data.data, "releases-and-commits-table")
  }
});


// todo: sleep for a 0.1 seconds or so between loading each graph
// because they seem to get placed out-of-order
projects.reverse().forEach(function (project) {
  Papa.parse(`data/${project}-github.csv`, {
    download: true,
    dynamicTyping: true,
    header: true,
    complete: function (data) {
      graphIssues(project, data.data)
    }
  });
});
