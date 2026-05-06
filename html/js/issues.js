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
 * Create a styled checkbox item and append it to a container.
 * If colorBox is provided (a CSS color string), a small color swatch is shown.
 */
function createCheckboxItem(
  container,
  { id, label, checked, onChange, colorBox = null },
) {
  const labelEl = document.createElement("label");
  labelEl.htmlFor = id;
  labelEl.style.cssText =
    "display:flex;align-items:center;gap:0.4rem;cursor:pointer;margin-bottom:0.3rem;";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = id;
  checkbox.checked = checked;
  checkbox.addEventListener("change", () => onChange(checkbox.checked));

  labelEl.appendChild(checkbox);
  if (colorBox) {
    const swatch = document.createElement("span");
    swatch.style.cssText = `display:inline-block;width:12px;height:12px;flex-shrink:0;background-color:${colorBox};border:1px solid #666;`;
    labelEl.appendChild(swatch);
  }
  labelEl.appendChild(document.createTextNode(label));
  container.appendChild(labelEl);
}

/**
 * Populate a checkbox container with one checkbox per project.
 */
function createProjectCheckboxes(containerId, checkboxPrefix, onChange) {
  const container = document.getElementById(containerId);

  for (const project of projects) {
    if (!projectData[project]) continue;
    createCheckboxItem(container, {
      id: `${checkboxPrefix}-${project}`,
      label: project,
      checked: project === "all-projects",
      onChange: () => onChange(),
      colorBox: projectData[project].color,
    });
  }
}

/**
 * Create a new Chart.js line chart on the given canvas with a y-axis label.
 */
function createLineChart(canvasId, yLabel) {
  return new Chart(document.getElementById(canvasId), {
    type: "line",
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      elements: { point: { radius: 0 } },
      plugins: {
        legend: { display: false },
        tooltip: { mode: "index", intersect: false },
      },
      scales: {
        x: { display: true, title: { display: true, text: "Date" } },
        y: {
          display: true,
          beginAtZero: true,
          title: { display: true, text: yLabel },
          ticks: { precision: 0 },
        },
      },
      interaction: { mode: "nearest", axis: "x", intersect: false },
    },
  });
}

/**
 * Update a line chart based on the currently-checked project checkboxes.
 *
 * @param {Chart} chartRef - The Chart.js instance to update.
 * @param {string} checkboxPrefix - Prefix used for checkbox element IDs.
 * @param {string} allKey - projectData key for the "all issues" series.
 * @param {string} nmKey - projectData key for the "contributors only" series.
 * @param {object} extraDatasetProps - Extra dataset properties (e.g. { spanGaps: false }).
 */
function updateLineChart(
  chartRef,
  checkboxPrefix,
  allKey,
  nmKey,
  extraDatasetProps = {},
) {
  const selectedProjects = projects.filter((project) => {
    const checkbox = document.getElementById(`${checkboxPrefix}-${project}`);
    return checkbox?.checked;
  });

  if (selectedProjects.length === 0 || (!showAll && !showContributors)) {
    chartRef.data.labels = [];
    chartRef.data.datasets = [];
    chartRef.update();
    return;
  }

  chartRef.data.labels = projectData[selectedProjects[0]].dates;

  const makeDataset = (project, dataKey, label, isDashed) => ({
    label,
    data: projectData[project][dataKey],
    borderColor: projectData[project].color,
    backgroundColor: `${projectData[project].color}20`,
    borderWidth: 2,
    fill: false,
    tension: 0.1,
    ...(isDashed ? { borderDash: [6, 4] } : {}),
    ...extraDatasetProps,
  });

  if (showAll && showContributors) {
    chartRef.data.datasets = selectedProjects.flatMap((project) => [
      makeDataset(project, allKey, `${project} (all)`, false),
      makeDataset(project, nmKey, `${project} (contributors)`, true),
    ]);
  } else {
    const dataKey = showContributors ? nmKey : allKey;
    chartRef.data.datasets = selectedProjects.map((project) =>
      makeDataset(project, dataKey, project, false),
    );
  }

  chartRef.update();
}

/**
 * Create view-mode checkboxes and wire up events.
 * Runs immediately so the checkboxes appear before project data loads.
 */
function initializeViewToggle() {
  const container = document.getElementById("view-checkboxes");
  if (!container) return;

  const viewOptions = [
    {
      id: "view-all",
      label: "All issues",
      getter: () => showAll,
      setter: (v) => {
        showAll = v;
      },
    },
    {
      id: "view-contributors",
      label: "Only contributor issues",
      getter: () => showContributors,
      setter: (v) => {
        showContributors = v;
      },
    },
  ];

  for (const { id, label, getter, setter } of viewOptions) {
    createCheckboxItem(container, {
      id,
      label,
      checked: getter(),
      onChange: (v) => {
        setter(v);
        updateChart();
        updateAgeChart();
        updateClosedChart();
      },
    });
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
  chart = createLineChart("issues-chart", "Open Issues");
  ageChart = createLineChart("age-chart", "Median Issue Age (days)");
  closedChart = createLineChart(
    "closed-chart",
    "Issues Closed / Week (30-day avg)",
  );
  updateChart();
  updateAgeChart();
  updateClosedChart();
}

function updateChart() {
  updateLineChart(chart, "checkbox", "issues", "nm_issues");
}

function updateAgeChart() {
  updateLineChart(ageChart, "age-checkbox", "age", "nm_age", {
    spanGaps: false,
  });
}

function updateClosedChart() {
  updateLineChart(closedChart, "closed-checkbox", "closed", "nm_closed");
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
