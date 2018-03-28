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
import psycopg2 as p
import psycopg2.extras as e

#0xF1F2F3F4C1 is command center
#0xF1F2F3F4A1 is the sensor
pipes = [[0xF1, 0xF2, 0xF3, 0XF4, 0xC1], [0xF1, 0xF2, 0xF3, 0xF4, 0xA1]]

#List of zones and their objects....
ZoneList = []


#Postgres SQL Constants.
host = "ec2-54-83-23-91.compute-1.amazonaws.com"
database = "d6q2l2eqtqu66u"
port = "5432"
username = "wcakxmmlvfppvl"
password = "509b5b0fac09ca205c14a6ff6e9db2d820b0d74d7142bc7aefd7144b73d710b6"
userID = 1 #hardcoded for now. might wana read in from a settings file
connection = None
cursor = None


#constant commands
cmdRequesDataPackage = 100
cmdPowerDown = 105
cmdReset = 110


#hue Constants
HueIP = '192.168.0.100'
#HueSecurityKey = 'NIlVZOyFJ1kDfw+m1osb2h-xDOqg2yfCG6q5vDu3d'
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
			
			print("Currently checking the zone with zone name: " + curZone.ZoneName)

			overrideflag = 10000 #some arbitrary number
			overrideflag = checkOverRideFlag(curZone.ZoneId) #check flag.
		
			#if user is not trying to override the settings then lets try to set the settings. 
			if (overrideflag == 0):
				RequesetData(curZone)
				if(RequesetData):
					AdjustLight(curZone)
			else:
				#change this to adjustlight manual function which we ahve to write to read brightness settings
				#change brightness setting. 
				print ("override flag is set for the zone:" + curZone.ZoneName + ", moving to next zone")
			
			#wait a second between each zone checks...
			time.sleep(1)

	
#this function initializes all of our antennas and devices for operations. 		
def setupAllDevices():
	global radio, bridge, receivedData
	
	print("Initialization sequence activated...")
	
	#connect to the Postgres Database
	if(ConnectToSQLDB()):
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
		
		#initialize all zones from the database....
		InitializeZoneList(userID)

		#hue configuration
		logging.basicConfig()
		bridge = phue.Bridge(HueIP, HueSecurityKey)
		time.sleep (0.2)

		print("Successfully initialized all devices and objects...")
	else:
		print ("Initialization sequence failed")

	
def ConnectToSQLDB():
	global connection, cursor
	try:
		connection =  p.connect("dbname = 'd6q2l2eqtqu66u' user = 'wcakxmmlvfppvl' host = 'ec2-54-83-23-91.compute-1.amazonaws.com' password = '509b5b0fac09ca205c14a6ff6e9db2d820b0d74d7142bc7aefd7144b73d710b6' port = '5432'")
		
		cursor = connection.cursor(cursor_factory =e.DictCursor)
		return True
		
	except :
		print ("An error occurred while connecting to the database please contact support")
		return False 



		
def InitializeZoneList(uid):
	global ZoneList

	try:
		query = "select * from zonetable where uid = " + str(uid) + ";"
		cursor.execute(query)
		rows = cursor.fetchall()

		for row in rows:
			object = Zone(row["zoneid"],row["uid"],row["zonename"],row["bulbid"],row["brightnesssetting"],row["lightsensorid"])
			ZoneList.append(object)
	except:
		print ("Error initializing zone list... maybe database connection is down, try resetting the pi")

	

def checkOverRideFlag(zoneID):
	try:
		query = "select overrideflag from zonetable where zoneid = " + str(zoneID) + ";"
		cursor.execute(query)
		result = cursor.fetchone()
		return (result[0])
	
	except:
		print ("Error checking override flag... maybe database connection is down, try resetting the pi")
		return 100



def GetUserID():
	return True 
	
	
	
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
	
	print ("the length of the data array is: " + str(len(rawSensorData)))
	print ("the Sensor ID is: " + str(receivedData.SensorID))
	print ("the Light Sensor value is: " + str(receivedData.LightSensorValue))
	print ("the Battery level is: " + str(receivedData.BatteryValue))
	return True
	
	
	

	
#light adjustment logic... 
def AdjustLight(curZone):

	mybulbList = curZone.bulbList.split(",")

    if (receivedData.LightSensorValue < 100):
		for bulb in mybulbList:
		    bridge.set_light(bulb,'bri', 200)	
			time.sleep (0.2)

	elif (receivedData.LightSensorValue > 100):
		for bulb in mybulbList:
		    bridge.set_light(bulb,'bri', 5)	
			time.sleep (0.2)
     

	
	
	
#class definitions below:	
#just to package up the incoming data to keep things nice and clean. 
class IncommingDataPackage:
	def __init__(self, SensorID,LightSensorValue,BatteryValue):
		self.SensorID = SensorID
		self.LightSensorValue = LightSensorValue
		self.BatteryValue = BatteryValue


		
		#zone objects... hard code for now ...later initialize to a list read in from a JSON file 
class Zone:
	def __init__(self,ZoneId,Uid,ZoneName,bulbList,Brightnesssetting,LightSensorID):
	
		self.ZoneId = ZoneId
		self.Uid = Uid
		self.ZoneName = ZoneName
		self.bulbList = bulbList
		self.Brightnesssetting = Brightnesssetting
		self.LightSensorID = LightSensorID
		


		
#entry point for the code 		
if __name__ == '__main__':
	main()
