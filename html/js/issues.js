import { chartData, graphIssues } from "./util.js";

// TODO: these should be loaded from a CSV (which needs to be created)
let projects = [
    "charmcraft",
    "rockcraft",
    "snapcraft",
    "craft-application",
    "craft-archives",
    "craft-cli",
    "craft-grammar",
    "craft-parts",
    "craft-providers",
    "craft-platforms",
    "craft-store",
    "starbase",
];

/* Chart the "all-projects" project first */
Papa.parse(`data/all-projects-github.csv`, {
    download: true,
    dynamicTyping: true,
    header: true,
    complete: function (data) {
        graphIssues("all-projects", data.data, "issues");
    },
});

/**
 * Chart the rest of the projects.
 * `forEach` loops are async, so the order is not guaranteed.
 * After they are loaded and cached, refreshing the page will probably
 * result in the "correct" order.
 */
projects.reverse().forEach(function (project) {
    Papa.parse(`data/${project}-github.csv`, {
        download: true,
        dynamicTyping: true,
        header: true,
        complete: function (data) {
            graphIssues(project, data.data, "all-projects-chart-div");
        },
    });
});
