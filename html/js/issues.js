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
const AGE_ROLLING_WINDOW = 4;
const CLOSED_ROLLING_WINDOW = 30;

/**
 * Compute a rolling average over an array of numbers.
 */
function rollingAverage(values, windowSize) {
  return values.map((_, i) => {
    const start = Math.max(0, i - windowSize + 1);
    const window = values.slice(start, i + 1);
    return window.reduce((sum, v) => sum + v, 0) / window.length;
  });
}

/**
 * Compute a rolling average over an array of nullable numbers, skipping nulls.
 * Returns null for windows where all values are null.
 */
function rollingAverageNullable(values, windowSize) {
  return values.map((_, i) => {
    const start = Math.max(0, i - windowSize + 1);
    const window = values.slice(start, i + 1).filter((v) => v !== null);
    if (window.length === 0) return null;
    return window.reduce((sum, v) => sum + v, 0) / window.length;
  });
}

// Storage for project data and chart instances
const projectData = {};
let chart = null;
let ageChart = null;
let closedChart = null;

// Which data series to display
let showAll = true;
let showContributors = false;

/**
 * Generate a distinct color for a project
 */
function getProjectColor(index) {
  return colors[index % colors.length];
}

/**
 * Resolve the CSV file path for a project key.
 * Launchpad projects use the "(launchpad)" suffix convention.
 */
function csvPath(project) {
  if (project.endsWith(" (launchpad)")) {
    return `data/${project.replace(" (launchpad)", "")}-launchpad.csv`;
  }
  return `data/${project}-github.csv`;
}

/**
 * Load CSV data for a project
 */
function loadProjectData(project, index) {
  Papa.parse(csvPath(project), {
    download: true,
    dynamicTyping: true,
    header: true,
    complete: (result) => {
      projectData[project] = {
        dates: result.data.map((d) => d.date),
        issues: rollingAverage(
          result.data.map((d) => d.issues),
          ROLLING_WINDOW,
        ),
        age: rollingAverageNullable(
          result.data.map((d) => (d.age !== "" ? d.age : null)),
          AGE_ROLLING_WINDOW,
        ),
        closed: rollingAverage(
          result.data.map((d) => d.closed ?? 0),
          CLOSED_ROLLING_WINDOW,
        ).map((v) => v * 7),
        nm_issues: rollingAverage(
          result.data.map((d) => d.nm_issues ?? 0),
          ROLLING_WINDOW,
        ),
        nm_age: rollingAverageNullable(
          result.data.map((d) =>
            d.nm_age !== "" && d.nm_age != null ? d.nm_age : null,
          ),
          AGE_ROLLING_WINDOW,
        ),
        nm_closed: rollingAverage(
          result.data.map((d) => d.nm_closed ?? 0),
          CLOSED_ROLLING_WINDOW,
        ).map((v) => v * 7),
        color: getProjectColor(index),
      };

      // Once all projects are loaded, initialize the UI
      if (Object.keys(projectData).length === projects.length) {
        initializeUI();
      }
    },
    error: (error) => {
      console.error(`Error loading ${project}:`, error);
      // Still mark as attempted so other projects aren't blocked
      projectData[project] = null;
      if (Object.keys(projectData).length === projects.length) {
        initializeUI();
      }
    },
  });
}

/**
 * Populate a checkbox container with one checkbox per project.
 */
function createProjectCheckboxes(containerId, checkboxPrefix, onChange) {
  const container = document.getElementById(containerId);

  for (const project of projects) {
    if (!projectData[project]) continue;

    const labelEl = document.createElement("label");
    labelEl.htmlFor = `${checkboxPrefix}-${project}`;
    labelEl.style.cssText = "display:flex;align-items:center;gap:0.4rem;cursor:pointer;margin-bottom:0.3rem;";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = `${checkboxPrefix}-${project}`;
    checkbox.value = project;
    checkbox.checked = project === "all-projects";
    checkbox.addEventListener("change", onChange);

    const colorBox = document.createElement("span");
    colorBox.style.cssText = `display:inline-block;width:12px;height:12px;flex-shrink:0;background-color:${projectData[project].color};border:1px solid #666;`;

    labelEl.appendChild(checkbox);
    labelEl.appendChild(colorBox);
    labelEl.appendChild(document.createTextNode(project));
    container.appendChild(labelEl);
  }
}

