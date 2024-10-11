import serial
import serial.tools.list_ports
import configparser
import paho.mqtt.client as mqtt
import mysql.connector
from mysql.connector import Error
import pandas as pd
import functools
import operator

def create_server_connection(host_name, user_name, user_password, db_name):		#funzione utile alla connessione
	connection = None															#tra database e script python
	try:
		connection = mysql.connector.connect(
			host=host_name,
			user=user_name,
			passwd=user_password,
			database=db_name
		)
		print("MySQL Database connection successful")
	except Error as err:
		print(f"Error: '{err}'")
	return connection

def read_query(connection, query):												#funzione utile all'esecuzione
	cursor = connection.cursor()												#di una query che richiede dati
	result = None
	try:
		cursor.execute(query)
		result = cursor.fetchall()
		return result
	except Error as err:
		print(f"Error: '{err}'")

def execute_query(connection, query):											#funzione utile all'esecuzione
	cursor = connection.cursor()												#di una query che modifica dati
	try:
		cursor.execute(query)
		connection.commit()
		print("Query successful")
	except Error as err:
		print(f"Error: '{err}'")

def execute_insert(connection, query, value):				#funzione utile all'esecuzione
	cursor = connection.cursor()							#di una query che modifica dati
	try:
		cursor.execute(query, value)
		connection.commit()
		print("Query successful")
	except Error as err:
		print(f"Error: '{err}'")

