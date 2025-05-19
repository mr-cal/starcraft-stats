craft-stats
###########

|test-status-badge| |fast-data-collection-badge| |slow-data-collection-badge|

Overview
========

Dashboard, insights, and statistics for the \*craft applications and libraries.

https://mr-cal.github.io/starcraft-stats/html/index.html

Design
======

This project contains a few parts:

* A Python command-line application that retrieves, processes, and stores data
  in a set of CSV and JSON files.
* A static webpage that loads and displays the JSON as tables and CSV as graphs.
* A nightly cron job to refresh data

How to
======

How to update data
^^^^^^^^^^^^^^^^^^

Data is updated once a day, but you can manually trigger the
``data-collection`` workflow in GitHub.

How to update what data is collected
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Update the ``starcraft-config.yaml`` file.

How to run locally
^^^^^^^^^^^^^^^^^^

It's a Python package with a CLI, so it can be installed and run locally.

You will need a `fine-grained github token`_ with no extra permissions, just
read-only access to public repositories.

.. code-block::

    export GITHUB_TOKEN=<your token from github>
    uv tool install -e .
    starcraft-stats --help

Web browsers will not run Javascript from a local webpage.
The easiest way to view the webpage locally is to use Python:

.. code-block::

    cd html
    python3 -m http.server 8000
    open http://127.0.0.1:8000

Contributing
============

Contributions are encouraged!

.. |test-status-badge| image:: https://github.com/mr-cal/starcraft-stats/actions/workflows/qa.yaml/badge.svg?branch=main
.. _test-status-badge: https://github.com/mr-cal/starcraft-stats/actions/workflows/qa.yaml
.. |fast-data-collection-badge| image:: https://github.com/mr-cal/starcraft-stats/actions/workflows/fast-data-collection.yaml/badge.svg?branch=main
.. _fast-data-collection-badge: https://github.com/mr-cal/starcraft-stats/actions/workflows/fast-data-collection.yaml
.. |slow-data-collection-badge| image:: https://github.com/mr-cal/starcraft-stats/actions/workflows/slow-data-collection.yaml/badge.svg?branch=main
.. _slow-data-collection-badge: https://github.com/mr-cal/starcraft-stats/actions/workflows/slow-data-collection.yaml
.. _fine-grained github token: https://github.com/settings/tokens?type=beta