/**
 * Create view-mode checkboxes and wire up events.
 * Runs immediately so the checkboxes appear before project data loads.
 */
function initializeViewToggle() {
  const container = document.getElementById("view-checkboxes");
  if (!container) return;

  const viewOptions = [
    { id: "view-all", label: "All issues", getter: () => showAll, setter: (v) => { showAll = v; } },
    { id: "view-contributors", label: "Only contributor issues", getter: () => showContributors, setter: (v) => { showContributors = v; } },
  ];

  for (const { id, label, getter, setter } of viewOptions) {
    const labelEl = document.createElement("label");
    labelEl.htmlFor = id;
    labelEl.style.cssText = "display:flex;align-items:center;gap:0.5rem;cursor:pointer;margin-bottom:0.4rem;";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = id;
    checkbox.checked = getter();
    checkbox.addEventListener("change", () => {
      setter(checkbox.checked);
      updateChart();
      updateAgeChart();
      updateClosedChart();
    });

    labelEl.appendChild(checkbox);
    labelEl.appendChild(document.createTextNode(label));
    container.appendChild(labelEl);
  }
}

/**
 * Initialize checkboxes and charts once all project data is loaded.
 */
function initializeUI() {
  createProjectCheckboxes("project-checkboxes", "checkbox", updateChart);
  createProjectCheckboxes("age-checkboxes", "age-checkbox", updateAgeChart);
  createProjectCheckboxes(
    "closed-checkboxes",
    "closed-checkbox",
    updateClosedChart,
  );

  initializeViewToggle();
  initializeChart();
  initializeAgeChart();
  initializeClosedChart();
  updateChart();
  updateAgeChart();
  updateClosedChart();
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
    return checkbox?.checked;
  });

  if (selectedProjects.length === 0 || (!showAll && !showContributors)) {
    chart.data.labels = [];
    chart.data.datasets = [];
    chart.update();
    return;
  }

  const firstProject = selectedProjects[0];
  chart.data.labels = projectData[firstProject].dates;

  if (showAll && showContributors) {
    chart.data.datasets = selectedProjects.flatMap((project) => [
      {
        label: `${project} (all)`,
        data: projectData[project].issues,
        borderColor: projectData[project].color,
        backgroundColor: `${projectData[project].color}20`,
        borderWidth: 2,
        fill: false,
        tension: 0.1,
      },
      {
        label: `${project} (contributors)`,
        data: projectData[project].nm_issues,
        borderColor: projectData[project].color,
        backgroundColor: `${projectData[project].color}20`,
        borderWidth: 2,
        borderDash: [6, 4],
        fill: false,
        tension: 0.1,
      },
    ]);
  } else {
    const dataKey = showContributors ? "nm_issues" : "issues";
    chart.data.datasets = selectedProjects.map((project) => ({
      label: project,
      data: projectData[project][dataKey],
      borderColor: projectData[project].color,
      backgroundColor: `${projectData[project].color}20`,
      borderWidth: 2,
      fill: false,
      tension: 0.1,
    }));
  }

  chart.update();
}

/**
 * Initialize the median issue age chart
 */
