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
const orderedProjects = projects.filter((p) => p in snapshot);

// "all" = all issues/PRs, "nm" = non-maintainer only
let snapshotViewMode = "all";

function makeBarChart(canvasId, labels, datasets, xLabel) {
  const ctx = document.getElementById(canvasId);

  // Chart.js with responsive:true + maintainAspectRatio:false fills its parent
  // container. We need an explicit-height wrapper to prevent a growth feedback loop.
  const wrapper = document.createElement("div");
  wrapper.style.position = "relative";
  wrapper.style.height = `${labels.length * 28 + 60}px`;
  ctx.parentNode.insertBefore(wrapper, ctx);
  wrapper.appendChild(ctx);

  return new Chart(ctx, {
    type: "bar",
    data: { labels, datasets },
    options: {
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
    },
  });
}

const labels = orderedProjects;

/**
 * Build datasets for the open issues/PRs chart based on the current view mode.
 */
function openDatasetsForMode(mode) {
  const issueKey = mode === "nm" ? "nm_open_issues" : "open_issues";
  const prKey = mode === "nm" ? "nm_open_prs" : "open_prs";
  return [
    {
      label: "Open Issues",
      data: orderedProjects.map((p) => snapshot[p][issueKey]),
      backgroundColor: `${ISSUE_COLOR}CC`,
      borderColor: ISSUE_COLOR,
      borderWidth: 1,
    },
    {
      label: "Open PRs",
      data: orderedProjects.map((p) => snapshot[p][prKey]),
      backgroundColor: `${PR_COLOR}CC`,
      borderColor: PR_COLOR,
      borderWidth: 1,
    },
  ];
}

/**
 * Build datasets for the median age chart based on the current view mode.
 */
function ageDatasetsForMode(mode) {
  const issueKey = mode === "nm" ? "nm_median_issue_age" : "median_issue_age";
  const prKey = mode === "nm" ? "nm_median_pr_age" : "median_pr_age";
  return [
    {
      label: "Median Issue Age (days)",
      data: orderedProjects.map((p) => snapshot[p][issueKey]),
      backgroundColor: `${ISSUE_COLOR}CC`,
      borderColor: ISSUE_COLOR,
      borderWidth: 1,
    },
    {
      label: "Median PR Age (days)",
      data: orderedProjects.map((p) => snapshot[p][prKey]),
      backgroundColor: `${PR_COLOR}CC`,
      borderColor: PR_COLOR,
      borderWidth: 1,
    },
  ];
}

/**
 * Build datasets for the closed-in-year chart based on the current view mode.
 */
function closedDatasetsForMode(mode) {
  const issueKey =
    mode === "nm" ? "nm_closed_issues_year" : "closed_issues_year";
  const prKey = mode === "nm" ? "nm_closed_prs_year" : "closed_prs_year";
  return [
    {
      label: "Issues Closed (last year)",
      data: orderedProjects.map((p) => snapshot[p][issueKey]),
      backgroundColor: `${ISSUE_COLOR}CC`,
      borderColor: ISSUE_COLOR,
      borderWidth: 1,
    },
    {
      label: "PRs Closed (last year)",
      data: orderedProjects.map((p) => snapshot[p][prKey]),
      backgroundColor: `${PR_COLOR}CC`,
      borderColor: PR_COLOR,
      borderWidth: 1,
    },
  ];
}

const openChart = makeBarChart(
  "snapshot-open-chart",
  labels,
  openDatasetsForMode("all"),
  "Count",
);

const ageChart = makeBarChart(
  "snapshot-age-chart",
  labels,
  ageDatasetsForMode("all"),
  "Days",
);

const closedChart = makeBarChart(
  "snapshot-closed-chart",
  labels,
  closedDatasetsForMode("all"),
  "Count",
);

// Wire up the snapshot view-mode toggle
for (const radio of document.querySelectorAll(
  'input[name="snapshot-view-mode"]',
)) {
  radio.addEventListener("change", () => {
    snapshotViewMode = radio.value;
    openChart.data.datasets = openDatasetsForMode(snapshotViewMode);
    openChart.update();
    ageChart.data.datasets = ageDatasetsForMode(snapshotViewMode);
    ageChart.update();
    closedChart.data.datasets = closedDatasetsForMode(snapshotViewMode);
    closedChart.update();
  });
}
