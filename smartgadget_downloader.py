#!/usr/bin/env python3
"""
Marco Eppenberger, 2020
"""

from struct import unpack, pack
from datetime import datetime
from time import time, sleep

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

import pygatt
from pygatt.backends import BLEAddressType

from smartgadget_bt_constants import *


class SmartGadgetDownloader(object):

    def __init__(self, logger):

        # get logger
        self.lgr = logger

        # specify scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._event_tick, 'cron', minute='*/1', second='10')

        # add error listener for logging
        self.scheduler.add_listener(self._on_job_error, mask=EVENT_JOB_ERROR)

        # gatttool
        self.btadapter = pygatt.GATTToolBackend(search_window_size=2048)

        # data storage
        self.last_temps = []
        self.last_humids = []

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

    def _ms_timestamp(self):
        return int(round(time() * 1000))

    def _unpack_SH3T_logger_data(self, binary_data):
        seq_num_binary = binary_data[0:4]
        seq_num = unpack('I', seq_num_binary)[0]
        values_binary = binary_data[4:]
        values = unpack('f', values_binary)
        return seq_num, values

    def _retrieve_temperature_log(self, handle, binary_data):
        print("Rx of {:d} bytes.".format(len(binary_data)))
        seq_num, values = self._unpack_SH3T_logger_data(binary_data=binary_data)
        print("Received temp log #{:d}: {}".format(seq_num, values))
        self.last_temps.extend(values)

    def _retrieve_humidity_log(self, handle, binary_data):
        print("Rx of {:d} bytes.".format(len(binary_data)))
        seq_num, values = self._unpack_SH3T_logger_data(binary_data=binary_data)
        print("Received humid log #{:d}: {}".format(seq_num, values))
        self.last_humids.extend(values)

    def _event_tick(self):

        try:
            self.btadapter.start()
            device = self.btadapter.connect('DA:F0:63:93:BE:97', address_type=BLEAddressType.random, timeout=10)

            device.bond()

            # temperature_binary = device.char_read(SHT3X_TEMPERATURE_UUID)
            # humidity_binary = device.char_read(SHT3X_HUMIDITY_UUID)

            # step 1: subscribe to value characteristics
            device.subscribe(SHT3X_TEMPERATURE_UUID,
                             callback=self._retrieve_temperature_log,
                             wait_for_response=False,
                             indication=True)
            device.subscribe(SHT3X_HUMIDITY_UUID,
                             callback=self._retrieve_humidity_log,
                             wait_for_response=False,
                             indication=True)

            # step 2: write host ms timestamp
            device.char_write(SYNC_TIME_MS_UUID, pack('Q', self._ms_timestamp()))

            # step 3: set oldest timestamp to retrieve
            device.char_write(OLDEST_TIMESTAMP_MS_UUID, pack('Q', self._ms_timestamp() - 60000))  # = 1 min in ms

            # step 4: trigger download
            device.char_write(START_LOGGER_DOWNLOAD_UUID, pack('B', 1))

            # wait until download is over
            sleep(10)

            # step 5: unsub
            device.unsubscribe(SHT3X_TEMPERATURE_UUID, wait_for_response=False)
            device.unsubscribe(SHT3X_HUMIDITY_UUID, wait_for_response=False)

        finally:
            self.btadapter.stop()

        # temperature = unpack('f', temperature_binary)[0]
        # humidity = unpack('f', humidity_binary)[0]

        timestamp = str('{date:%Y-%m-%d_%H%M%S}'.format(date=datetime.now()))

        with open("values_log.txt", 'a') as fp:
            for temp, humid in zip(self.last_temps, self.last_humids):
                log_line = "{0:s},{1:.2f},{2:.2f}\n".format(timestamp, temp, humid)
                fp.write(log_line)

        self.last_temps = []
        self.last_humids = []


if __name__ == '__main__':
    import logging

    lgr = logging.getLogger()
    downloader = SmartGadgetDownloader(lgr)
    downloader._event_tick()