class Bridge():

	def __init__(self):
		self.config = configparser.ConfigParser()
		self.config.read('config.ini')
		self.setupMQTT()

	def setupMQTT(self):
		self.clientMQTT = mqtt.Client()
		self.clientMQTT.on_connect = self.on_connect
		self.clientMQTT.on_message = self.on_message
		print("connecting to MQTT broker...")
		self.clientMQTT.connect(
			self.config.get("MQTT","Server", fallback= "localhost"),
			self.config.getint("MQTT","Port", fallback= 1883),
			60)

		self.clientMQTT.loop_start()

	def on_connect(self, client, userdata, flags, rc):
		print("Connected with result code " + str(rc))

		self.clientMQTT.subscribe("animals/+")						#server-database richiesta della liste dei dispositivi
		self.clientMQTT.subscribe("animals/temperature/+")			#server-database richiesta della temperatura di un animale in un particolare mese
		self.clientMQTT.subscribe("animals/heartRate/+")			#server-database richiesta della frequenza cardiaca di un animale in un particolare mese
		self.clientMQTT.subscribe("animals/last_position/+")		#server-database richiesta dell'ultima posizione di un animale in un particolare mese
		self.clientMQTT.subscribe("average/+")						#server-database richiesta salvataggio dati di un dispositivo
		self.clientMQTT.subscribe("last_position/+")				#server-database richiesta salvataggio ultima posizione di un dispositivo

	def on_message(self, client, userdata, msg):
		print(msg.topic + " " + str(msg.payload))

		message = str(msg.payload)
		if(msg.topic == "animals/" and message == "b'request'"):				#funzione che esegue la query
			self.animals_request()												#di richiesta della lista di dispositivi
		if (msg.topic == "animals/temperature/" and message[2: 6].isdigit()):	#funzione che esegue la query di richiesta
			self.animal_temp_request(message[2: 6], message[7: -1])				#della temperatura di un animale in un particolare mese
		if (msg.topic == "animals/heartRate/" and message[2: 6].isdigit()):		#funzione che esegue la query di richiesta della
			self.animal_heart_rate_request(message[2: 6], message[7: -1])		#frequenza cardiaca di un animale in un particolare mese
		if (msg.topic == "animals/last_position/" and message[2: -1].isdigit()):#funzione che esegue la query di richiesta
			self.animal_last_position_request(message[2: -1])					#dell'ultima posizione di un animale in un particolare mese
		if (msg.topic == "average/" and message[2: 6].isdigit()):				#funzione che esegue la query
			self.save_average(message[2: 6], message[7: -1])					#di salvataggio delle medie
		if (msg.topic == "last_position/" and message[2: 6].isdigit()):			#funzione che esegue la query
			self.save_last_position(message[2: 6], message[7: -1])				#di salvataggio della posizione

	def animals_request(self):
		connection = create_server_connection("localhost", "root", "", "dati animali")	#creazione della connessione
		results = read_query(connection, "SELECT id, type FROM animals")				#esecuzione della query
		for result in results:
			res = ""
			for element in result:														#tutto quello dentro il for serve per la formattazione dei dati
				res = res + " " + str(element)
			print(res)
			self.clientMQTT.publish('server/animals/response/','{:s}'.format(res))      #database-server risposta della liste dei dispositivi

	def animal_temp_request(self, id, date):
		connection = create_server_connection("localhost", "root", "", "dati animali")	#creazione della connessione
		id = (id)
		results = read_query(connection, "SELECT date, temperature FROM parameters WHERE ref_id = %s"%id)	#esecuzione della query
		res2 = date.split("-")
		for result in results:
			for element in result:
				if type(element) != float:
					res = str(element).split(" ")
					ora = res[1].split(":")
					if res2[1] == str(element.month) and res2[2] == str(element.year) and res2[0] == str(element.day):	#se i risultati della query corrispondono con il giorno scelto
						res = str(ora[0]) + " " + str(result[1])
						self.clientMQTT.publish('server/animals/temperature/%s' %id, '{:s}'.format(res)) 	#database-server richiesta della temperatura
						print(res)																			#di un animale in un particolare mese

	def animal_heart_rate_request(self, id, date):
		connection = create_server_connection("localhost", "root", "", "dati animali")	#creazione della connessione
		id = (id)
		results = read_query(connection, "SELECT date, heart_rate FROM parameters WHERE ref_id = %s"%id)	#esecuzione della query
		res2 = date.split("-")
		for result in results:
			for element in result:
				if type(element) != float:
					res = str(element).split(" ")
					ora = res[1].split(":")
					if res2[1] == str(element.month) and res2[2] == str(element.year) and res2[0] == str(element.day):	#se i risultati della query corrispondono con il giorno scelto
						res = str(ora[0]) + " " + str(result[1])
						self.clientMQTT.publish('server/animals/heartRate/%s'%id,'{:s}'.format(res))	#database-server richiesta della frequenza cardiaca
						print(res)																		#di un animale in un particolare mese

	def animal_last_position_request(self, id):
		connection = create_server_connection("localhost", "root", "", "dati animali")	#creazione della connessione
		data = (id)
		results = read_query(connection, "SELECT last_latitude, last_longitude FROM animals WHERE id = %s"%data)	#esecuzione della query
		for result in results:
			res = ""
			for element in result:														#dentro il for, formattazione dei dati
				res = res + " " + str(element)
			self.clientMQTT.publish('server/animals/last_position/%s'%data, '{:s}'.format(res))			#database-server richiesta dell'ultima posizione
			print(res)																					#di un animale in un particolare mese

	def save_average(self, id, average):
		connection = create_server_connection("localhost", "root", "", "dati animali")	#creazione della connessione
		id = (id)
		averages = average.split(" ")
		execute_insert(connection, "INSERT INTO `parameters` (`ref_id`, `temperature`, `heart_rate`) VALUES (%s, %s, %s)", (id, float(averages[0]), float(averages[1])))	#esecuzione della query

	def save_last_position(self, id, position):
		connection = create_server_connection("localhost", "root", "", "dati animali")	#creazione della connessione
		id = (id)
		positions = position.split(" ")
		execute_query(connection, "UPDATE `animals` SET last_latitude = %s, last_longitude = %s WHERE id = %s" %(float(positions[0]), float(positions[1]), id))	#esecuzione della query

	def loop(self):
		while (True):
			pass

if __name__ == '__main__':
	br=Bridge()
	br.loop()