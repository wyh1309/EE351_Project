from G60 import GPS
import time


if __name__ == "__main__":
    gps = GPS()
    try:
        while True:
            if gps.GPS_read():
                gps.GPS_show()
    except KeyboardInterrupt:
        gps.stop()