# craft-stats

[![Test Status](https://github.com/mr-cal/starcraft-stats/actions/workflows/qa.yaml/badge.svg?branch=main)](https://github.com/mr-cal/starcraft-stats/actions/workflows/qa.yaml)
[![Fast Data Collection](https://github.com/mr-cal/starcraft-stats/actions/workflows/fast-data-collection.yaml/badge.svg?branch=main)](https://github.com/mr-cal/starcraft-stats/actions/workflows/fast-data-collection.yaml)
[![Slow Data Collection](https://github.com/mr-cal/starcraft-stats/actions/workflows/slow-data-collection.yaml/badge.svg?branch=main)](https://github.com/mr-cal/starcraft-stats/actions/workflows/slow-data-collection.yaml)

## Overview

Dashboard, insights, and statistics for the \*craft applications and libraries.

https://mr-cal.github.io/starcraft-stats/html/index.html

## Design

This project contains a few parts:

- A Python command-line application that retrieves, processes, and stores data
  in a set of CSV and JSON files.
- A static webpage that loads and displays the JSON as tables and CSV as graphs.
- A nightly cron job to refresh data.

## How to

### How to update data

Data is updated once a day, but you can manually trigger the
`data-collection` workflow in GitHub.

### How to update what data is collected

Update the `starcraft-config.yaml` file.

### How to run locally

It's a Python package with a CLI, so it can be installed and run locally.

You will need a [fine-grained GitHub token](https://github.com/settings/tokens?type=beta) with no extra permissions, just read-only access to public repositories.

```bash
export GITHUB_TOKEN=<your token from github>
uv tool install -e .
starcraft-stats --help
```

Web browsers will not run Javascript from a local webpage.
The easiest way to view the webpage locally is to use Python:

.. code-block::

```bash
cd html
python3 -m http.server 8000
open http://127.0.0.1:8000
```
