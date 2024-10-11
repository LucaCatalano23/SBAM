import serial
import serial.tools.list_ports
import configparser
import paho.mqtt.client as mqtt
import struct

class Bridge():

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.setupSerial()
        self.setupMQTT()

    def setupSerial(self):
        # open serial port
        self.ser = None

        if self.config.get("Serial", "UseDescription", fallback=False):
            self.portname = self.config.get("Serial", "PortName", fallback="COM1")
        else:
            print("list of available ports: ")
            ports = serial.tools.list_ports.comports()

            for port in ports:
                print(port.device)
                print(port.description)
                if self.config.get("Serial", "PortDescription", fallback="arduino").lower() \
                        in port.description.lower():
                    self.portname = port.device

        try:
            if self.portname is not None:
                print("connecting to " + self.portname)
                self.ser = serial.Serial(self.portname, 9600, timeout=0)
        except:
            self.ser = None

        # self.ser.open()

        # internal input buffer from serial
        self.inbuffer = []

    def setupMQTT(self):
        self.clientMQTT = mqtt.Client()
        self.clientMQTT.on_connect = self.on_connect
        self.clientMQTT.on_message = self.on_message
        print("connecting to MQTT broker...")
        self.clientMQTT.connect(
            self.config.get("MQTT", "Server", fallback="localhost"),
            self.config.getint("MQTT", "Port", fallback=1883), 60)

        self.clientMQTT.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        self.clientMQTT.subscribe("custode/alarm/+")        #server-custode eventuali errori per allarmare in tempo reale
        self.clientMQTT.subscribe("custode/alarm/rec/+")    #server-custode stato allarme in tempo reale
        self.clientMQTT.subscribe("custode/alarm/send/+")   #server-custode spegnimento allarme

    def on_message(self, client, userdata, msg):
        print(msg.topic + " " + str(msg.payload))

        topic = msg.topic.split("/")    # si considera il topic senza l'id alla fine
        self.id = topic[-1]             # senza l'id alla fine e si memorizza
        top = str(msg.topic[0: -4])

        if top =="custode/alarm/" and self.id.isdigit():
            self.ser.write(bytes(self.id + "-" + str(msg.payload)[2 : -1] + "_", 'utf-8'))      #scrivo sulla seriale il messaggio d'errore
        if top == "custode/alarm/rec/" and self.id.isdigit() and str(msg.payload) == "b'OFF'":
            self.ser.write(bytes(self.id + "-" + "F", 'utf-8'))                                 #scrivo sulla seriale lo spegnimento dell'allarme
        if top == "custode/alarm/send/" and self.id.isdigit() and str(msg.payload) == "b'ON'":
            self.ser.write(bytes(self.id + "-" + "N", 'utf-8'))                                 #scrivo sulla seriale l'accensione dell'allarme utente

    def loop(self):
        # infinite loop for serial managing
        while (True):
            pass

if __name__ == '__main__':
    br = Bridge()
    br.loop()
