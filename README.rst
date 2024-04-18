craft-stats
###########

|test-status-badge| |data-collection-badge|

Overview
========

Dashboard, insights, and statistics for the \*craft applications and libraries.

https://mr-cal.github.io/starcraft-stats/html/index.html

Design
======

This project contains a few parts:

* A Python command-line application that retrieves, processes, and stores data
  in a CSV file.
* A static webpage that loads and displays the CSV data as tables and charts.
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

You will need a github token. You can create a new fine-grained
token here in your `settings page`_.

.. code-block::

    export GITHUB_TOKEN=<your token from github>
    pip install -e .
    starcraft-stats --help

TODO
====

☐ track if releases are up-to-date
(how many commits have happen since a branch's last tag?)


Contributing
============

Contributions are encouraged!



.. |test-status-badge| image:: https://github.com/mr-cal/starcraft-stats/actions/workflows/tests.yaml/badge.svg?branch=main
.. _test-status-badge: https://github.com/mr-cal/starcraft-stats/actions/workflows/tests.yaml
.. |data-collection-badge| image:: https://github.com/mr-cal/starcraft-stats/actions/workflows/data-collection.yaml/badge.svg?branch=main
.. _data-collection-badge: https://github.com/mr-cal/starcraft-stats/actions/workflows/data-collection.yaml
.. _settings page: https://github.com/settings/tokens?type=beta
