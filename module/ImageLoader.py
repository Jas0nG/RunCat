from pathlib import Path
from PIL import Image
from ConfigManager import ConfigManager

class ImageLoader:
    @staticmethod
    def load_images(prefix_string):
        """
        Load a series of cat images based on the given prefix string.
        根据给定的前缀字符串加载一系列图像。
        Args:
            prefix_string (str): The prefix string used to generate the image paths.
        Returns:
            list: A list of opened image objects.
        参数:
            prefix_string (str): 用于生成图像路径的前缀字符串。
        返回:
            list: 打开的图像对象列表。
        """
        image_paths = [Path(f'./resources/cat/{prefix_string}_cat_{i}.ico') for i in range(5)]
        return [Image.open(image_path) for image_path in image_paths]

    @staticmethod
    def load_images():
        """
        Load a series of cat images based on the current color setting.

        Returns:
            list: A list of opened image objects.

        根据当前的颜色设置加载一系列图像。

        返回:
            list: 打开的图像对象列表。
        """
        prefix_string = ConfigManager.get_setting("settings.dark_mode") and "dark" or "light"
        print("color setting:", prefix_string)
        image_paths = [Path(f'./resources/cat/{prefix_string}_cat_{i}.ico') for i in range(5)]
        return [Image.open(image_path) for image_path in image_paths]