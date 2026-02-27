/**
 * Create a chart from CSV data
 * @param {*} data a 2D array of data to chart where the first row is contains the headers
 * @param {*} id the id of the HTML div to insert the chart into
 */
export function chartData(data, id) {
  const div = document.getElementById(id);
  const table = document.createElement("table");
  const header_group = document.createElement("thead");
  const body_group = document.createElement("tbody");

  let is_header = true;
  let row_name = "th";

  // Iterate through the parsed data
  for (const rowData of data) {
    // Create a row for each row of data
    if (rowData[0] === null) {
      continue; // Skips the current iteration
    }
    const row = document.createElement("tr");

    // Iterate through the row's data and create cells
    for (const cellData of rowData) {
      const cell = document.createElement(row_name);
      let text = cellData.toString();
      let attr = "u-align--right";
      if (text.startsWith("!")) {
        attr += " outdated";
        text = text.replace("!", "");
      } else if (text === "not used") {
        attr += " not-used";
      }
      cell.setAttribute("class", attr);
      cell.innerHTML = text;
      row.appendChild(cell);
    }

    // Add the row to the table
    if (is_header) {
      header_group.appendChild(row);
      is_header = false;
      row_name = "td";
    } else {
      body_group.appendChild(row);
    }
  }
  table.appendChild(header_group);
  table.appendChild(body_group);
  div.appendChild(table);
}

/**
 * Create a graph of open issues for a project
 * @param {*} project the name of the project
 * @param {*} data the data to graph
 * @param {*} previousElementId id of the html element to insert the graph after
 */
export function graphIssues(project, data, previousElementId) {
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

  const previousElement = document.getElementById(previousElementId);
  const chartDiv = document.createElement("div");
  chartDiv.setAttribute("class", "row--25-75");
  chartDiv.setAttribute("id", `${project}-chart-div`);
  const col1 = document.createElement("div");
  col1.setAttribute("class", "col");
  chartDiv.appendChild(col1);
  const title = document.createElement("p");
  title.setAttribute("class", "p-muted-heading");
  title.textContent = `${project}: open issues`;
  col1.appendChild(title);
  const col2 = document.createElement("div");
  col2.setAttribute("class", "col");
  chartDiv.appendChild(col2);
  const canvas = document.createElement("canvas");
  canvas.setAttribute("id", `${project}-issues`);
  canvas.setAttribute("style", "width: 70vw;");
  col2.appendChild(canvas);
  const hr = document.createElement("hr");
  col2.appendChild(hr);
  previousElement.parentNode.insertBefore(
    chartDiv,
    previousElement.nextSibling,
  );
  const ctx = document.getElementById(`${project}-issues`);

  // load data into arrays
  const dates = data.map((d) => d.date);
  const issues = data.map((d) => d.issues_avg);
  const age = data.map((d) => d.age);

  // graph the data
  const myChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Open issues",
          data: issues,
        },
      ],
    },
    options: {
      elements: {
        point: {
          radius: 0,
        },
        line: {
          borderColor: "#000000",
        },
      },
      responsive: true,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            precision: 0,
          },
        },
      },
    },
  });
}
