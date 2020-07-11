#!/usr/bin/env python3
"""
Marco Eppenberger, 2020
"""

from struct import unpack
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

import pygatt
from pygatt.backends import BLEAddressType


class SmartGadgetDownlaoder(object):

    def __init__(self, logger):

        # get logger
        self.lgr = logger

        # specify scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._event_tick, 'cron', minute='*/1', second='10')

        # add error listener for logging
        self.scheduler.add_listener(self._on_job_error, mask=EVENT_JOB_ERROR)

        # gatttool
        self.btadapter = pygatt.GATTToolBackend()

    def start(self):
        self.scheduler.start()
        self.lgr.info("Scheduler started.")

    def stop(self):
        self.scheduler.shutdown()
        self.lgr.info("Scheduler shut down.")

    def _on_job_error(self, event):
        print("Job Errored:")
        print("-> " + str(event.exception))
        self.lgr.error("Job Errored:")
        self.lgr.error(str(event.exception))
        self.lgr.error("Traceback: " + str(event.traceback))

    def _event_tick(self):

        try:
            self.btadapter.start()
            device = self.btadapter.connect('DA:F0:63:93:BE:97', address_type=BLEAddressType.random)
            temperature_binary = device.char_read("00002235-b38d-4985-720e-0f993a68ee41")
            humidity_binary = device.char_read("00001235-b38d-4985-720e-0f993a68ee41")
        finally:
            self.btadapter.stop()

        temperature = unpack('f', temperature_binary)
        humidity = unpack('f', humidity_binary)
        timestamp = datetime.now().isoformat()

        log_line = "{timestamp:s},{temperature:.2f},{humidity:.2f}\n".format(
            timestamp=timestamp,
            temperature=temperature,
            humidity=humidity
        )

        with open("smartgadget_log.txt", 'a') as fp:
            fp.write(log_line)
