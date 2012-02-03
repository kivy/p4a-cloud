P4A Build Cloud
===============

This project is aimed to provide a build cloud architecture for submitting
python application to convert to APK.

.. warning::

    Development version, use with care.

How it's working
----------------

The project is composed of:

- master: serve the webpage, got an API for job submission, and read builder
  logs
- slave: a builder that read a job, do it, and post the result back to master
- p4a-build: command line tool for submitting a job


Master and slave are communicating with `hotqueue
<https://github.com/richardhenry/hotqueue>`_: a queue message based on `Redis
<http://redis.io>`_.

Master needs: flask, requests, sqlalchemy, wtforms, hotqueue
Slave needs: hotqueue, requests
p4a-build needs: requests

