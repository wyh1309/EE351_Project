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
    def Convert_to_degrees(in_data1, in_data2):
        len_data1 = len(in_data1)
        str_data2 = "%05d" % int(in_data2)
        temp_data = int(in_data1)
        symbol = 1
        if temp_data < 0:
            symbol = -1
        degree = int(temp_data / 100.0)
        str_decimal = str(in_data1[len_data1-2]) + str(in_data1[len_data1-1]) + str(str_data2)
        f_degree = int(str_decimal)/60.0/100000.0
        # print("f_degree:", f_degree)
        if symbol > 0:
            result = degree + f_degree
        else:
            result = degree - f_degree
        return result


    def GPS_read(self):
        if self.ser.inWaiting():
            if self.ser.read(1) == b'G':
                time.sleep(.05) 
                if self.ser.inWaiting():
                    if self.ser.read(1) == b'N':
                        if self.ser.inWaiting():
                            choice = self.ser.read(1)
                            if choice == b'G':
                                if self.ser.inWaiting():
                                    if self.ser.read(1) == b'G':
                                        if self.ser.inWaiting():
                                            if self.ser.read(1) == b'A':
                                                #utctime = self.ser.read(7)
                                                GGA = self.ser.read(70)
                                                GGA_g = re.findall(r"\w+(?=,)|(?<=,)\w+", str(GGA))
                                                # print(GGA_g)
                                                if len(GGA_g) < 13:
                                                    print("GPS no found")
                                                    self.gps_t = 0
                                                    return 0
                                                else:
                                                    self.utctime = GGA_g[0]
                                                    # lat = GGA_g[2][0]+GGA_g[2][1]+'°'+GGA_g[2][2]+GGA_g[2][3]+'.'+GGA_g[3]+'\''
                                                    self.lat = "%.8f" % self.Convert_to_degrees(str(GGA_g[2]), str(GGA_g[3]))
                                                    self.ulat = GGA_g[4]
                                                    # lon = GGA_g[5][0]+GGA_g[5][1]+GGA_g[5][2]+'°'+GGA_g[5][3]+GGA_g[5][4]+'.'+GGA_g[6]+'\''
                                                    self.lon = "%.8f" % self.Convert_to_degrees(str(GGA_g[5]), str(GGA_g[6]))
                                                    self.ulon = GGA_g[7]
                                                    self.numSv = GGA_g[9]
                                                    self.msl = GGA_g[12]+'.'+GGA_g[13]+GGA_g[14]
                                                    #print(GGA_g)
                                                    self.gps_t = 1
                                                    return 1
                            elif choice == b'V':
                                if self.ser.inWaiting():
                                    if self.ser.read(1) == b'T':
                                        if self.ser.inWaiting():
                                            if self.ser.read(1) == b'G':
                                                if self.gps_t == 1:
                                                    VTG = self.ser.read(40)
                                                    VTG_g = re.findall(r"\w+(?=,)|(?<=,)\w+", str(VTG))
                                                    self.cogt = VTG_g[0]+'.'+VTG_g[1]+'T'
                                                    if VTG_g[3] == 'M':
                                                        self.cogm = '0.00'
                                                        self.sog = VTG_g[4]+'.'+VTG_g[5]
                                                        self.kph = VTG_g[7]+'.'+VTG_g[8]
                                                    elif VTG_g[3] != 'M':
                                                        self.cogm = VTG_g[3]+'.'+VTG_g[4]
                                                        self.sog = VTG_g[6]+'.'+VTG_g[7]
                                                        self.kph = VTG_g[9]+'.'+VTG_g[10]
                                                #print(kph)

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

    

