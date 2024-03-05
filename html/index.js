function snapcraftDeps(data) {
    console.log(data)
    var div = document.getElementById("app-deps");
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
        cell.setAttribute("class", "u-align--right")
        var textNode = document.createTextNode(cellData);
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

Papa.parse("data/app-deps.csv", {
    download: true,
    dynamicTyping: true,
    header: false,
    complete: function (data) {
        snapcraftDeps(data.data)
    }
});
