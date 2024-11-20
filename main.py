#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   TianchenWu, XueWeiHan
#   Date    :   2024-08-15 20:01
#   Desc    :   RunCat
import time
import pystray
import psutil
import threading
import json
from pathlib import Path
from PIL import Image
from pystray import MenuItem as Item, Menu
import sys
import logging
from typing import List, Dict


# 设置日志
def setup_logging():
    log_dir = Path.home() / '.runcat' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / 'runcat.log'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )


# 全局变量
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


config = Config()


def get_resource_path(relative_path: str) -> Path:
    """获取资源文件的路径，适用于开发环境和打包环境"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


def ensure_config_exists():
    """确保配置文件存在，如果不存在则创建默认配置"""
    try:
        config.config_dir.mkdir(parents=True, exist_ok=True)
        if not config.config_path.exists():
            default_config = {
                "settings": {
                    "dark_mode": False,
                    "speed": [1.0]
                }
            }
            with open(config.config_path, 'w') as file:
                json.dump(default_config, file, indent=4)
            logging.info("Created default config file")
    except Exception as e:
        logging.error(f"Error creating config file: {e}")
        raise


def load_config():
    """加载配置文件"""
    try:
        with open(config.config_path, 'r') as file:
            conf = json.load(file)
        with config.config_lock:
            config.dark_mode = conf['settings']['dark_mode']
            config.speed = conf['settings']['speed']
        logging.info("Config loaded successfully")
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise


def save_config():
    """保存配置到文件"""
    try:
        with config.config_lock:
            conf = {
                "settings": {
                    "dark_mode": config.dark_mode,
                    "speed": config.speed
                }
            }
        with open(config.config_path, 'w') as file:
            json.dump(conf, file, indent=4)
        logging.info("Config saved successfully")
    except Exception as e:
        logging.error(f"Error saving config: {e}")
        raise


def load_images(prefix_string: str):
    """加载图标图片"""
    try:
        image_paths = [get_resource_path(f'resources/cat/{prefix_string}_cat_{i}.ico')
                       for i in range(5)]
        return [Image.open(str(path)) for path in image_paths]
    except Exception as e:
        logging.error(f"Error loading images: {e}")
        raise


def refresh_images():
    """刷新图标图片"""
    try:
        prefix_string = 'dark' if config.dark_mode else 'light'
        config.icon_images = load_images(prefix_string)
        logging.info("Images refreshed successfully")
    except Exception as e:
        logging.error(f"Error refreshing images: {e}")
        raise


def get_cpu_usage(update_interval: List[float]):
    """监控CPU使用率并更新图标更新间隔"""
    interval_list = [0.5, 0.3, 0.2, 0.1, 0.07]

    while True:
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            with config.config_lock:
                if cpu_usage < 10.0:
                    update_interval[0] = interval_list[0] * config.speed[0]
                elif 10.0 <= cpu_usage < 20.0:
                    update_interval[0] = interval_list[1] * config.speed[0]
                elif 20.0 <= cpu_usage < 40.0:
                    update_interval[0] = interval_list[2] * config.speed[0]
                elif 40.0 <= cpu_usage < 60.0:
                    update_interval[0] = interval_list[3] * config.speed[0]
                else:
                    update_interval[0] = interval_list[4] * config.speed[0]
            logging.debug(f"CPU Usage: {cpu_usage}%")
        except Exception as e:
            logging.error(f"Error in CPU monitoring: {e}")
            time.sleep(1)


def update_icon(icon: pystray.Icon):
    """更新托盘图标动画"""
    index = 0
    while True:
        try:
            with config.config_lock:
                current_image = config.icon_images[index]
                update_time = config.update_interval[0]
            icon.icon = current_image
            index = (index + 1) % len(config.icon_images)
            time.sleep(update_time)
        except Exception as e:
            logging.error(f"Error updating icon: {e}")
            time.sleep(1)


def toggle_theme():
    """切换主题"""
    try:
        with config.config_lock:
            config.dark_mode = not config.dark_mode
        save_config()
        refresh_images()
        logging.info(f"Theme changed to {'Dark' if config.dark_mode else 'Light'}")
    except Exception as e:
        logging.error(f"Error toggling theme: {e}")


def set_speed(icon: pystray.Icon, speed_value: float):
    """设置速度"""
    try:
        with config.config_lock:
            config.speed[0] = speed_value
        save_config()
        icon.update_menu()
        logging.info(f"Speed changed to {speed_value}")
    except Exception as e:
        logging.error(f"Error setting speed: {e}")


def setup_tray_icon():
    """设置系统托盘图标"""
    try:
        ensure_config_exists()
        load_config()
        refresh_images()

        theme_item = Item(
            lambda text="": f"Theme: {'Dark' if config.dark_mode else 'Light'}",
            toggle_theme
        )

        speed_menu = Menu(
            Item("Slow", lambda icon, item: set_speed(icon, 1.5)),
            Item("Medium", lambda icon, item: set_speed(icon, 1.0)),
            Item("Fast", lambda icon, item: set_speed(icon, 0.5))
        )

        tray_menu = Menu(
            theme_item,
            Item(
                lambda text='Speed': f"Speed: {config.speed_labels.get(config.speed[0], 'Medium')}",
                speed_menu
            ),
            Item('Quit', lambda icon, item: icon.stop())
        )

        tray = pystray.Icon("RunCat", icon=config.icon_images[0], menu=tray_menu)

        cpu_thread = threading.Thread(
            target=get_cpu_usage,
            args=(config.update_interval,),
            daemon=True
        )
        cpu_thread.start()

        icon_thread = threading.Thread(
            target=update_icon,
            args=(tray,),
            daemon=True
        )
        icon_thread.start()

        tray.run()

    except Exception as e:
        logging.error(f"Error setting up tray icon: {e}")
        raise


if __name__ == "__main__":
    try:
        setup_logging()
        setup_tray_icon()
    except Exception as e:
        logging.critical(f"Application crashed: {e}")
        sys.exit(1)