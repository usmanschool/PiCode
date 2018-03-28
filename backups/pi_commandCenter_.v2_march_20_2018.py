#code works with only python 3 and above......
#note we will be mapping python integers to Arduino Long variables 
#furthermore dont forget to specify little endian


import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
from struct import *
import time
import spidev
import phue
import logging

#0xF1F2F3F4C1 is command center
#0xF1F2F3F4A1 is the sensor
pipes = [[0xF1, 0xF2, 0xF3, 0XF4, 0xC1], [0xF1, 0xF2, 0xF3, 0xF4, 0xA1]]

#device list with their unique IDs
deviceList = [1001,1002]
ZoneList = []


#constant commands
cmdRequesDataPackage = 100
cmdPowerDown = 105
cmdReset = 110


#hue Constants
HueIP = '192.168.0.100'
#HueSecurityKey = 'NIlVZOyFJ1kDfwm1osb2h-xDOqg2yfCG6q5vDu3d'
HueSecurityKey = 'NIlVZOyFJ1kDfwm1osb2h-xDOqg2yfCG6q5vDu3d'


#global object list
radio = None
receivedData = None	
bridge = None


def main():
	
	#initialize all of the devices and objects required 
	setupAllDevices()
	
	#loop forever
	while True:
		for curZone in ZoneList:
			RequesetData(curZone)
			if(RequesetData):
				AdjustLight(curZone)
			time.sleep(1)
	
				
		

#this function initializes all of our antennas and devices for operations. 		
def setupAllDevices():
	global radio, bridge, receivedData
	
	print("Initialization sequence activated...")
	GPIO.setmode(GPIO.BCM)
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
	
	#initialize the incoming package object 
	receivedData = IncommingDataPackage(0,0,0)
	
	#create the zone objects, note this will later be changed to be read in from a JSON File
	myZone1 = Zone(1002,1)
	myZone2 = Zone(1002,2)
	ZoneList.append(myZone1)
	ZoneList.append(myZone2)
	
	#hue configuration
	logging.basicConfig()
	bridge = phue.Bridge(HueIP, HueSecurityKey)
	time.sleep (0.2)

	print("Successfully initialized all devices and objects...")

	

	
	
	
	
def RequesetData(curZone):
	#stop listening so we can talk
	radio.stopListening()
	#might not need the little endian thing
	commandPackage = pack('<ii',curZone.LightSensorID,cmdRequesDataPackage)
	radio.write(commandPackage)
	print ("Requested Data from: " + str(curZone.LightSensorID))
	
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
		#continue
		return False
	
	#if we dont get timed out then ul reach this point else you wont
	
	rawSensorData = []
	radio.read(rawSensorData, radio.getDynamicPayloadSize())
	
	
	#map the raw data to the correct variables
	#overwrite the received Data Object's parameters	
	receivedData.SensorID = int.from_bytes(rawSensorData[0:3],byteorder='little', signed=False)
	receivedData.LightSensorValue = int.from_bytes(rawSensorData[4:7],byteorder='little', signed=False)
	receivedData.BatteryValue = int.from_bytes(rawSensorData[8:11],byteorder='little', signed=False)	
	
	print("the length of the data array is: " + str(len(rawSensorData)))
	print ("the Sensor ID is: " + str(receivedData.SensorID))
	print ("the Light Sensor value is: " + str(receivedData.LightSensorValue))
	print ("the Battery level is: " + str(receivedData.BatteryValue))
	return True
	
	
	

	
#light adjustment logic... 
def AdjustLight(curZone):
    if (receivedData.LightSensorValue < 100):
        bridge.set_light(curZone.BulbID,'bri', 200)	
        time.sleep (0.2)
    elif (receivedData.LightSensorValue > 100):
        bridge.set_light(curZone.BulbID,'bri', 5)	

	
	
	
#class definitions below:	
#just to package up the incoming data to keep things nice and clean. 
class IncommingDataPackage:
	def __init__(self, SensorID,LightSensorValue,BatteryValue):
		self.SensorID = SensorID
		self.LightSensorValue = LightSensorValue
		self.BatteryValue = BatteryValue


		
		#zone objects... hard code for now ...later initialize to a list read in from a JSON file 
class Zone:
	def __init__(self,LightSensorID,BulbID):
		self.LightSensorID = LightSensorID
		self.BulbID = BulbID


		
#entry point for the code 		
if __name__ == '__main__':
	main()
