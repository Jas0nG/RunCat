#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   TianchenWu, XueWeiHan
#   Date    :   2024-08-15 20:01
#   Desc    :   RunCat
from enum import Enum
import time
import pystray
import psutil
import threading
import json
from pathlib import Path
from PIL import Image
from pystray import MenuItem as Item, Menu
import webbrowser
import sys
import logging
import logging.handlers
from typing import List, Dict
from contextlib import contextmanager
import gc


class MonitorMode(Enum):
    CPU = "CPU"
    MEMORY = "Memory"
    NETWORK = "Network"


class Config:
    def __init__(self):
        self.dark_mode: bool = False
        self.speed: List[float] = [1.0]
        self.config_dir: Path = Path.home() / '.runcat'
        self.config_path: Path = self.config_dir / 'config.json'
        self.icon_images: List[Image.Image] = []
        self.update_interval: List[float] = [1.0]
        self.config_lock = threading.Lock()
        self.speed_labels: Dict[float, str] = {1.5: "Slow", 1.0: "Medium", 0.5: "Fast"}
        self.running = threading.Event()
        self._image_refs = []

        # 内存监控阈值 (MB)
        self.memory_threshold = 100

        self.monitor_mode = MonitorMode.CPU
        self.last_net_io = psutil.net_io_counters()
        self.last_io_time = time.time()

        # 创建配置目录
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def cleanup(self):
        """清理资源"""
        self.running.clear()
        self.close_images()

    def close_images(self):
        """关闭所有打开的图像"""
        for img in self.icon_images:
            try:
                img.close()
            except Exception:
                pass
        self.icon_images.clear()

        for img in self._image_refs:
            try:
                img.close()
            except Exception:
                pass
        self._image_refs.clear()

    def add_image_ref(self, image: Image.Image):
        """跟踪图像引用"""
        self._image_refs.append(image)


class ResourceManager:
    def __init__(self):
        self._resources = []
        self._lock = threading.Lock()

    def register(self, resource):
        with self._lock:
            self._resources.append(resource)

    def cleanup(self):
        with self._lock:
            for resource in self._resources:
                try:
                    resource.close()
                except Exception as e:
                    logging.error(f"Error closing resource: {e}")
            self._resources.clear()


