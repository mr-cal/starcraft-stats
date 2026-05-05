// Color for issues vs PRs in grouped bar charts
const ISSUE_COLOR = "#0066CC";
const PR_COLOR = "#E95420";

const response = await fetch("data/projects.json");
const { applications, libraries, launchpad } = await response.json();
const launchpadProjects = (launchpad ?? []).map((p) => `${p} (launchpad)`);
const projects = [...applications, ...libraries, ...launchpadProjects];

const snapshotResponse = await fetch("data/snapshot.json");
const snapshot = await snapshotResponse.json();

// Projects in display order, filtering out any missing from snapshot
const allProjects = projects.filter((p) => p in snapshot);

// Which data series to display
let showAll = true;
let showContributors = false;

// "All projects" shows an aggregate bar; selectedProjects adds individual bars
let showAllProjectsAggregate = true;
let selectedProjects = [];

/**
 * Return the display items for the charts:
 * - { label: "All projects", isAggregate: true } if the aggregate is enabled
 * - { label: <project>, isAggregate: false } for each individually selected project
 */
function getDisplayItems() {
  const items = [];
  if (showAllProjectsAggregate) items.push({ label: "All projects", isAggregate: true });
  for (const p of allProjects) {
    if (selectedProjects.includes(p)) items.push({ label: p, isAggregate: false });
  }
  return items;
}

/** Sum a snapshot field across all projects (fallback when all-projects not in snapshot). */
function sumAll(key) {
  return allProjects.reduce((total, p) => total + (snapshot[p][key] ?? 0), 0);
}

/** Average a snapshot field across all projects (fallback for median fields). */
function avgAll(key) {
  const vals = allProjects.map((p) => snapshot[p][key]).filter((v) => v != null);
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
}

/**
 * Map display items to data values for a given snapshot key.
 * For the aggregate item, use snapshot["all-projects"] if available (matches the
 * Python-computed aggregate), otherwise fall back to on-the-fly sum/average.
 */
function getValues(items, key, { useAvg = false } = {}) {
  return items.map((item) => {
    if (item.isAggregate) {
      return "all-projects" in snapshot
        ? snapshot["all-projects"][key]
        : useAvg ? avgAll(key) : sumAll(key);
    }
    return snapshot[item.label][key];
  });
}

function makeChartOptions(xLabel) {
  return {
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: "top" },
      tooltip: { mode: "index", intersect: false },
    },
    scales: {
      x: {
        display: true,
        beginAtZero: true,
        title: { display: true, text: xLabel },
        ticks: { precision: 0 },
      },
      y: { display: true },
    },
  };
}

function makeBarChart(canvasId, labels, datasets, xLabel) {
  const ctx = document.getElementById(canvasId);

  const wrapper = document.createElement("div");
  wrapper.style.position = "relative";
  wrapper.style.height = `${Math.max(1, labels.length) * 40 + 80}px`;
  ctx.parentNode.insertBefore(wrapper, ctx);
  wrapper.appendChild(ctx);

  const chart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets },
    options: makeChartOptions(xLabel),
  });

  return { chart, wrapper };
}


/**
 * Build datasets for the open issues/PRs chart based on the current view state.
 */
function openDatasetsForMode(items) {
  const datasets = [];
  if (showAll && showContributors) {
    datasets.push(
      { label: "Open Issues (all)", data: getValues(items, "open_issues"), backgroundColor: `${ISSUE_COLOR}CC`, borderColor: ISSUE_COLOR, borderWidth: 1 },
      { label: "Open Issues (contributors)", data: getValues(items, "nm_open_issues"), backgroundColor: `${ISSUE_COLOR}55`, borderColor: ISSUE_COLOR, borderWidth: 1, borderDash: [4, 4] },
      { label: "Open PRs (all)", data: getValues(items, "open_prs"), backgroundColor: `${PR_COLOR}CC`, borderColor: PR_COLOR, borderWidth: 1 },
      { label: "Open PRs (contributors)", data: getValues(items, "nm_open_prs"), backgroundColor: `${PR_COLOR}55`, borderColor: PR_COLOR, borderWidth: 1, borderDash: [4, 4] },
    );
  } else if (showAll || showContributors) {
    const issueKey = showContributors ? "nm_open_issues" : "open_issues";
    const prKey = showContributors ? "nm_open_prs" : "open_prs";
    datasets.push(
      { label: "Open Issues", data: getValues(items, issueKey), backgroundColor: `${ISSUE_COLOR}CC`, borderColor: ISSUE_COLOR, borderWidth: 1 },
      { label: "Open PRs", data: getValues(items, prKey), backgroundColor: `${PR_COLOR}CC`, borderColor: PR_COLOR, borderWidth: 1 },
    );
  }
  return datasets;
}