function initializeAgeChart() {
  const ctx = document.getElementById("age-chart");

  ageChart = new Chart(ctx, {
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
            text: "Median Issue Age (days)",
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
 * Update the age chart based on selected checkboxes
 */
function updateAgeChart() {
  const selectedProjects = projects.filter((project) => {
    const checkbox = document.getElementById(`age-checkbox-${project}`);
    return checkbox?.checked;
  });

  if (selectedProjects.length === 0 || (!showAll && !showContributors)) {
    ageChart.data.labels = [];
    ageChart.data.datasets = [];
    ageChart.update();
    return;
  }

  const firstProject = selectedProjects[0];
  ageChart.data.labels = projectData[firstProject].dates;

  if (showAll && showContributors) {
    ageChart.data.datasets = selectedProjects.flatMap((project) => [
      {
        label: `${project} (all)`,
        data: projectData[project].age,
        borderColor: projectData[project].color,
        backgroundColor: `${projectData[project].color}20`,
        borderWidth: 2,
        fill: false,
        tension: 0.1,
        spanGaps: false,
      },
      {
        label: `${project} (contributors)`,
        data: projectData[project].nm_age,
        borderColor: projectData[project].color,
        backgroundColor: `${projectData[project].color}20`,
        borderWidth: 2,
        borderDash: [6, 4],
        fill: false,
        tension: 0.1,
        spanGaps: false,
      },
    ]);
  } else {
    const dataKey = showContributors ? "nm_age" : "age";
    ageChart.data.datasets = selectedProjects.map((project) => ({
      label: project,
      data: projectData[project][dataKey],
      borderColor: projectData[project].color,
      backgroundColor: `${projectData[project].color}20`,
      borderWidth: 2,
      fill: false,
      tension: 0.1,
      spanGaps: false,
    }));
  }

  ageChart.update();
}

/**
 * Initialize the closed-issues-per-day chart
 */
function initializeClosedChart() {
  const ctx = document.getElementById("closed-chart");

  closedChart = new Chart(ctx, {
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
            text: "Issues Closed / Week (30-day avg)",
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
 * Update the closed-issues chart based on selected checkboxes
 */
function updateClosedChart() {
  const selectedProjects = projects.filter((project) => {
    const checkbox = document.getElementById(`closed-checkbox-${project}`);
    return checkbox?.checked;
  });

  if (selectedProjects.length === 0 || (!showAll && !showContributors)) {
    closedChart.data.labels = [];
    closedChart.data.datasets = [];
    closedChart.update();
    return;
  }

  const firstProject = selectedProjects[0];
  closedChart.data.labels = projectData[firstProject].dates;

  if (showAll && showContributors) {
    closedChart.data.datasets = selectedProjects.flatMap((project) => [
      {
        label: `${project} (all)`,
        data: projectData[project].closed,
        borderColor: projectData[project].color,
        backgroundColor: `${projectData[project].color}20`,
        borderWidth: 2,
        fill: false,
        tension: 0.1,
      },
      {
        label: `${project} (contributors)`,
        data: projectData[project].nm_closed,
        borderColor: projectData[project].color,
        backgroundColor: `${projectData[project].color}20`,
        borderWidth: 2,
        borderDash: [6, 4],
        fill: false,
        tension: 0.1,
      },
    ]);
  } else {
    const dataKey = showContributors ? "nm_closed" : "closed";
    closedChart.data.datasets = selectedProjects.map((project) => ({
      label: project,
      data: projectData[project][dataKey],
      borderColor: projectData[project].color,
      backgroundColor: `${projectData[project].color}20`,
      borderWidth: 2,
      fill: false,
      tension: 0.1,
    }));
  }

  closedChart.update();
}

// Load projects from the generated config and initialize the page
const response = await fetch("data/projects.json");
const { applications, libraries, launchpad } = await response.json();

// Order: all-projects first, then applications (alpha), then libraries (alpha),
// then launchpad projects displayed as "{name} (launchpad)"
const launchpadProjects = (launchpad ?? []).map((p) => `${p} (launchpad)`);
const projects = [
  "all-projects",
  ...applications,
  ...libraries,
  ...launchpadProjects,
];

// Load all project data
projects.forEach((project, index) => {
  loadProjectData(project, index);
});
