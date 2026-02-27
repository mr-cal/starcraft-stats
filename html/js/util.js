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
