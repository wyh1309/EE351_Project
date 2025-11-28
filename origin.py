import time
from collections import deque


def establish_origin(gps,
                     warmup_s=10,        # 暖机时间（等收星/时钟稳定）
                     min_sats=10,        # 卫星数门限
                     collect_s=10,       # 满足门限后采样这么久
                     max_wait_s=20):    # 最长等待时间（避免无限等）
    t_start = time.time()
    # 1) 先暖机
    while time.time() - t_start < warmup_s:
        gps.GPS_read()  # 读读数据，丢弃
        print("read")
        print(gps.GPS_read())
        time.sleep(1)

    # 2) 采样满足门限的点，做中位数作为原点
    buf_lat = deque()
    buf_lon = deque()
    t_collect_start = None

    while True:
        if gps.GPS_read():
            # G60.py 里 self.lat/self.lon 已经是十进制度字符串
            try:
                lat = float(str(gps.lat).strip("NSEW"))
                lon = float(str(gps.lon).strip("NSEW"))
                sats = int(gps.numSv) if gps.numSv else 0
            except:
                continue

            if sats >= min_sats:
                if t_collect_start is None:
                    t_collect_start = time.time()
                buf_lat.append(lat)
                buf_lon.append(lon)

        # 采样时间到 -> 用中位数定原点
        if t_collect_start and (time.time() - t_collect_start >= collect_s) and len(buf_lat) >= 10:
            lat_sorted = sorted(buf_lat)
            lon_sorted = sorted(buf_lon)
            lat0 = lat_sorted[len(lat_sorted)//2]
            lon0 = lon_sorted[len(lon_sorted)//2]
            print(f"[INIT] 原点已建立：lat={lat0:.8f}, lon={lon0:.8f} （基于 {len(buf_lat)} 个样本，中位数）")
            return lat0, lon0

        # 超时兜底：拿到第一个可解析点就开始
        if time.time() - t_start > max_wait_s:
            if len(buf_lat) > 0:
                lat0 = buf_lat[-1]; lon0 = buf_lon[-1]
                print(f"[INIT] 超时兜底：使用最新点作为原点 lat={lat0:.8f}, lon={lon0:.8f}")
                return lat0, lon0
            # 还没有可用点，就直接尝试当前帧
            if gps.GPS_read():
                try:
                    lat0 = float(str(gps.lat).strip("NSEW"))
                    lon0 = float(str(gps.lon).strip("NSEW"))
                    print(f"[INIT] 超时兜底：使用当前点作为原点 lat={lat0:.8f}, lon={lon0:.8f}")
                    return lat0, lon0
                except:
                    pass

        time.sleep(0.02)