/**
 * Build datasets for the median age chart based on the current view state.
 */
function ageDatasetsForMode(items) {
  const datasets = [];
  if (showAll && showContributors) {
    datasets.push(
      { label: "Median Issue Age, days (all)", data: getValues(items, "median_issue_age", { useAvg: true }), backgroundColor: `${ISSUE_COLOR}CC`, borderColor: ISSUE_COLOR, borderWidth: 1 },
      { label: "Median Issue Age, days (contributors)", data: getValues(items, "nm_median_issue_age", { useAvg: true }), backgroundColor: `${ISSUE_COLOR}55`, borderColor: ISSUE_COLOR, borderWidth: 1, borderDash: [4, 4] },
      { label: "Median PR Age, days (all)", data: getValues(items, "median_pr_age", { useAvg: true }), backgroundColor: `${PR_COLOR}CC`, borderColor: PR_COLOR, borderWidth: 1 },
      { label: "Median PR Age, days (contributors)", data: getValues(items, "nm_median_pr_age", { useAvg: true }), backgroundColor: `${PR_COLOR}55`, borderColor: PR_COLOR, borderWidth: 1, borderDash: [4, 4] },
    );
  } else if (showAll || showContributors) {
    const issueKey = showContributors ? "nm_median_issue_age" : "median_issue_age";
    const prKey = showContributors ? "nm_median_pr_age" : "median_pr_age";
    datasets.push(
      { label: "Median Issue Age (days)", data: getValues(items, issueKey, { useAvg: true }), backgroundColor: `${ISSUE_COLOR}CC`, borderColor: ISSUE_COLOR, borderWidth: 1 },
      { label: "Median PR Age (days)", data: getValues(items, prKey, { useAvg: true }), backgroundColor: `${PR_COLOR}CC`, borderColor: PR_COLOR, borderWidth: 1 },
    );
  }
  return datasets;
}

/**
 * Build datasets for the closed-in-year chart based on the current view state.
 */
function closedDatasetsForMode(items) {
  const datasets = [];
  if (showAll && showContributors) {
    datasets.push(
      { label: "Issues Closed, last year (all)", data: getValues(items, "closed_issues_year"), backgroundColor: `${ISSUE_COLOR}CC`, borderColor: ISSUE_COLOR, borderWidth: 1 },
      { label: "Issues Closed, last year (contributors)", data: getValues(items, "nm_closed_issues_year"), backgroundColor: `${ISSUE_COLOR}55`, borderColor: ISSUE_COLOR, borderWidth: 1, borderDash: [4, 4] },
      { label: "PRs Closed, last year (all)", data: getValues(items, "closed_prs_year"), backgroundColor: `${PR_COLOR}CC`, borderColor: PR_COLOR, borderWidth: 1 },
      { label: "PRs Closed, last year (contributors)", data: getValues(items, "nm_closed_prs_year"), backgroundColor: `${PR_COLOR}55`, borderColor: PR_COLOR, borderWidth: 1, borderDash: [4, 4] },
    );
  } else if (showAll || showContributors) {
    const issueKey = showContributors ? "nm_closed_issues_year" : "closed_issues_year";
    const prKey = showContributors ? "nm_closed_prs_year" : "closed_prs_year";
    datasets.push(
      { label: "Issues Closed (last year)", data: getValues(items, issueKey), backgroundColor: `${ISSUE_COLOR}CC`, borderColor: ISSUE_COLOR, borderWidth: 1 },
      { label: "PRs Closed (last year)", data: getValues(items, prKey), backgroundColor: `${PR_COLOR}CC`, borderColor: PR_COLOR, borderWidth: 1 },
    );
  }
  return datasets;
}

/**
 * Update all three snapshot charts to reflect the current view and project selection.
 */
