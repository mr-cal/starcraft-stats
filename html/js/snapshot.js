// Color for issues vs PRs in grouped bar charts
const ISSUE_COLOR = "#0066CC";
const PR_COLOR = "#E95420";

const BAR_HEIGHT_PX = 28;
const CHART_BASE_HEIGHT_PX = 80;

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
  if (showAllProjectsAggregate)
    items.push({ label: "All projects", isAggregate: true });
  for (const p of allProjects) {
    if (selectedProjects.includes(p))
      items.push({ label: p, isAggregate: false });
  }
  return items;
}

/** Sum a snapshot field across all projects (fallback when all-projects not in snapshot). */
function sumAll(key) {
  return allProjects.reduce((total, p) => total + (snapshot[p][key] ?? 0), 0);
}

/** Average a snapshot field across all projects (fallback for median fields). */
function avgAll(key) {
  const vals = allProjects
    .map((p) => snapshot[p][key])
    .filter((v) => v != null);
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
        : useAvg
          ? avgAll(key)
          : sumAll(key);
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
  wrapper.style.height = `${Math.max(1, labels.length) * Math.max(1, datasets.length) * BAR_HEIGHT_PX + CHART_BASE_HEIGHT_PX}px`;
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
 * Generic dataset builder for a bar chart that shows issue and PR metrics.
 *
 * In "both" mode (showAll && showContributors), four datasets are emitted:
 * all-issues, contributors-issues, all-PRs, contributors-PRs.
 * In single mode, two datasets are emitted using the active key set.
 *
 * @param {Array}  items        - Display items from getDisplayItems().
 * @param {object} keys         - { allIssue, nmIssue, allPr, nmPr } snapshot keys.
 * @param {object} labels       - { issue, pr } human-readable label strings.
 * @param {boolean} useAvg      - Pass true for median-age fields to use avgAll fallback.
 */
function makeDatasetsForMode(
  items,
  {
    allIssueKey,
    nmIssueKey,
    allPrKey,
    nmPrKey,
    issueLabel,
    prLabel,
    useAvg = false,
  },
) {
  const vals = (key) => getValues(items, key, { useAvg });
  if (showAll && showContributors) {
    return [
      {
        label: `${issueLabel} (all)`,
        data: vals(allIssueKey),
        backgroundColor: `${ISSUE_COLOR}CC`,
        borderColor: ISSUE_COLOR,
        borderWidth: 1,
      },
      {
        label: `${issueLabel} (contributors)`,
        data: vals(nmIssueKey),
        backgroundColor: `${ISSUE_COLOR}55`,
        borderColor: ISSUE_COLOR,
        borderWidth: 1,
        borderDash: [4, 4],
      },
      {
        label: `${prLabel} (all)`,
        data: vals(allPrKey),
        backgroundColor: `${PR_COLOR}CC`,
        borderColor: PR_COLOR,
        borderWidth: 1,
      },
      {
        label: `${prLabel} (contributors)`,
        data: vals(nmPrKey),
        backgroundColor: `${PR_COLOR}55`,
        borderColor: PR_COLOR,
        borderWidth: 1,
        borderDash: [4, 4],
      },
    ];
  }
  if (showAll || showContributors) {
    return [
      {
        label: issueLabel,
        data: vals(showContributors ? nmIssueKey : allIssueKey),
        backgroundColor: `${ISSUE_COLOR}CC`,
        borderColor: ISSUE_COLOR,
        borderWidth: 1,
      },
      {
        label: prLabel,
        data: vals(showContributors ? nmPrKey : allPrKey),
        backgroundColor: `${PR_COLOR}CC`,
        borderColor: PR_COLOR,
        borderWidth: 1,
      },
    ];
  }
  return [];
}

function openDatasetsForMode(items) {
  return makeDatasetsForMode(items, {
    allIssueKey: "open_issues",
    nmIssueKey: "nm_open_issues",
    allPrKey: "open_prs",
    nmPrKey: "nm_open_prs",
    issueLabel: "Open Issues",
    prLabel: "Open PRs",
  });
}

function ageDatasetsForMode(items) {
  return makeDatasetsForMode(items, {
    allIssueKey: "median_issue_age",
    nmIssueKey: "nm_median_issue_age",
    allPrKey: "median_pr_age",
    nmPrKey: "nm_median_pr_age",
    issueLabel: "Median Issue Age (days)",
    prLabel: "Median PR Age (days)",
    useAvg: true,
  });
}

function closedDatasetsForMode(items) {
  return makeDatasetsForMode(items, {
    allIssueKey: "closed_issues_year",
    nmIssueKey: "nm_closed_issues_year",
    allPrKey: "closed_prs_year",
    nmPrKey: "nm_closed_prs_year",
    issueLabel: "Issues Closed (last year)",
    prLabel: "PRs Closed (last year)",
  });
}

/**
 * Update all three snapshot charts to reflect the current view and project selection.
 */
function updateSnapshotCharts() {
  const items = getDisplayItems();
  const labels = items.map((i) => i.label);

  const openDatasets = openDatasetsForMode(items);
  const ageDatasets = ageDatasetsForMode(items);
  const closedDatasets = closedDatasetsForMode(items);

  function chartHeight(datasets) {
    return `${Math.max(1, labels.length) * Math.max(1, datasets.length) * BAR_HEIGHT_PX + CHART_BASE_HEIGHT_PX}px`;
  }

  openChart.destroy();
  openWrapper.style.height = chartHeight(openDatasets);
  openChart = new Chart(document.getElementById("snapshot-open-chart"), {
    type: "bar",
    data: { labels, datasets: openDatasets },
    options: makeChartOptions("Count"),
  });

  ageChart.destroy();
  ageWrapper.style.height = chartHeight(ageDatasets);
  ageChart = new Chart(document.getElementById("snapshot-age-chart"), {
    type: "bar",
    data: { labels, datasets: ageDatasets },
    options: makeChartOptions("Days"),
  });

  closedChart.destroy();
  closedWrapper.style.height = chartHeight(closedDatasets);
  closedChart = new Chart(document.getElementById("snapshot-closed-chart"), {
    type: "bar",
    data: { labels, datasets: closedDatasets },
    options: makeChartOptions("Count"),
  });
}

/**
 * Create a simple styled checkbox item appended to container.
 */
function createCheckboxItem(container, { id, label, checked, onChange }) {
  const labelEl = document.createElement("label");
  labelEl.htmlFor = id;
  labelEl.style.cssText =
    "display:flex;align-items:center;gap:0.5rem;cursor:pointer;margin-bottom:0.4rem;";

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
    onChange: (v) => {
      showAll = v;
      updateSnapshotCharts();
    },
  });
  createCheckboxItem(container, {
    id: "snapshot-view-contributors",
    label: "Only contributor issues",
    checked: showContributors,
    onChange: (v) => {
      showContributors = v;
      updateSnapshotCharts();
    },
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
    onChange: (v) => {
      showAllProjectsAggregate = v;
      updateSnapshotCharts();
    },
  });

  for (const project of allProjects) {
    createCheckboxItem(container, {
      id: `snapshot-checkbox-${project}`,
      label: project,
      checked: false,
      onChange: (checked) => {
        if (checked) {
          selectedProjects.push(project);
          selectedProjects = allProjects.filter((p) =>
            selectedProjects.includes(p),
          );
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
