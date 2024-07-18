import threading
import json

class ConfigManager:
    """
    A class for managing configuration settings.

    用于管理配置设置的类。

    Attributes:
        _instance (ConfigManager): The singleton instance of the ConfigManager class.
            ConfigManager类的单例实例。
        _lock (threading.Lock): A lock to ensure thread safety when initializing the instance.
            用于在初始化实例时确保线程安全的锁。
        _settings (dict): The loaded configuration settings.
            加载的配置设置。
    """

    _instance = None
    _lock = threading.Lock()
    _settings = None

    @classmethod
    def initialize(cls, config_path='config.json'):
        """
        Initializes the ConfigManager instance with the specified configuration file.

        使用指定的配置文件初始化ConfigManager实例。

        Args:
            config_path (str, optional): The path to the configuration file. Defaults to 'config.json'.
                配置文件的路径。默认为'config.json'。

        Raises:
            Exception: If ConfigManager is not initialized. Call 'ConfigManager.initialize()' first.
                如果ConfigManager未初始化。请先调用'ConfigManager.initialize()'。
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._settings = cls._instance.load_config(config_path)

    @classmethod
    def load_config(cls, config_path):
        """
        Loads the configuration settings from the specified file.

        从指定的文件加载配置设置。

        Args:
            config_path (str): The path to the configuration file.
                配置文件的路径。

        Returns:
            dict: The loaded configuration settings.
                加载的配置设置。
        """
        with open(config_path, 'r') as file:
            config = json.load(file)
        return config

    @classmethod
    def get_setting(cls, key, default=None):
        """
        Retrieves the value of the specified setting.

        获取指定设置的值。

        Args:
            key (str): The key of the setting, in dot notation (e.g., 'section.subsection.setting').
                设置的键，使用点表示法（例如，'section.subsection.setting'）。
            default (Any, optional): The default value to return if the setting is not found. Defaults to None.
                如果未找到设置，则返回的默认值。默认为None。

        Returns:
            Any: The value of the setting, or the default value if the setting is not found.
                设置的值，如果未找到设置，则返回默认值。
        """
        if cls._settings is None:
            raise Exception("ConfigManager is not initialized. Call 'ConfigManager.initialize()' first.")
        
        keys = key.split('.')
        value = cls._settings
        try:
            for k in keys:
                value = value[k]
        except KeyError:
            return default
        return value
