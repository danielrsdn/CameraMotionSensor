import serial
import time
import adafruit_board_toolkit.circuitpython_serial
import sys
import datetime
import subprocess
import os
import requests
import face_recognition
from multiprocessing import Process, Queue
from queue import Empty
import json

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
UPLOAD_URL = "https://ljgqi1zvt4.execute-api.us-west-2.amazonaws.com/v1/upload"
NOTIFY_URL = "https://ljgqi1zvt4.execute-api.us-west-2.amazonaws.com/v1/notify"


class LambdaAPI:
    @staticmethod
    def uploadAndNotifyImage(image):
        response = requests.get(UPLOAD_URL, headers=Headers)
        if response.status_code == 200:
            response = response.json()
            if response['httpRequest'] == 'PUT':
                with open(image, "rb") as i:
                    imageData = i.read()
                    Headers2 = {}
                    for k in response['headers']:
                        Headers2[k] = response['headers'][k][0]
                    response2 = requests.put(response['url'], data=imageData, headers=Headers2)
                    print("Attempt to upload image to s3: "  + str(response2))
                    if (response2.status_code // 200) == 1:
                        response3 = requests.put(NOTIFY_URL, json={'photoName': response['photoName']}, headers=Headers)
                        print("Attempt to notify image: "  + str(response3))
                        if (response3.status_code // 200 == 1):
                            print("Succesfully uploaded image and notified device owner(s)")


class ImageAnalyzer:
    @staticmethod
    def detectFace(imagePath, queue):
        print("Detecting face for  " + imagePath)
        image = face_recognition.load_image_file(imagePath)
        face_locations = face_recognition.face_locations(image)
        if len(face_locations) > 0:
            print("Detected face for  " + imagePath)
            queue.put(imagePath)
            queue.close()
    
    @staticmethod
    def waitForFaceDetection(queue):
        imagePath = queue.get()
        LambdaAPI.uploadAndNotifyImage(imagePath)

class ImageHandler:    
    def validateImage(self, image, queue):
        Process(target=ImageAnalyzer.detectFace, args=(image, queue,)).start()

    def waitForValidation(self, queue):
        Process(target=ImageAnalyzer.waitForFaceDetection, args=(queue,)).start()
    

class Listener:
    def __init__ (self, device, imageHandler, burstSize):
        self.device = device
        self.buffer = bytes()
        self.imageHandler = imageHandler
        self.lastTimeNoRead = None
        self.burstSize = burstSize
    
    def receiveAndHandleImage(self, queue):
        self.lastTimeNoRead = None
        self.buffer = bytes()

        while True:
            if self.device.in_waiting > 0:
                self.lastTimeNoRead = time.time()
                response = self.device.read(self.device.in_waiting)
            
                if bytes("Out of memory", 'utf-8') in response:
                    self.lastTimeNoRead = None
                    self.buffer = bytes() 
                    break
                
                if bytes("done", 'utf-8') in response:
                    #print("Read image from Pico")
                    response = response.split(bytes("done", 'utf-8'))[0]
                    self.buffer = self.buffer + response
                    #print("Got new picture!")
                    imageName = "/tmp/image_" + datetime.datetime.today().strftime("%d-%b-%Y-%H-%M-%S-%f") +  ".jpeg";
                    image = open(imageName, "wb+")
                    image.write(self.buffer)
                    image.close()
                    self.imageHandler.validateImage(imageName, queue)
                    self.lastTimeNoRead = None
                    break
                
                self.buffer = self.buffer + response
        
            elif self.lastTimeNoRead is None:
                continue
            elif (time.time() - self.lastTimeNoRead) < 20:
                continue
            else:
                break


    def listen(self):
        while True:
            if self.device.in_waiting > 0:
                self.lastTimeNoRead = time.time()
                response = self.device.read(self.device.in_waiting)

                if bytes("Out of memory", 'utf-8') in response:
                    self.lastTimeNoRead = None
                    self.buffer = bytes() 

                if bytes("Should take image?", 'utf-8') in response:
                    self.device.write(bytes([self.burstSize]))
                    queue = Queue()
                    for i in range(0, self.burstSize):
                        self.receiveAndHandleImage(queue)
                    self.imageHandler.waitForValidation(queue)
                
            elif self.lastTimeNoRead is None:
                continue
            elif (time.time() - self.lastTimeNoRead) < 20:
                continue
            else:
                break

def kill(s):
    print(f'{sys.argv[0]}: {s}', file=sys.stderr)
    sys.exit(1)

def start():
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

    #if not comports:
        #kill("No comports module found")

    device = serial.Serial(device_COM, baudrate=115200)
    imageHandler = ImageHandler()
    listener = Listener(device, imageHandler, 5)
    try: 
        listener.listen()
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
     start()


if __name__ == "__main__":
    main()