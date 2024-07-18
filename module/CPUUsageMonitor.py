import psutil
import threading
from ConfigManager import ConfigManager

class CPUUsageMonitor:
    """
    Monitor CPU usage and adjust the interval based on the usage level.

    监控CPU使用率并根据使用级别调整间隔。

    Args:
        interval (float): The initial interval value.
            初始间隔值。
        lock (threading.Lock): The lock used for thread synchronization.
            用于线程同步的锁。

    Attributes:
        interval_list (list): A list of interval values corresponding to different CPU usage levels.
            不同CPU使用率级别对应的间隔值列表。
        interval (float): The current interval value.
            当前的间隔值。
        lock (threading.Lock): The lock used for thread synchronization.
            用于线程同步的锁。
    """

    def __init__(self, interval, lock):
        self.interval_list = [0.08, 0.1, 0.2, 0.3, 0.4]
        self.interval = interval
        self.lock = lock
        if ConfigManager.get_setting("settings.positive_correlation"):
            self.interval_list.reverse()

    def set_interval(self, value):
        """
        Set the interval value.

        设置间隔值。

        Args:
            value (float): The new interval value.
                新的间隔值.
        """
        with self.lock:
            self.interval[0] = value

    def get_cpu_usage(self):
        """
        Continuously monitor the CPU usage and adjust the interval based on the usage level.

        持续监控CPU使用率并根据使用级别调整间隔。
        """
        while True:
            cpu_usage = psutil.cpu_percent(interval=1)
            if cpu_usage < 10.0:
                self.set_interval(self.interval_list[0])
            elif 10.0 <= cpu_usage < 20.0:
                self.set_interval(self.interval_list[1])
            elif 20.0 <= cpu_usage < 40.0:
                self.set_interval(self.interval_list[2])
            elif 40.0 <= cpu_usage < 60.0:
                self.set_interval(self.interval_list[3])
            elif 60.0 <= cpu_usage < 80.0:
                self.set_interval(self.interval_list[4])

    def start(self):
        """
        Start monitoring the CPU usage in a separate thread.

        在单独的线程中开始监控CPU使用率。
        """
        threading.Thread(target=self.get_cpu_usage, daemon=True).start()
