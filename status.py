#!/usr/bin/env python3

import sys
import I2C_LCD_driver
from time import *
from datetime import datetime
import subprocess
import netifaces as ni
import threading


class Clock:
    def __init__(self, display, mutex_lock):
        self.thr = None
        self.running = False
        self.display = display
        self.lock = mutex_lock
        self.refresh_rate = 0.1

    def run(self):
        if self.thr is not None:
            if self.thr.isAlive():
                return
        self.running = True
        self.thr = ClockThread(0, 'loop', self)

        self.thr.start()
        # self.thr.join()

    def loop(self):
        while self.running:
            dt = datetime.now().strftime('%b %d  %H:%M:%S')
            dt += chr(20) * (20 - len(dt))
            with self.lock:
                self.display.lcd_display_string(dt, 4)
            sleep(self.refresh_rate)

    def stop(self):
        self.thr.stop()  # stop the thread immediately
        self.running = False  # stop the loop


class ClockThread(threading.Thread):
    def __init__(self, thread_id, name, clock):
        super(ClockThread, self).__init__()
        self.threadID = thread_id
        self.name = name
        self.clock = clock
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        self.clock.loop()


class NIC:

    def __init__(self, display, mutex_lock):
        self.display = display
        self.lock = mutex_lock
        self.eth0_addr = None
        self.wlan0_addr = None

    def _clear_display(self):
        with self.lock:
            self.display.lcd_write(0x01)

    def show_eth0(self):
        self._clear_display()
        with self.lock:
            self.display.lcd_display_string('eth: ' + NIC.get_eth_ip_address(), 1)

    def show_wifi(self):
        self._clear_display()
        status = NIC.get_wifi_status()
        with self.lock:
            self.display.lcd_display_string('wifi:' + NIC.get_wifi_ip_address(), 1)
            if 'ssid' in status:
                self.display.lcd_display_string('SSID:', 2)
                self.display.lcd_display_string(status['ssid'][:19], 3)
            else:
                self.display.lcd_display_string('SSID scan error: not', 2)
                self.display.lcd_display_string('found or bad passwd', 3)

    @staticmethod
    def get_ip_address(iface):
        try:
            ip = ni.ifaddresses(iface)[ni.AF_INET][0]['addr']
            return ip
        except KeyError:
            return 'down'
        except:
            return 'error'

    @staticmethod
    def get_eth_ip_address():
        return NIC.get_ip_address('eth0')

    @staticmethod
    def get_wifi_ip_address():
        return NIC.get_ip_address('wlan0')

    @staticmethod
    def get_wifi_status():
        stdout = subprocess.check_output(['/sbin/wpa_cli', '-i', 'wlan0', 'status'], universal_newlines=True)
        status = {}
        lines = stdout.splitlines()
        for line in lines:
            key, value = line.split('=', 1)
            status[key] = value
        return status


def main(argv):
    display = I2C_LCD_driver.lcd()

    display.lcd_clear()
    mutex_lock = threading.Lock()

    # Run the clock in a separate thread, since it needs to update more
    # often (pretty much every second)
    lcd_clock = Clock(display, mutex_lock)
    lcd_clock.run()

    nic = NIC(display, mutex_lock)

    try:
        while True:
            nic.show_eth0()
            sleep(5)
            nic.show_wifi()
            sleep(5)

    except(KeyboardInterrupt, SystemExit):
        lcd_clock.stop()
        display.lcd_write(0x01)  # Faster and more consistent than lcd_clear()
    finally:
        display.lcd_write(0x01)
        sys.exit


if __name__ == "__main__":
    main(sys.argv)
