// Color for issues vs PRs in grouped bar charts
const ISSUE_COLOR = "#0066CC";
const PR_COLOR = "#E95420";

const response = await fetch("data/projects.json");
const { applications, libraries } = await response.json();
const projects = [...applications, ...libraries];

const snapshotResponse = await fetch("data/snapshot.json");
const snapshot = await snapshotResponse.json();

// Projects in display order, filtering out any missing from snapshot
const orderedProjects = projects.filter((p) => p in snapshot);

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

makeBarChart(
  "snapshot-open-chart",
  labels,
  [
    {
      label: "Open Issues",
      data: orderedProjects.map((p) => snapshot[p].open_issues),
      backgroundColor: `${ISSUE_COLOR}CC`,
      borderColor: ISSUE_COLOR,
      borderWidth: 1,
    },
    {
      label: "Open PRs",
      data: orderedProjects.map((p) => snapshot[p].open_prs),
      backgroundColor: `${PR_COLOR}CC`,
      borderColor: PR_COLOR,
      borderWidth: 1,
    },
  ],
  "Count",
);

makeBarChart(
  "snapshot-age-chart",
  labels,
  [
    {
      label: "Median Issue Age (days)",
      data: orderedProjects.map((p) => snapshot[p].median_issue_age),
      backgroundColor: `${ISSUE_COLOR}CC`,
      borderColor: ISSUE_COLOR,
      borderWidth: 1,
    },
    {
      label: "Median PR Age (days)",
      data: orderedProjects.map((p) => snapshot[p].median_pr_age),
      backgroundColor: `${PR_COLOR}CC`,
      borderColor: PR_COLOR,
      borderWidth: 1,
    },
  ],
  "Days",
);

makeBarChart(
  "snapshot-closed-chart",
  labels,
  [
    {
      label: "Issues Closed (last year)",
      data: orderedProjects.map((p) => snapshot[p].closed_issues_year),
      backgroundColor: `${ISSUE_COLOR}CC`,
      borderColor: ISSUE_COLOR,
      borderWidth: 1,
    },
    {
      label: "PRs Closed (last year)",
      data: orderedProjects.map((p) => snapshot[p].closed_prs_year),
      backgroundColor: `${PR_COLOR}CC`,
      borderColor: PR_COLOR,
      borderWidth: 1,
    },
  ],
  "Count",
);
