#!/usr/bin/env python3
"""
Marco Eppenberger, 2020
"""

# python package imports
import logging
import sys
import traceback

from smartgadget_downloader import SmartGadgetDownloader


def init_logging():

    lgr = logging.getLogger()

    lgr.setLevel(logging.INFO)
    logging.getLogger('pygatt').setLevel(logging.WARNING)

    # clear all existing handlers
    hlist = list(lgr.handlers)
    for h in hlist:
        h.close()
        lgr.removeHandler(h)

    handler = logging.handlers.RotatingFileHandler('./smartgadget_downloader.log', maxBytes=20000000, backupCount=10)
    formatter = logging.Formatter(fmt="{asctime} [{levelname:8s}]: {module}.{funcName}() {message}", style="{")
    handler.setFormatter(formatter)
    lgr.addHandler(handler)

    return lgr


if __name__ == "__main__":

    lgr = init_logging()

    # start gui application
    downloader = SmartGadgetDownloader(lgr)
    try:
        downloader.start()
        print("EventPlayer Started. Press Ctrl+C to quit.")
        while True:
            input()
    except KeyboardInterrupt as e:  # Ctrl-C
        lgr.debug("exiting (KeyboardInterrupt)")
        downloader.stop()
        print("\nexiting ...")
        sys.exit(0)
    except SystemExit as e:  # sys.exit()
        lgr.debug("exiting (SystemExit)")
        downloader.stop()
        print("exiting ...")
        raise e
    except Exception as e:
        lgr.critical(traceback.format_exc())
        print('ERROR, UNEXPECTED EXCEPTION:')
        print(str(e))
        raise e
