import serial
import serial.tools.list_ports
import configparser
import paho.mqtt.client as mqtt
import struct
import time                                              #libreria importata per temporizzare alcune operazioni

class Bridge():

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.setupSerial()
        self.setupMQTT()
        self.temp = 0.0                                             #variabile in cui si salva l'ultima temperatura ricevuta
        self.freq = 0.0                                             #variabile in cui si salva l'ultima frequenza ricevuta
        self.a = False                                              #serve per regolare la frequenza di invio di eventuali errori
        self.tl = False                                             #serve per regolare la frequenza di invio di temperatura bassa
        self.hl = False                                             #serve per regolare la frequenza di invio di frequenza bassa
        self.th = False                                             #serve per regolare la frequenza di invio di temperatura alta
        self.hh = False                                             #serve per regolare la frequenza di invio di frequenza alta
        self.time = time.time()                                     #serve per regolare la frequenza di invio di eventuali errori
        self.timer = 10                                             #intervallo di tempo tra due invii

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

        self.clientMQTT.subscribe("alarm/send/1111")            #server-bracciale accensione o spegnimento allarme

    def on_message(self, client, userdata, msg):
        print(msg.topic + " " + str(msg.payload))

        if(msg.topic=="alarm/send/1111" and str(msg.payload) == "b'OFF'" ):
            self.ser.write(bytes('F', 'utf-8'))                                 #scrive sulla seriale il carattere
        if (msg.topic == "alarm/send/1111" and str(msg.payload) == "b'ON'"):
            self.ser.write(bytes('N', 'utf-8'))                                 #scrive sulla seriale il carattere

    def loop(self):
        # infinite loop for serial managing
        while (True):
            # look for a byte from serial
            if not self.ser is None:

                if self.ser.in_waiting > 0:
                    # data available from the serial port
                    lastchar = self.ser.read(1)
                    if lastchar == b'\xfe':  # EOL
                        self.useData
                        self.inbuffer = []
                    else:
                        # append
                        self.inbuffer.append(lastchar)

    @property
    def useData(self):
        # I have received a packet from the serial port. I can use it
        if len(self.inbuffer) < 3:  # at least header, size, footer
            return False
        # split parts
        if self.inbuffer[0] != b'\xff':
            return False
        numval = int.from_bytes(self.inbuffer[1], byteorder='little')       #leggo dalla seriale il codice grazie alla quale capisco che tipo di dato ho ricevuto
        strval = "errore"
        if (numval == 1):                                                   #1 codice temperatura
            [val] = struct.unpack('f', b''.join(self.inbuffer[2:6]))        #leggo il valore dalla seriale
            strval = str(round(val, 1))
            self.clientMQTT.publish('server/temperature/1111', '{:s}'.format(strval))   #bracciale-server temperatura in tempo reale
            self.temp = float(strval)                                       #aggiorno il valore corrente della temperatura
        elif (numval == 2):                                                 #2 codice latitudine
            [val] = struct.unpack('f', b''.join(self.inbuffer[2:6]))        #leggo il valore dalla seriale
            strval = str(val)
            self.clientMQTT.publish('server/gps/lat/1111', '{:s}'.format(strval))   #bracciale-server latitudine in tempo reale
        elif (numval == 3):                                                 #3 codice longitudine
            [val] = struct.unpack('f', b''.join(self.inbuffer[2:6]))        #leggo il valore dalla seriale
            strval = str(val)
            self.clientMQTT.publish('server/gps/lon/1111', '{:s}'.format(strval))   #bracciale-server longitudine in tempo reale
        elif (numval == 4):                                                 #4 codice frequenza cardiaca
            [val] = struct.unpack('f', b''.join(self.inbuffer[2:6]))        #leggo il valore dalla seriale
            strval = str(round(val, 1))
            self.clientMQTT.publish('server/heart_rate/1111', '{:s}'.format(strval))#bracciale-server frequenza cardiaca in tempo reale
            self.freq = float(strval)                                       #aggiorno il valore corrente della temperatura
        elif (numval == 5):                                                 #5 codice stato allarme
            val = int.from_bytes(self.inbuffer[2], byteorder='little')      #leggo il valore dalla seriale
            if val:
                self.clientMQTT.publish('server/alarm/rec/1111', 'ON')      #bracciale-server stato allarme in tempo reale
            else:
                self.clientMQTT.publish('server/alarm/rec/1111', 'OFF')     #bracciale-server stato allarme in tempo reale
        elif (numval == 99):                                                #99 codice errore temperatura
            self.clientMQTT.publish('server/alarm/1111', 'Temperature error')   #bracciale-server eventuali errori per allarmare in tempo reale
        elif (numval == 98):                                                #98 codice errore gps
            self.clientMQTT.publish('server/alarm/1111', 'Gps error')           #bracciale-server eventuali errori per allarmare in tempo reale

        if self.temp < 10 or self.temp > 45 or self.freq < 20 or self.freq > 200:   #controllo se ci sono valori fuori range
            self.ser.write(bytes('N', 'utf-8'))                                     #scrivo nella seriale per attivare l'allarme
            self.a = True                                                           #true quando c'è un qualsiasi valore fuori range
            time1 = time.time()
            if time1 -self.time >= self.timer:                                      #se è passato un tempo >= a self.timer reimposto tutti i booleani
                self.time = time1
                self.tl = False
                self.hl = False
                self.th = False
                self.hh = False
            if self.temp < 10:
                if self.tl == False:                                                #self.tl serve per non far inviare continuamente l'errore
                    self.clientMQTT.publish('server/alarm/1111', "Temperature low") #bracciale-server eventuali errori per allarmare in tempo reale
                    self.tl = True
            else:
                self.tl = False
            if self.temp > 45:
                if self.th ==  False:                                               #self.th serve per non far inviare continuamente l'errore
                    self.clientMQTT.publish('server/alarm/1111', "Temperature high")#bracciale-server eventuali errori per allarmare in tempo reale
                    self.th = True
            else:
                self.th = False
            if self.freq < 20:
                if self.hl == False:                                                #self.hl serve per non far inviare continuamente l'errore
                    self.clientMQTT.publish('server/alarm/1111', "HeartRate low")   #bracciale-server eventuali errori per allarmare in tempo reale
                    self.hl = True
            else:
                self.hl = False
            if self.freq > 200:
                if self.hh == False:                                                #self.hh serve per non far inviare continuamente l'errore
                    self.clientMQTT.publish('server/alarm/1111', "HeartRate high")  #bracciale-server eventuali errori per allarmare in tempo reale
                    self.hh = True
            else:
                self.hh = False
        elif self.a == True:
            self.ser.write(bytes('F', 'utf-8'))
            self.a = False

if __name__ == '__main__':
    br = Bridge()
    br.loop()
