// Color palette for different projects
const colors = [
  "#E95420", // Ubuntu orange
  "#0E8420", // Green
  "#0066CC", // Blue
  "#772953", // Purple
  "#AEA79F", // Warm grey
  "#333333", // Dark grey
  "#007AA6", // Light blue
  "#C7162B", // Red
  "#F99B11", // Orange
  "#38B44A", // Light green
  "#5E2750", // Dark purple
  "#77216F", // Magenta
  "#335280", // Slate blue
];

const ROLLING_WINDOW = 4;

/**
 * Compute a rolling average over an array of numbers.
 */
function rollingAverage(values, windowSize) {
  return values.map((_, i) => {
    const start = Math.max(0, i - windowSize + 1);
    const window = values.slice(start, i + 1);
    return Math.floor(window.reduce((sum, v) => sum + v, 0) / window.length);
  });
}

// Storage for project data and chart instance
let projectData = {};
let chart = null;

/**
 * Generate a distinct color for a project
 */
function getProjectColor(index) {
  return colors[index % colors.length];
}

/**
 * Load CSV data for a project
 */
function loadProjectData(project, index) {
  Papa.parse(`data/${project}-github.csv`, {
    download: true,
    dynamicTyping: true,
    header: true,
    complete: function (result) {
      projectData[project] = {
        dates: result.data.map((d) => d.date),
        issues: rollingAverage(
          result.data.map((d) => d.issues),
          ROLLING_WINDOW,
        ),
        color: getProjectColor(index),
      };

      // Once all projects are loaded, initialize the UI
      if (Object.keys(projectData).length === projects.length) {
        initializeUI();
      }
    },
    error: function (error) {
      console.error(`Error loading ${project}:`, error);
    },
  });
}

/**
 * Initialize the checkboxes and chart
 */
function initializeUI() {
  const checkboxContainer = document.getElementById("project-checkboxes");

  projects.forEach((project, index) => {
    // Create checkbox wrapper
    const wrapper = document.createElement("div");
    wrapper.className = "p-checkbox";

    // Create checkbox input
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "p-checkbox__input";
    checkbox.id = `checkbox-${project}`;
    checkbox.value = project;

    // Check "all-projects" by default
    if (project === "all-projects") {
      checkbox.checked = true;
    }

    checkbox.addEventListener("change", updateChart);

    // Create label
    const label = document.createElement("label");
    label.className = "p-checkbox__label";
    label.htmlFor = `checkbox-${project}`;

    // Add color indicator
    const colorBox = document.createElement("span");
    colorBox.style.display = "inline-block";
    colorBox.style.width = "12px";
    colorBox.style.height = "12px";
    colorBox.style.backgroundColor = projectData[project].color;
    colorBox.style.marginRight = "8px";
    colorBox.style.border = "1px solid #666";

    label.appendChild(colorBox);
    label.appendChild(document.createTextNode(project));

    wrapper.appendChild(checkbox);
    wrapper.appendChild(label);
    checkboxContainer.appendChild(wrapper);
  });

  // Initialize the chart
  initializeChart();
  updateChart();
}

/**
 * Initialize the Chart.js chart
 */
function initializeChart() {
  const ctx = document.getElementById("issues-chart");

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      elements: {
        point: {
          radius: 0,
        },
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          display: true,
          title: {
            display: true,
            text: "Date",
          },
        },
        y: {
          display: true,
          beginAtZero: true,
          title: {
            display: true,
            text: "Open Issues",
          },
          ticks: {
            precision: 0,
          },
        },
      },
      interaction: {
        mode: "nearest",
        axis: "x",
        intersect: false,
      },
    },
  });
}

/**
 * Update chart based on selected checkboxes
 */
function updateChart() {
  const selectedProjects = projects.filter((project) => {
    const checkbox = document.getElementById(`checkbox-${project}`);
    return checkbox && checkbox.checked;
  });

  // If no projects selected, clear the chart
  if (selectedProjects.length === 0) {
    chart.data.labels = [];
    chart.data.datasets = [];
    chart.update();
    return;
  }

  // Use the dates from the first selected project
  const firstProject = selectedProjects[0];
  chart.data.labels = projectData[firstProject].dates;

  // Create datasets for each selected project
  chart.data.datasets = selectedProjects.map((project) => ({
    label: project,
    data: projectData[project].issues,
    borderColor: projectData[project].color,
    backgroundColor: projectData[project].color + "20", // Add transparency
    borderWidth: 2,
    fill: false,
    tension: 0.1,
  }));

  chart.update();
}

// Load projects from the generated config and initialize the page
const response = await fetch("data/projects.json");
const projects = await response.json();

// Load all project data
projects.forEach((project, index) => {
  loadProjectData(project, index);
});
