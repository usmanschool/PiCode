import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
from struct import *
import time
import spidev

GPIO.setmode(GPIO.BCM)

#code works with only python 3 and above......
#note we will be mapping python integers to Arduino Long variables 
#furthermore dont forget to specify little endian


#0xF1F2F3F4C1 is command center
#0xF1F2F3F4A1 is the sensor
pipes = [[0xF1, 0xF2, 0xF3, 0XF4, 0xC1], [0xF1, 0xF2, 0xF3, 0xF4, 0xA1]]

#device list with their unique IDs
deviceList = [1001,1002]
cmdRequesDataPackage = 100
cmdPowerDown = 105
cmdReset = 110

radio = NRF24(GPIO, spidev.SpiDev())
radio.begin(0, 17)

#allow a maximum of 32 bytes
#notes that we are transmitting arrays of bytes
radio.setPayloadSize(32)
radio.setChannel(0x76)
radio.setDataRate(NRF24.BR_1MBPS)
radio.setPALevel(NRF24.PA_MAX)
#radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()
radio.openReadingPipe(1, pipes[0])
radio.openWritingPipe(pipes[1])
radio.printDetails()


#loop forever
while True:
	for curDevice in deviceList:
		#stop listening so we can talk
		radio.stopListening()
		#might not need the little endian thing
		commandPackage = pack('<ii',curDevice,cmdRequesDataPackage)
		radio.write(commandPackage)
		print ("Requested Data from: " + str(curDevice))
		
		#start listening for the response
		radio.startListening()
		
		#define the timeout variable for now we set the timeout to be 1 second
		timeout = time.time() + 1   
		timedOut = False
		#wait for the timeout
		while not radio.available():
			if time.time() > timeout:
				timedOut = True
				break
		
		if timedOut:
			print ("timed out no response received")
			#move to the next device
			continue 
		
		#if we dont get timed out then ul reach this point else you wont
		
		rawSensorData = []
		radio.read(rawSensorData, radio.getDynamicPayloadSize())
		
		#initialize the storage variables....
		receivedSensorID = 0
		receivedLightSensorValue = 0
		receivedBatteryValue = 0
		
		#map the raw data to the correct variables
		#note if we are using longs, then we will need change each array to be 4 bytes long 	
		receivedSensorID = int.from_bytes(rawSensorData[0:3],byteorder='little', signed=False)
		receivedLightSensorValue = int.from_bytes(rawSensorData[4:7],byteorder='little', signed=False)
		receivedBatteryValue = int.from_bytes(rawSensorData[8:11],byteorder='little', signed=False)
		
		
		
		print("the length of the data array is: " + str(len(rawSensorData)))
		print ("the Sensor ID is: " + str(receivedSensorID))
		print ("the Light Sensor value is: " + str(receivedLightSensorValue))
		print ("the Battery level is: " + str(receivedBatteryValue))
		time.sleep(5)
	
				
		
	
