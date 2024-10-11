import configparser
import paho.mqtt.client as mqtt
import time                                 #libreria importata per temporizzare alcune operazioni

class Bridge:

    def __init__(self):
        self.id = None
        self.clientMQTT = None
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.setupMQTT()
        self.time_1 = time.time()                   #serve per l'invio temporizzato della temperatura
        self.time_2 = time.time()                   #serve per l'invio temporizzato della frequenza cardiaca
        self.time_3 = time.time()                   #serve per l'invio temporizzato della posizione
        self.timer = 30                             #intervallo di tempo tra due invii
        self.timer_gps = 21600                      #intervallo di tempo tra due richieste di salvataggi della posizione
        self.countTemp = {}                         #dizionario id-contatore...contatore riferito al numero di volte che arriva una temperatura
        self.sommaTemp = {}                         #dizionario id-somma...somma di tutte le temperature ricevute
        self.countBeat = {}                         #dizionario id-contatore...contatore riferito al numero di volte che arriva una frequenza cardiaca
        self.sommaBeat = {}                         #dizionario id-somma...somma di tutte le frequenza cardiaca ricevute
        self.lat = {}                               #dizionario id-latitudine

    def setupMQTT(self):
        self.clientMQTT = mqtt.Client()
        self.clientMQTT.on_connect = self.on_connect
        self.clientMQTT.on_message = self.on_message
        print("connecting to MQTT broker...")
        self.clientMQTT.connect(
            self.config.get("MQTT", "Server", fallback="localhost"),
            self.config.getint("MQTT", "Port", fallback=1883), 60)

        self.clientMQTT.loop_start()

    def on_connect(self, client, userdata, flags,  rc):
        print("Connected with result code " + str(rc))

        self.clientMQTT.subscribe("server/animals/")                #app-server richiesta della lista dei dispositivi
        self.clientMQTT.subscribe("server/animals/response/")       #database-server risposta della lista dei dispositivi
        self.clientMQTT.subscribe("server/temperature/+")           #bracciale-server temperatura in tempo reale
        self.clientMQTT.subscribe("server/heart_rate/+")            #bracciale-server frequenza cardiaca in tempo reale
        self.clientMQTT.subscribe("server/gps/+/+")                 #bracciale-server posizione in tempo reale (latitudine e longitudine)
        self.clientMQTT.subscribe("server/alarm/+")                 #bracciale-server eventuali errori per allarmare in tempo reale
        self.clientMQTT.subscribe("server/alarm/rec/+")             #bracciale-server stato allarme in tempo reale
        self.clientMQTT.subscribe("server/alarm/send/+")            #app-server accensione o spegnimento allarme
        self.clientMQTT.subscribe("server/animals/last_position/")  #app-server richiesta ultima posizione
        self.clientMQTT.subscribe("server/animals/last_position/+") #database-server risposta ultima posizione
        self.clientMQTT.subscribe("server/animals/temperature/")    #app-server richiesta della temperatura in un particolare mese
        self.clientMQTT.subscribe("server/animals/temperature/+")   #database-server risposta della temperatura in un particolare mese
        self.clientMQTT.subscribe("server/animals/heartRate/")      #app-server richiesta della frequenza cardiaca in un particolare mese
        self.clientMQTT.subscribe("server/animals/heartRate/+")     #database-server risposta della frequenza cardiaca in un particolare mese

    def on_message(self, client, userdata, msg):
        print(msg.topic + " " + str(msg.payload))

        if str(msg.topic) == "server/animals/" and str(msg.payload) == "b'request'":
            self.clientMQTT.publish('animals/', str(msg.payload)[2:-1])                         #server-database richiesta della lista dei dispositivi
        if str(msg.topic) == "server/animals/response/":
            self.clientMQTT.publish('animals/response/', str(msg.payload)[2:-1])                #server-app risposta della lista dei dispositivi

        topic = msg.topic.split("/")                                                            #si considera il topic senza l'id alla fine
        self.id = topic[-1]                                                                     #e si memorizza lo stesso
        top = str(msg.topic[0: -4])                                                             #in una variabile separata

        if top == "server/temperature/":
            if self.id not in self.countTemp:                                           #se l'id non è presente nei dizionari
                self.sommaTemp[self.id] = 0                                             #lo aggiungo assegnando
                self.countTemp[self.id] = 0                                             #come valore 0
            time1 = time.time()
            if time1 - self.time_1 >= self.timer:                                       #se è passato un tempo >= self.timer
                self.time_1 = time1
                self.sommaTemp[self.id] += float(str(msg.payload)[2:-1])                #sommo i valori corretti nei
                self.countTemp[self.id] += 1                                            #rispettivi dizionari
            self.clientMQTT.publish('temperature/%s' % self.id, str(msg.payload)[2:-1])         #server-app temperatura in tempo reale

        if top == "server/heart_rate/":
            if self.id not in self.countBeat:                                           #se l'id non è presente nei dizionari
                self.sommaBeat[self.id] = 0                                             #lo aggiungo assegnando
                self.countBeat[self.id] = 0                                             #come valore 0
            time2 = time.time()
            if time2 - self.time_2 >= self.timer:                                       #se è passato un tempo >= self.timer
                self.time_2 = time2
                self.sommaBeat[self.id] += float(str(msg.payload)[2:-1])                #sommo i valori corretti nei
                self.countBeat[self.id] += 1                                            #rispettivi dizionari
            self.clientMQTT.publish('heart_rate/%s' % self.id, str(msg.payload)[2:-1])          #server-app frequenza cardiaca in tempo reale

        if top == "server/gps/lat/":
            self.clientMQTT.publish('gps/lat/%s' % self.id, str(msg.payload)[2:-1])             #server-app latitudine in tempo reale
            self.lat[self.id] = str(msg.payload)[2:-1]                       #aggiorno il valore della latitudine di un particolare id nel dizionario
        if top == "server/gps/lon/":
            self.clientMQTT.publish('gps/lon/%s' % self.id, str(msg.payload)[2:-1])             #server-app longitudine in tempo reale
            time3 = time.time()
            if time3 - self.time_3 >= self.timer_gps:                                   #se è passato un tempo >= self.timer_gps
                self.clientMQTT.publish('last_position/', self.id + " " + self.lat[self.id] + " " + str(msg.payload)[2:-1]) #server-database richiesta salvataggio ultima posizione di un dispositivo
                self.time_3 = time3

        if top == "server/alarm/":
            self.clientMQTT.publish('alarm/%s' % self.id, str(msg.payload)[2:-1])               #server-app eventuali errori per allarmare in tempo reale
            self.clientMQTT.publish('custode/alarm/%s' % self.id, str(msg.payload)[2:-1])       #server-custode eventuali errori per allarmare in tempo reale
        if top == "server/alarm/rec/":
            self.clientMQTT.publish('alarm/rec/%s' % self.id, str(msg.payload)[2:-1])           #server-app stato allarme in tempo reale
            self.clientMQTT.publish('custode/alarm/rec/%s' % self.id, str(msg.payload)[2:-1])   #server-custode stato allarme in tempo reale
            self.clientMQTT.publish('notify/alarm/rec/', self.id + " " + str(msg.payload)[2:-1])#server-app notifiche allarme in tempo reale

        if top == "server/alarm/send/" and str(msg.payload) == "b'OFF'":
            self.clientMQTT.publish('alarm/send/%s' % self.id, 'OFF')                           #server-bracciale spegnimento allarme
        if top == "server/alarm/send/" and str(msg.payload) == "b'ON'":
            self.clientMQTT.publish('alarm/send/%s' % self.id, 'ON')                            #server-bracciale accensione allarme
            self.clientMQTT.publish('custode/alarm/send/%s' % self.id, 'ON')                    #server-custode accensione allarme

        if msg.topic == "server/animals/last_position/" and str(msg.payload)[2:6].isdigit():
            self.clientMQTT.publish('animals/last_position/', str(msg.payload)[2:-1])           #server-database richiesta ultima posizione
        if top == "server/animals/last_position/":
            self.clientMQTT.publish('animals/last_position/%s' % self.id, str(msg.payload)[3:-1])#server-app risposta ultima posizione

        if msg.topic == "server/animals/temperature/" and str(msg.payload)[2: 6].isdigit():
            self.clientMQTT.publish('animals/temperature/', str(msg.payload)[2:-1])             #server-database richiesta della temperatura in un particolare mese
        if top == "server/animals/temperature/":
            self.clientMQTT.publish('animals/temperature/%s' % self.id, str(msg.payload)[2:-1]) #server-app risposta della temperatura in un particolare mese

        if msg.topic == "server/animals/heartRate/" and str(msg.payload)[2: 6].isdigit():
            self.clientMQTT.publish('animals/heartRate/', str(msg.payload)[2:-1])               #server-database richiesta della frequenza cardiaca in un particolare mese
        if top == "server/animals/heartRate/":
            self.clientMQTT.publish('animals/heartRate/%s' % self.id, str(msg.payload)[2:-1])   #server-app risposta della frequenza cardiaca in un particolare mese

    def loop(self):
        # infinite loop for serial managing
        while True:
            for key in self.countTemp:                                          #per ogni id nel dizionario
                if self.countTemp[key] >= 120:                                  #se sono stati ricevuti più di 120 valori
                    averageTemp = self.sommaTemp[key] / self.countTemp[key]     #si effettua la media
                    self.countTemp[key] = 0.0                                   #si azzera il valore del dizionario
                    self.sommaTemp[key] = 0.0                                   #si azzera il valore del dizionario
                    averageBeat = self.sommaBeat[key] / self.countBeat[key]     #si effettua la media
                    self.countBeat[key] = 0.0                                   #si azzera il valore del dizionario
                    self.sommaBeat[key] = 0.0                                   #si azzera il valore del dizionario
                    self.clientMQTT.publish('average/', key + " " + str(averageTemp) + " " + str(averageBeat)) #server-database richiesta salvataggio dati di un dispositivo

if __name__ == '__main__':
    br = Bridge()
    br.loop()
