import serial
import time
import adafruit_board_toolkit.circuitpython_serial
import sys
import boto3
import datetime
import subprocess
import os
import requests

DMESG_CMD = "/usr/bin/dmesg"
TAIL_CMD = "/usr/bin/tail"
GREP_CMD = "/usr/bin/grep"
CREATE_NESTED_DIR_CMD = "mkdir"
MOUNT_CMD = "mount"
CP_CMD = "cp"
SYNC_CMD = "sync"
LIST_CMD = "ls"

PATTERN_1 = '''"sd.*: sd.*"'''
PATTERN_2 = '''"sd.[0-9]"'''

DEV_DIR = "/dev"
MNT_DIR = "/mnt/pico"

USB_DEVICE = DEV_DIR + "/ttyACM*"

UF2_FILE_PATH = '''./Project/C/build/src/Main/Main.uf2'''

Headers = {"session_id": "testkey"}
upload_url = "https://ljgqi1zvt4.execute-api.us-west-2.amazonaws.com/v1/upload"
notify_url = "https://ljgqi1zvt4.execute-api.us-west-2.amazonaws.com/v1/notify"

def kill(s):
    print(f'{sys.argv[0]}: {s}', file=sys.stderr)
    sys.exit(1)

def listen():
    comports = adafruit_board_toolkit.circuitpython_serial.data_comports()
    device_COM = None
    while device_COM is None:
        cp = subprocess.run([LIST_CMD + " -a " + USB_DEVICE], shell=True, stdout=subprocess.PIPE)
        if cp.returncode == 0:
            device_COM = cp.stdout.decode("utf-8").split("\n")[0]
        else:
            print("Still waiting to detect usb device")
            time.sleep(1)

    print("detected device_COM: " + device_COM)
    lastTimeNoRead = None
    s3 = boto3.resource('s3')
    #if not comports:
        #kill("No comports module found")

    device = serial.Serial(device_COM, baudrate=115200)
    buffer = bytes()  
    try:
        print("Got here")
        while True:
            if device.in_waiting > 0:
                lastTimeNoRead = time.time()
                response = device.read(device.in_waiting)
                print(response);
                if bytes("Out of memory", 'utf-8') in response:
                    lastTimeNoRead = None
                    buffer = bytes() 
                    continue
                if bytes("Should take image?", 'utf-8') in response:
                    capture = input("Capture image?: ")
                    if (capture == 'y'):
                        device.write(bytes("c", 'utf-8'))
                        lastTimeNoRead = None
                        buffer = bytes() 
                        continue
                    elif (capture == 'n'):
                        device.write(bytes("i", 'utf-8'))
                        lastTimeNoRead = None
                        buffer = bytes() 
                        continue
                    elif (capture == 'q'):
                        device.write(bytes("q", 'utf-8'))
                        lastTimeNoRead = None
                        buffer = bytes() 
                        continue
                if bytes("done", 'utf-8') in response:
                    response = response.split(bytes("done", 'utf-8'))[0]
                    buffer = buffer + response
                    print("Got new picture!")
                    imageName = "/tmp/image_" + datetime.datetime.today().strftime("%d-%b-%Y-%H-%M-%S-%f") +  ".jpeg";
                    image = open(imageName, "wb+")
                    image.write(buffer)
                    image.close()
                    x = requests.get(upload_url, headers=Headers)
                    print("Status Code: " + str(x.status_code))
                    print(x.json())
                    buffer = bytes()
                    lastTimeNoRead = None
                buffer = buffer + response
            elif lastTimeNoRead is None:
                continue
            elif (time.time() - lastTimeNoRead) < 20:
                continue
            else:
                break
    

    finally:
        device.close()

def flash():
     #Create tmp directory
     if subprocess.run([CREATE_NESTED_DIR_CMD, "-p", MNT_DIR]).returncode != 0:
         kill("Cannot create mounted directory")

     disk_file = subprocess.run([GREP_CMD + " -o " + PATTERN_2], stdout=subprocess.PIPE, input=subprocess
               .run([GREP_CMD + " -o " + PATTERN_1], stdout=subprocess.PIPE, input=subprocess
               .run([TAIL_CMD], stdout=subprocess.PIPE, input=subprocess
                    .run([DMESG_CMD], stdout=subprocess.PIPE).stdout).stdout, shell=True).stdout, shell=True).stdout.decode("utf-8").split("\n")[0]
     
     if "sd" not in disk_file:
         kill("Can't find pico disk file")
    
     if subprocess.run([MOUNT_CMD, DEV_DIR + "/" + disk_file, MNT_DIR]).returncode != 0:
         kill("Can't mount disk on temp folder")
          
     if not os.access(UF2_FILE_PATH, os.R_OK):
         kill("UF2 File does not exist")
    
     if subprocess.run([CP_CMD, UF2_FILE_PATH, MNT_DIR]).returncode != 0:
         kill("Can't copy uf2 file to pico")

     if subprocess.run([SYNC_CMD]).returncode != 0:
         kill("Can't flash uf2 file to pico")

          
def main():
     # Flash UF2 on PICO
     flash()
     listen()


if __name__ == "__main__":
    main()