function updateSnapshotCharts() {
  const items = getDisplayItems();
  const labels = items.map((i) => i.label);
  const height = `${Math.max(1, labels.length) * 40 + 80}px`;

  openChart.destroy();
  openWrapper.style.height = height;
  openChart = new Chart(document.getElementById("snapshot-open-chart"), {
    type: "bar",
    data: { labels, datasets: openDatasetsForMode(items) },
    options: makeChartOptions("Count"),
  });

  ageChart.destroy();
  ageWrapper.style.height = height;
  ageChart = new Chart(document.getElementById("snapshot-age-chart"), {
    type: "bar",
    data: { labels, datasets: ageDatasetsForMode(items) },
    options: makeChartOptions("Days"),
  });

  closedChart.destroy();
  closedWrapper.style.height = height;
  closedChart = new Chart(document.getElementById("snapshot-closed-chart"), {
    type: "bar",
    data: { labels, datasets: closedDatasetsForMode(items) },
    options: makeChartOptions("Count"),
  });
}

/**
 * Create a simple styled checkbox item appended to container.
 */
function createCheckboxItem(container, { id, label, checked, onChange }) {
  const labelEl = document.createElement("label");
  labelEl.htmlFor = id;
  labelEl.style.cssText = "display:flex;align-items:center;gap:0.5rem;cursor:pointer;margin-bottom:0.4rem;";

  const input = document.createElement("input");
  input.type = "checkbox";
  input.id = id;
  input.checked = checked;
  input.addEventListener("change", () => onChange(input.checked));

  labelEl.appendChild(input);
  labelEl.appendChild(document.createTextNode(label));
  container.appendChild(labelEl);
}

/**
 * Create the view-mode checkboxes (All issues / Only contributor issues) via JS.
 */
function createSnapshotViewCheckboxes() {
  const container = document.getElementById("snapshot-view-checkboxes");
  if (!container) return;

  createCheckboxItem(container, {
    id: "snapshot-view-all",
    label: "All issues",
    checked: showAll,
    onChange: (v) => { showAll = v; updateSnapshotCharts(); },
  });
  createCheckboxItem(container, {
    id: "snapshot-view-contributors",
    label: "Only contributor issues",
    checked: showContributors,
    onChange: (v) => { showContributors = v; updateSnapshotCharts(); },
  });
}

/**
 * Create project checkboxes for the snapshot section.
 * "All projects" (checked by default) shows an aggregate bar of all projects.
 * Individual project checkboxes add that project as a separate bar.
 */
function createSnapshotCheckboxes() {
  const container = document.getElementById("snapshot-checkboxes");
  if (!container) return;

  createCheckboxItem(container, {
    id: "snapshot-checkbox-all-projects",
    label: "All projects",
    checked: true,
    onChange: (v) => { showAllProjectsAggregate = v; updateSnapshotCharts(); },
  });

  for (const project of allProjects) {
    createCheckboxItem(container, {
      id: `snapshot-checkbox-${project}`,
      label: project,
      checked: false,
      onChange: (checked) => {
        if (checked) {
          selectedProjects.push(project);
          selectedProjects = allProjects.filter((p) => selectedProjects.includes(p));
        } else {
          selectedProjects = selectedProjects.filter((p) => p !== project);
        }
        updateSnapshotCharts();
      },
    });
  }
}

const initialItems = getDisplayItems();
const initialLabels = initialItems.map((i) => i.label);

let openChart;
let ageChart;
let closedChart;

const { chart: openChartInit, wrapper: openWrapper } = makeBarChart(
  "snapshot-open-chart",
  initialLabels,
  openDatasetsForMode(initialItems),
  "Count",
);
openChart = openChartInit;

const { chart: ageChartInit, wrapper: ageWrapper } = makeBarChart(
  "snapshot-age-chart",
  initialLabels,
  ageDatasetsForMode(initialItems),
  "Days",
);
ageChart = ageChartInit;

const { chart: closedChartInit, wrapper: closedWrapper } = makeBarChart(
  "snapshot-closed-chart",
  initialLabels,
  closedDatasetsForMode(initialItems),
  "Count",
);
closedChart = closedChartInit;

createSnapshotViewCheckboxes();
createSnapshotCheckboxes();