class RunCatApp:
    def __init__(self):
        self.config = Config()
        self.resource_manager = ResourceManager()
        self.tray_icon = None
        self.threads = []
        self.last_gc_time = time.time()
        self.last_net_io = None
        self.last_io_time = None

    def setup_logging(self):
        """设置日志系统"""
        log_dir = self.config.config_dir / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'runcat.log'

        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=3,
            encoding='utf-8'
        )

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler())

    @contextmanager
    def load_image(self, path: Path):
        """安全加载图像的上下文管理器"""
        image = Image.open(path)
        self.config.add_image_ref(image)
        try:
            yield image
        finally:
            pass

    def load_images(self, prefix_string: str):
        """加载图标图片"""
        try:
            image_paths = [
                get_resource_path(f'resources/cat/{prefix_string}_cat_{i}.ico')
                for i in range(5)
            ]
            loaded_images = []
            for path in image_paths:
                with self.load_image(path) as img:
                    img_copy = img.copy()
                    loaded_images.append(img_copy)
                    self.config.add_image_ref(img_copy)
            return loaded_images
        except Exception as e:
            logging.error(f"Error loading images: {e}")
            raise

    def get_memory_usage(self):
        """获取内存使用率"""
        return psutil.virtual_memory().percent

    def get_network_usage(self):
        """获取网络使用率"""
        current_net_io = psutil.net_io_counters()
        current_time = time.time()

        if self.last_net_io is None:
            self.last_net_io = current_net_io
            self.last_io_time = current_time
            return 0

        time_delta = current_time - self.last_io_time
        if time_delta <= 0:
            return 0

        bytes_sent = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / time_delta
        bytes_recv = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / time_delta

        self.last_net_io = current_net_io
        self.last_io_time = current_time

        total_mb_per_sec = (bytes_sent + bytes_recv) / (1024 * 1024)
        return min(total_mb_per_sec * 10, 100)

    def get_usage(self):
        """根据当前模式获取使用率"""
        try:
            if self.config.monitor_mode == MonitorMode.CPU:
                return psutil.cpu_percent(interval=1)
            elif self.config.monitor_mode == MonitorMode.MEMORY:
                return self.get_memory_usage()
            elif self.config.monitor_mode == MonitorMode.NETWORK:
                return self.get_network_usage()
        except Exception as e:
            logging.error(f"Error getting usage: {e}")
            return 0

    def get_cpu_usage(self):
        """监控系统使用率并更新图标更新间隔"""
        interval_list = [0.5, 0.3, 0.2, 0.1, 0.07]

        while self.config.running.is_set():
            try:
                usage = self.get_usage()
                with self.config.config_lock:
                    if usage < 10.0:
                        self.config.update_interval[0] = interval_list[0] * self.config.speed[0]
                    elif 10.0 <= usage < 20.0:
                        self.config.update_interval[0] = interval_list[1] * self.config.speed[0]
                    elif 20.0 <= usage < 40.0:
                        self.config.update_interval[0] = interval_list[2] * self.config.speed[0]
                    elif 40.0 <= usage < 60.0:
                        self.config.update_interval[0] = interval_list[3] * self.config.speed[0]
                    else:
                        self.config.update_interval[0] = interval_list[4] * self.config.speed[0]
                logging.debug(f"{self.config.monitor_mode.value} Usage: {usage}%")
            except Exception as e:
                if self.config.running.is_set():
                    logging.error(f"Error in monitoring: {e}")
                time.sleep(1)

    def update_icon(self, icon: pystray.Icon):
        """更新托盘图标动画"""
        index = 0
        while self.config.running.is_set():
            try:
                with self.config.config_lock:
                    current_image = self.config.icon_images[index]
                    update_time = self.config.update_interval[0]
                icon.icon = current_image
                index = (index + 1) % len(self.config.icon_images)
                time.sleep(update_time)
            except Exception as e:
                if self.config.running.is_set():
                    logging.error(f"Error updating icon: {e}")
                time.sleep(1)

    def ensure_config_exists(self):
        """确保配置文件存在"""
        if not self.config.config_path.exists():
            default_config = {
                "dark_mode": False,
                "speed": 1.0
            }
            self.save_config(default_config)

    def load_config(self):
        """加载配置"""
        try:
            with open(self.config.config_path, 'r') as f:
                data = json.load(f)
                self.config.dark_mode = data.get('dark_mode', False)
                self.config.speed[0] = float(data.get('speed', 1.0))
                mode_str = data.get('monitor_mode', 'CPU')
                self.config.monitor_mode = MonitorMode(mode_str)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            # 使用默认值
            self.config.dark_mode = False
            self.config.speed[0] = 1.0
            self.config.monitor_mode = MonitorMode.CPU

    def save_config(self, config_data=None):
        """保存配置"""
        if config_data is None:
            config_data = {
                "dark_mode": self.config.dark_mode,
                "speed": self.config.speed[0],
                "monitor_mode": self.config.monitor_mode.value
            }

        try:
            with open(self.config.config_path, 'w') as f:
                json.dump(config_data, f)
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def refresh_images(self):
        """刷新图标图片"""
        try:
            prefix_string = 'dark' if self.config.dark_mode else 'light'
            self.config.close_images()
            self.config.icon_images = self.load_images(prefix_string)
            logging.info("Images refreshed successfully")
        except Exception as e:
            logging.error(f"Error refreshing images: {e}")
            raise

    def toggle_theme(self):
        """切换主题"""
        try:
            with self.config.config_lock:
                self.config.dark_mode = not self.config.dark_mode
            self.save_config()
            self.refresh_images()
            logging.info(f"Theme changed to {'Dark' if self.config.dark_mode else 'Light'}")
        except Exception as e:
            logging.error(f"Error toggling theme: {e}")

    def set_speed(self, icon: pystray.Icon, speed_value: float):
        """设置速度"""
        try:
            with self.config.config_lock:
                self.config.speed[0] = speed_value
            self.save_config()
            icon.update_menu()
            logging.info(f"Speed changed to {speed_value}")
        except Exception as e:
            logging.error(f"Error setting speed: {e}")

    def set_monitor_mode(self, icon: pystray.Icon, mode: MonitorMode):
        """设置监控模式"""
        try:
            with self.config.config_lock:
                self.config.monitor_mode = mode
            self.save_config()
            icon.update_menu()
            logging.info(f"Monitor mode changed to {mode.value}")
        except Exception as e:
            logging.error(f"Error setting monitor mode: {e}")


    def star_me(self):
        """在浏览器中打开 GitHub 仓库"""
        try:
            webbrowser.open("https://github.com/Jas0nG/RunCat")
            logging.info("Opened GitHub page in web browser")
        except Exception as e:
            logging.error(f"Error opening GitHub page: {e}")

    def create_tray_icon(self):
        """创建系统托盘图标"""
        theme_item = Item(
            lambda text="": f"Theme: {'Dark' if self.config.dark_mode else 'Light'}",
            self.toggle_theme
        )

        speed_menu = Menu(
            Item("Slow", lambda icon, item: self.set_speed(icon, 1.5)),
            Item("Medium", lambda icon, item: self.set_speed(icon, 1.0)),
            Item("Fast", lambda icon, item: self.set_speed(icon, 0.5))
        )

        mode_menu = Menu(
            Item("CPU", lambda icon, item: self.set_monitor_mode(icon, MonitorMode.CPU)),
            Item("Memory", lambda icon, item: self.set_monitor_mode(icon, MonitorMode.MEMORY)),
            Item("Network", lambda icon, item: self.set_monitor_mode(icon, MonitorMode.NETWORK))
        )

        star_me_item = Item("Star✨", self.star_me)

        tray_menu = Menu(
            theme_item,
            Item(
                lambda text='Speed': f"Speed: {self.config.speed_labels.get(self.config.speed[0], 'Medium')}",
                speed_menu
            ),
            Item(
                lambda text='Mode': f"Mode: {self.config.monitor_mode.value}",
                mode_menu
            ),
            star_me_item,
            Item('Quit', self.quit_application)
        )

        return pystray.Icon(
            "RunCat",
            icon=self.config.icon_images[0],
            menu=tray_menu
        )

    def quit_application(self, icon):
        """安全退出应用程序"""
        logging.info("Quitting application...")
        self.config.running.clear()
        icon.stop()
        self.cleanup()

    def cleanup(self):
        """清理所有资源"""
        logging.info("Cleaning up resources...")
        self.config.cleanup()
        self.resource_manager.cleanup()

        # 等待所有线程结束
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1.0)

        # 强制GC
        gc.collect()

        logging.info("Cleanup completed")

    def run(self):
        """运行应用程序"""
        try:
            self.setup_logging()
            logging.info("Starting RunCat application...")

            self.ensure_config_exists()
            self.load_config()
            self.refresh_images()

            self.config.running.set()
            self.tray_icon = self.create_tray_icon()

            # 创建并启动线程
            cpu_thread = threading.Thread(
                target=self.get_cpu_usage,
                name="CPUMonitor",
                daemon=True
            )
            icon_thread = threading.Thread(
                target=self.update_icon,
                args=(self.tray_icon,),
                name="IconUpdater",
                daemon=True
            )

            self.threads.extend([cpu_thread, icon_thread])

            for thread in self.threads:
                thread.start()
                logging.info(f"Started thread: {thread.name}")

            # 运行托盘图标
            logging.info("Running tray icon...")
            self.tray_icon.run()

        except Exception as e:
            logging.critical(f"Application crashed: {e}")
            self.cleanup()
            raise
        finally:
            self.cleanup()


def get_resource_path(relative_path: str) -> Path:
    """获取资源文件的路径"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


if __name__ == "__main__":
    app = RunCatApp()
    try:
        app.run()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        sys.exit(1)