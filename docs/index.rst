.. Python SwitchBot BLE documentation master file, created by
   sphinx-quickstart on Thu Apr 27 02:11:22 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python SwitchBot BLE
=====================

A Bluetooth Low Energy API for interacting with SwitchBot devices!


* Free software: GPL v3.0
* Documentation: https://python-switchbot-ble.readthedocs.io


SwitchBot BLE is a reverse engineered API for communicating with SwitchBot devices without a Hub.

Features
--------

* Supports all platforms supported by `bleak <https://bleak.readthedocs.io>`_.
    - Supports Windows 10, version 16299 (Fall Creators Update) or greater
    - Supports Linux distributions with BlueZ >= 5.43
    - OS X/macOS support via Core Bluetooth API, from at least OS X version 10.11
* Ability to control SwitchBot protected by a "password"
* Well tested on the SwitchBot Bot, but has the infrastructure to support other SwitchBot devices

Bleak supports reading, writing and getting notifications from
GATT servers, as well as a function for discovering BLE devices.

.. toctree::
   :maxdepth: 2

   installation
   usage-repl
   usage-dev
   api/index
   contributing



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
