import serial
import time
import adafruit_board_toolkit.circuitpython_serial
import sys
import boto3
import datetime


comports = adafruit_board_toolkit.circuitpython_serial.data_comports()
device_COM = '/dev/ttyACM11'
lastTimeNoRead = None
s3 = boto3.resource('s3')
#if not comports:
 #   raise Exception("No modules found")

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
                image = open("saved1.jpeg", "wb+")
                image.write(buffer)
                image.close()
                image = open("saved1.jpeg", "rb+")
                imageName = "image_" + datetime.datetime.today().strftime("%d-%b-%Y-%H-%M-%S-%f") +  ".jpeg";
                s3.Bucket('arducambucket').put_object(Key=imageName, Body=image) 
                print("Sent image to S3 Bucket!")
                print(buffer)
                buffer = bytes()
                lastTimeNoRead = None
                print("Would you like to continue?")
                con = input("Continue: ")
                if (con == "y"):
                	break
                else:
                	continue
                
            buffer = buffer + response
        elif lastTimeNoRead is None:
            continue
        elif (time.time() - lastTimeNoRead) < 20:
            continue
        else:
            break
    

finally:
    device.close()
