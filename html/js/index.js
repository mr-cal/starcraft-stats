import { chartData } from "./util.js";

async function getData(url) {
    const response = await fetch(url);
    return response.json();
}

/* Graph the dependencies */

var deps = await getData("./data/app-deps.json");
var apps = Object.keys(deps.apps);

console.log(deps);

// First row is the header
// Replace the first "/" with a line break (i.e. 'charmcraft/hotfix/3.2' -> 'charmcraft<br>hotfix/3.2')
var deps_data = [["Library"].concat(apps.map((app) => app.replace("/", "<br>")))];
// Create empty rows for each library
for (var i = 0; i < deps.libs.length; i++) {
    var row = Array(apps.length + 2).fill("");
    console.log(row);
    deps_data.push(row);
}

// Populate table
for (var i = 0; i < deps.libs.length; i++) {
    var lib = deps.libs[i];
    deps_data[i + 1][0] = lib;
    for (var j = 0; j < apps.length; j++) {
        var app = apps[j];
        if (app in deps.apps && lib in deps.apps[app]) {
            var dep_lib = deps.apps[app][lib];
            var v = dep_lib.version;
            if (dep_lib.outdated) {
                v = "!" + v + "<br>(" + dep_lib.latest + ")";
            }
            deps_data[i + 1][j + 1] = v;
        } else {
            deps_data[i + 1][j + 1] = "not used";
        }
    }
}

chartData(deps_data, "libs-and-apps-table");
