import time
import pystray
import threading
from PIL import Image

class TrayIconManager:
    def __init__(self, images, interval, lock):
        """
        初始化TrayIconManager类的实例。

        Args:
            images (list): 图标图片的列表。
            interval (list): 图标切换的时间间隔列表。
            lock (threading.Lock): 线程锁对象。
        """
        self.images = images
        self.interval = interval
        self.lock = lock
        self.icon = pystray.Icon("RunCat", icon=self.images[0])

    def update_icon(self):
        """
        更新系统托盘图标。

        图标会按照设定的时间间隔切换显示。

        Returns:
            None
        """
        index = 0
        while True:
            with self.lock:
                current_interval = self.interval[0]
            self.icon.icon = self.images[index]
            index = (index + 1) % len(self.images)
            time.sleep(current_interval)

    def run(self):
        """
        启动图标更新线程和系统托盘图标。

        Returns:
            None
        """
        threading.Thread(target=self.update_icon, daemon=True).start()
        self.icon.run()

    def stop(self):
        """
        停止系统托盘图标的更新。

        Returns:
            None
        """
        self.icon.stop()
