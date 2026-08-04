import os
import sys
import uart_wifi_cred
import serial
import time
import subprocess
import Sensor

UART_PORT = "/dev/serial0"
UART_TXD2 = 14
UART_RXD2 = 15
BAUD_RATE = 115200
READ_TIMEOUT = 1

def log(msg: str) -> None:
    print(f"[INFO] {msg}")

def err(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)

def run_cmd(cmd, check=True):
    result = subprocess.run(cmd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}\n"
        )
    return result

def check_root():
    if os.geteuid() != 0:
        err("This script must be run as root: sudo python3 uart_wifi_config.py")
        sys.exit(1)


def open_uart():
    return serial.Serial(
        port = UART_PORT,
        baudrate = BAUD_RATE,
        timeout = READ_TIMEOUT
    )

def main():
    NTU = pH = Temp = 0
    check_root()

    log(f"Opening UART on {UART_PORT} at {BAUD_RATE} baud")
    ser = open_uart()
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(2)

    log("Waiting for messages over UART...")

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            log(f"Recieved UART message: {line}")
            if "WIFI:" in line:
                result = uart_wifi_cred.main(line)
                if result == None:
                    result = "None"
                if isinstance(result, bytes):
                    result=result.decode()
                ser.write((result + "\n").encode())
            if "SENSOR_CMD:" in line:
                ser.write(b"OK:SENSOR STARTING!\n")
                log("Message Recieved")
                time.sleep(5)
                 
                for x in range(13):
                    ntu, ph, temp = Sensor.main()
                    NTU += ntu
                    pH += ph
                    Temp += temp
                    data = f"OK: PH={pH}|TURBIDITY={NTU}|OXYGEN={Temp}\n"
                    log(data)
                    time.sleep(1)
                    x += 1

                NTU = (NTU/13)
                pH = (pH/13)
                Temp = (Temp/13)
            if "SENSOR_READ" in line:
                data = f"OK: PH={pH}|TURBIDITY={NTU}|OXYGEN={Temp}\n"
                ser.write(data.encode())
                log(f"Data Sent: {data}")

        except Exception as e:
            err(f"Unexpected error: {e}")
            time.sleep(1)
    ser.close()


if __name__ == "__main__":
    main()
