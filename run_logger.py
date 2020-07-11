#!/usr/bin/env python3
"""
Marco Eppenberger, 2020
"""

# python package imports
import logging
import sys
import traceback

from smartgadget_downloader import SmartGadgetDownlaoder

if __name__ == "__main__":

    lgr = logging.getLogger()

    # start gui application
    downloader = SmartGadgetDownlaoder(lgr)
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
