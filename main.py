import sys
from pathlib import Path
import threading

module_path = Path(__file__).resolve().parent / 'module'
sys.path.append(str(module_path))

from ConfigManager import ConfigManager
from CPUUsageMonitor import CPUUsageMonitor
from TrayIconManager import TrayIconManager
from ImageLoader import ImageLoader

def main():
    # Initialize ConfigManager
    ConfigManager.initialize('config.json')

    images = ImageLoader.load_images()
    lock = threading.Lock()

    # global update_interval
    update_interval = [1.0]

    cpu_monitor = CPUUsageMonitor(update_interval, lock)
    cpu_monitor.start()

    tray_icon_manager = TrayIconManager(images, update_interval, lock)
    tray_icon_manager.run()

if __name__ == "__main__":
    main()