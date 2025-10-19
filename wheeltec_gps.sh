#!/bin/bash
echo 'KERNEL=="ttyACM*", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d4", ATTRS{serial}=="597C001526", MODE:="0777", GROUP:="dialout", SYMLINK+="wheeltec_gps"' | sudo tee /etc/udev/rules.d/wheeltec_gps.rules

# 重新加载 udev 规则并触发一次
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty --action=add
