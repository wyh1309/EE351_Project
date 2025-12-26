from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'gps_serial_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
                # ⭐⭐ 添加 launch 文件安装 ⭐⭐
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yihan',
    maintainer_email='yihan@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gps_serial_node = gps_serial_pkg.gps_serial_node:main',
            'gps_receiver_node = gps_serial_pkg.gps_websocket_receiver_node:main', 
        ],
    },
)
