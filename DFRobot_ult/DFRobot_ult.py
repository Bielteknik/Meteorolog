import serial
import time

class DFRobot_A02_Distance:

  ## Board status 
  STA_OK = 0x00
  STA_ERR_CHECKSUM = 0x01
  STA_ERR_SERIAL = 0x02
  STA_ERR_CHECK_OUT_LIMIT = 0x03
  STA_ERR_CHECK_LOW_LIMIT = 0x04
  STA_ERR_DATA = 0x05

  ## last operate status, users can use this variable to determine the result of a function call. 
  last_operate_status = STA_OK

  ## variable 
  distance = 0

  ## Maximum range
  distance_max = 4500
  distance_min = 0
  range_max = 4500

  def __init__(self):
    self._ser = serial.Serial("COM4", 9600, timeout=1)
    if self._ser.isOpen() != True:
      self.last_operate_status = self.STA_ERR_SERIAL

  def set_dis_range(self, min, max):
    self.distance_max = max
    self.distance_min = min

  def getDistance(self):
    self._measure()
    return self.distance
  
  def _check_sum(self, l):
    return (l[0] + l[1] + l[2])&0x00ff

  def _measure(self):
    data = [0]*4
    i = 0
    timenow = time.time()

    while (self._ser.inWaiting() < 4):
      time.sleep(0.01)
      if ((time.time() - timenow) > 1):
        break
    
    rlt = self._ser.read(self._ser.inWaiting())
    #print(rlt)
    
    index = len(rlt)
    if(len(rlt) >= 4):
       index = len(rlt) - 4
       while True:
         try:
           data[0] = ord(rlt[index])
         except:
           data[0] = rlt[index]
         if(data[0] == 0xFF):
           break
         elif (index > 0):
           index = index - 1
         else:
           break
       #print(data)
       if (data[0] == 0xFF):
         try:
           data[1] = rlt[index + 1]
           data[2] = rlt[index + 2]
           data[3] = rlt[index + 3]
         except:
           data[1] = rlt[index + 1]
           data[2] = rlt[index + 2]
           data[3] = rlt[index + 3]
         i = 4
    #print(data)
    if i == 4:
      sum = self._check_sum(data)
      if sum != data[3]:
        self.last_operate_status = self.STA_ERR_CHECKSUM
      else:
        self.distance = data[1]*256 + data[2]
        self.last_operate_status = self.STA_OK
      if self.distance > self.distance_max:
        self.last_operate_status = self.STA_ERR_CHECK_OUT_LIMIT
        self.distance = self.distance_max
      elif self.distance < self.distance_min:
        self.last_operate_status = self.STA_ERR_CHECK_LOW_LIMIT
        self.distance = self.distance_min
    else:
      self.last_operate_status = self.STA_ERR_DATA
    return self.distance

