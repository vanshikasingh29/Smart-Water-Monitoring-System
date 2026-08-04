import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import time
import os
import glob
import json

spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D5)
mcp = MCP.MCP3008(spi, cs)

channel0 = AnalogIn(mcp, MCP.P0)
channel1 = AnalogIn(mcp, MCP.P1)

def Take_Readings():

    v0 = round(channel0.voltage, 2)
    v1 = round(channel1.voltage, 2)

    c0 = round(channel0.value, 2)
    c1 = round(channel1.value, 2)

# y = mv+c
#m = y2-y1/v2-v1
#c = y1 - mv1

    NTU = round(-278.3  * v0 + 317.8, 2)
    if NTU < 0:
        NTU = 0

    Ph = round(-11.11 * v1 + 20.78, 2)

    Temp = 5

    return NTU, Ph, Temp

def Write_Readings(NTU, Ph, Temp):
    data_file = 'Python/data.json'

    data = {
        "current": {
            "ph": Ph,
            "temperature": Temp,
            "turbidity": NTU,
           # "risk": "We Shall See",
           # "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        },
        "notifications": [
            {"message": Notification(NTU, Ph, Temp), "time":  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}
        ],
        "history": [{
            "ph": Ph,
            "temperature": Temp,
            "turbidity": NTU,
           # "risk": "It was ok",
           # "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }]
    }

    try:
        with open(data_file, 'r+') as f:
            try:
                File_Data = json.load(f)
            except json.JSONDecodeError:
                File_Data = {"current": {}, "notifications": [], "history": []}

            File_Data["current"].update(data["current"])
            File_Data["notifications"].extend(data["notifications"])
            File_Data["history"].extend(data["history"])
            f.seek(0)
            json.dump(File_Data, f, indent=4, separators=(",", ":"))
            f.truncate()
    except FileNotFoundError:
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=4, separators=(",", ":"))



def Notification(NTU, Ph, Temp):
    return "Happy Days"

def main():
    NTU = 0
    Ph = 0
    Temp = 0
    NTU, Ph, Temp = Take_Readings()
    Write_Readings(NTU, Ph, 5)

    return NTU, Ph, Temp
