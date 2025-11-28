# coding: utf-8
# last modified:20231031
import time
import serial
import re

class GPS:
    def __init__(self, port="/dev/wheeltec_gps", baud=9600, timeout=1.0):
        self.utctime = ''
        self.lat = ''
        self.ulat = ''
        self.lon = ''
        self.ulon = ''
        self.numSv = ''
        self.msl = ''
        self.cogt = ''
        self.cogm = ''
        self.sog = ''
        self.kph = ''
        self.gps_t = 0
        self.ser = serial.Serial(port, baud, timeout=timeout)
        if self.ser.isOpen():
            print("GPS Serial Opened! Baudrate=9600")
        else:
            print("GPS Serial Open Failed!")

    @staticmethod
    def Convert_to_degrees(ddmm_mmmm, hemi):
        """
        ddmm.mmmm + N/S/E/W -> 十进制度
        失败返回 None（而不是抛异常）
        """
        if not ddmm_mmmm:
            return None
        try:
            v = float(ddmm_mmmm)  # 允许带小数
        except Exception:
            return None

        deg = int(v // 100)
        minutes = v - deg * 100
        dec = deg + minutes / 60.0
        if hemi in ('S', 'W', 's', 'w'):
            dec = -dec
        return dec



    def GPS_read(self):
        """
        逐行读一条 NMEA；只在确认为 GGA / VTG 时解析。
        解析失败返回 0，不抛异常。
        """
        try:
            line = self.ser.readline().decode('ascii', errors='ignore').strip()
            if not line:
                return 0

            # ---------- GGA：时间、经纬度、卫星数、海拔 ----------
            if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                f = line.split(',')
                # 标准 GGA: 0:$GxGGA,1=UTC,2=lat,3=N/S,4=lon,5=E/W,6=fix,7=sats,8=HDOP,9=alt,10=M,...
                if len(f) < 11:
                    return 0

                self.utctime = f[1]
                lat = self.Convert_to_degrees(f[2], f[3])
                lon = self.Convert_to_degrees(f[4], f[5])
                if lat is None or lon is None:
                    return 0  # 本帧无效

                self.lat  = f"{lat:.8f}"
                self.ulat = f[3]
                self.lon  = f"{lon:.8f}"
                self.ulon = f[5]
                self.numSv = f[7] or ''
                # 海拔可能在 f[9]，单位在 f[10]（通常为 M）
                self.msl = f[9] if len(f) > 9 else ''

                self.gps_t = 1
                return 1

            # ---------- VTG：地速/地面航向 ----------
            if line.startswith('$GPVTG') or line.startswith('$GNVTG'):
                if self.gps_t != 1:
                    return 0
                f = line.split(',')
                # VTG: 0:$..VTG,1=cogt,2=T,3=cogm,4=M,5=sog(kn),6=N,7=sog(kmh),8=K,...
                # 字段可能为空，做防空处理
                self.cogt = (f[1] or '0.00') + 'T' if len(f) > 1 else '0.00T'
                self.cogm = (f[3] or '0.00') if len(f) > 3 else '0.00'
                self.sog  = (f[5] or '0.00') if len(f) > 5 else '0.00'
                self.kph  = (f[7] or '0.00') if len(f) > 7 else '0.00'
                return 0  # 维持原有行为：VTG 不返回 1

            # 其他句子（GSV/GSA/RMC等）忽略
            return 0

        except Exception:
            # 任何解析问题都吞掉，返回 0，避免像 'GPGSV' 再次把程序打崩
            return 0


    def GPS_show(self):
        print("*********************")
        print('UTC Time:'+self.utctime)
        print('Latitude:'+self.lat+self.ulat)
        print('Longitude:'+self.lon+self.ulon)
        print('Number of satellites:'+self.numSv)
        print('Altitude:'+self.msl)
        print('True north heading:'+self.cogt+'°')
        print('Magnetic north heading:'+self.cogm+'°')
        print('Ground speed:'+self.sog+'Kn')
        print('Ground speed:'+self.kph+'Km/h')
        print("*********************")

    def GPS_stop(self):
        self.ser.close()
        print("GPS serial Close!")