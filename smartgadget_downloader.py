#!/usr/bin/env python3
"""
Marco Eppenberger, 2020
"""

from struct import unpack, pack, iter_unpack
from datetime import datetime, timedelta
from time import time
from threading import Event

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
        self.btadapter = pygatt.GATTToolBackend()

        # threading: wait until all data is downloaded
        self.download_done = Event()
        self.download_done.clear()

        # data storage, newest events are first!
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
        values = [x[0] for x in iter_unpack('f', values_binary)]
        return seq_num, values

    def _retrieve_temperature_log(self, handle, binary_data):
        # print("Rx of {:d} bytes.".format(len(binary_data)))
        seq_num, values = self._unpack_SH3T_logger_data(binary_data=binary_data)
        # print("Received temp log #{:d}: {}".format(seq_num, values))
        self.last_temps.extend(values)
        # signal download done when we don't receive any more values. temperature values get received after humidities
        if len(values) == 0:
            self.download_done.set()

    def _retrieve_humidity_log(self, handle, binary_data):
        # print("Rx of {:d} bytes.".format(len(binary_data)))
        seq_num, values = self._unpack_SH3T_logger_data(binary_data=binary_data)
        # print("Received humid log #{:d}: {}".format(seq_num, values))
        self.last_humids.extend(values)

    def _event_tick(self):

        try:
            self.btadapter.start()
            device = self.btadapter.connect('DA:F0:63:93:BE:97', address_type=BLEAddressType.random, timeout=10)

            # temperature_binary = device.char_read(SHT3X_TEMPERATURE_UUID)
            # humidity_binary = device.char_read(SHT3X_HUMIDITY_UUID)

            # step 0: read currently set logging interval
            logging_interval_ms_uInt32 = device.char_read(LOGGER_INTERVAL_MS_UUID)
            logging_interval_ms = unpack('I', logging_interval_ms_uInt32)[0]

            # step 1: subscribe to value characteristics

            # for this to work, the pygatt module must be hotfixed!! they calculate the handle number wrongly
            # within the subscribe method!
            # in the file pygatt/device.py
            # change the line to:
            #    characteristic_config_handle = value_handle + 2
            #                                                    here was a +1, which is wrong for the smartgadget

            device.subscribe(SHT3X_TEMPERATURE_UUID,
                             callback=self._retrieve_temperature_log,
                             wait_for_response=False)
            device.subscribe(SHT3X_HUMIDITY_UUID,
                             callback=self._retrieve_humidity_log,
                             wait_for_response=False)

            # step 2: write host ms timestamp
            device.char_write(SYNC_TIME_MS_UUID, pack('Q', self._ms_timestamp()))

            # step 3: set oldest timestamp to retrieve
            device.char_write(OLDEST_TIMESTAMP_MS_UUID, pack('Q', self._ms_timestamp() - 600000))  # = 10 min in ms
            # device.char_write(OLDEST_TIMESTAMP_MS_UUID, pack('Q', 0))

            # step 4: trigger download
            device.char_write(START_LOGGER_DOWNLOAD_UUID, pack('B', 1))

            # wait until download is over
            self.download_done.wait(55.0)  # we should be done within 55s

            # step 5: disable upload
            device.char_write(START_LOGGER_DOWNLOAD_UUID, pack('B', 0))

            # step 6: unsubscribe
            # the same logic as described above with changing the pygatt module applies here
            device.unsubscribe(SHT3X_TEMPERATURE_UUID, wait_for_response=False)
            device.unsubscribe(SHT3X_HUMIDITY_UUID, wait_for_response=False)

        finally:
            # print("Finally clause. Stopping bt adaptor.")
            self.btadapter.stop()

        # temperature = unpack('f', temperature_binary)[0]
        # humidity = unpack('f', humidity_binary)[0]

        # create current timestamps, newest value is first!
        timestamp_now = datetime.now()
        timestamps = [timestamp_now - timedelta(milliseconds=x * logging_interval_ms) for x in
                      range(len(self.last_temps))]
        timestamp_strings = ['{date:%Y-%m-%d_%H%M%S}'.format(date=ts) for ts in timestamps]

        if len(self.last_temps) != len(self.last_humids):
            self.lgr.error("Temperatures and humidities lists are not of equal length! Only keeping available pairs!")

        # reverse all lists since we want to log earliest first
        timestamp_strings.reverse()
        self.last_temps.reverse()
        self.last_humids.reverse()

        with open("values_log.txt", 'a') as fp:
            for tss, temp, humid in zip(timestamp_strings, self.last_temps, self.last_humids):
                log_line = "{0:s},{1:.2f},{2:.2f}\n".format(tss, temp, humid)
                fp.write(log_line)

        self.last_temps = []
        self.last_humids = []


if __name__ == '__main__':
    import logging

    logging.basicConfig()
    logging.getLogger('pygatt').setLevel(logging.DEBUG)

    lgr = logging.getLogger()
    downloader = SmartGadgetDownloader(lgr)
    downloader._event_tick()
