#include <TinyGPS++.h>            //libreria per il gps
#include <SoftwareSerial.h>       //libreria per il gps
#include <OneWire.h>              //libreria per il sensore di temperatura
#include <DallasTemperature.h>    //libreria per il sensore di temperatura

#define BUZZ 5                    //definisco il pin del buzzer
#define ONE_WIRE_BUS 6            //definisco il pin del sensore di temperatura
#define R 7                       //definisco il pin del led rosso
#define G 8                       //definisco il pin del led verde
#define B 9                       //definisco il pin del led blu

OneWire oneWire(ONE_WIRE_BUS) ;
DallasTemperature sensors(&oneWire) ;

static const int TXPin = 4, RXPin = 3;
static const uint32_t GPSBaud = 9600;

// Oggetto TinyGPS++
TinyGPSPlus gps;

// Connessione seriale al dispositivo gps
SoftwareSerial ss(RXPin, TXPin);
bool allarme= false;                //stato allarme
bool aUt = false;                   //true se è attivo l'allarme utente
int cod = 0;                        //codice del dato da inviare
char led ;
bool state = true ;                 //stato allarme in tempo reale
bool t = false ;                    //stato sensore di temperatura
//per convertire float in binario e viceversa
typedef union {
  float floattante;
  byte binary[4];
} binaryFloat;

binaryFloat lat;                    //valore della latitudine del gps
binaryFloat lon;                    //valore della longitudine del gps
binaryFloat pulse;                  //valore del sensore di frequenza cardiaca
binaryFloat temp;                   //valore del sensore di temperatura

void setup() {
  
  Serial.begin(9600);
  ss.begin(GPSBaud);
  sensors.begin() ;
  pinMode(BUZZ, OUTPUT) ;     //settaggio del pin per il buzzer
  digitalWrite(BUZZ, LOW);    
  randomSeed(analogRead(A1)); //setup per il led
  pinMode(A0, INPUT);         //pin a cui è collegato il sensore della frequenza cardiaca
}

void loop() {

  if(Serial.available() > 0) {      //se c'è un byte all'interno della seriale
    led = Serial.read();            //leggi il byte
    if(led == 'N' ) {
      allarme = true ;
      aUt = true ; 
    } 
    else if(led=='F' && aUt == true) {
      allarme=false;
      aUt=false;
      cod=0;
    }
  }

  while (ss.available() > 0) {
    if (gps.encode(ss.read())) {
      gpsFunction() ;                 //funzione che legge i valori del gps
    }
  }

  printTemperature() ;                //funzione che legge i valori del sensore di temperatura

  heartRate() ;                       //funzione che legge i valori del sensore della frequenza cardiaca

  problemi(allarme, cod) ;            //funzione che determina se si deve attivare l'allarme e invia il codice del problema
  
  if(timer(1000)) {                   //invio temporizzato dei dati
    invio() ;                         //funzione che determina l'invio dei dati
  }
}

void printTemperature() {

  sensors.requestTemperatures() ;
  float temperature= sensors.getTempCByIndex(0) ;
  temp.floattante=temperature;                        //leggo il valore della temperatura

  if(temp.floattante != DEVICE_DISCONNECTED_C) {      //se il sensore non è disconnesso
    t = false ;  
    if(allarme == true && aUt== false)                //se l'allarme è acceso per un errore
      allarme = false;                                //lo spengo
      cod = 0 ;
  }
  else {                                              //altrimenti attivo l'allarme con il codice dell'errore del sensore di temperatura
  //allarme e led rosso
    allarme = true;
    aUt = false ;
    if(state && !t) {
      state = false ;
      t = true ;
    }  
    cod=99;                                           //codice dell'errore del sensore di temperatura
  }
}

void gpsFunction() {

  if (gps.location.isValid()) {                       //se la locazione è valida
    lat.floattante= gps.location.lat();               //leggo il valore della latitudine
    lon.floattante= gps.location.lng();               //leggo il valore della longitudine
  }
  //qui si dovrebbe far mandare l'errore per la non connessione con il satellite però per comodità si manda un valore di default
  else {
    lat.floattante= 44.62914473592921;               
    lon.floattante= 10.948843084508601;
  }
}

void heartRate() {

  int sum = 0;
  for (int i = 0; i < 50; i++)
    sum += analogRead(A0);                            //sommo il valore della frequenza
  pulse.floattante = sum / 50.00 ;                    //faccio una media e prendo il valore
}

void problemi(bool allarme, int cod) {

  if(state != allarme ) {                             //se lo stato dell'allarme è diverso dall'effettivo stato del bracciale
    Serial.write(0xFF) ;
    Serial.write(5);                                  //invio con il codice 5
    Serial.write(allarme);                            //invio lo stato dell'allarme  
		Serial.write(0xFE) ;
    if(allarme) {                                     //se l'allarme è attivo
      digitalWrite(BUZZ, HIGH) ;                      //attivo il buzzer
      analogWrite(R, 256);                            //imposto il led rosso
      analogWrite(G, 0);
      analogWrite(B, 0);
      Serial.write(0xFF) ;
      Serial.write(cod);                              
      Serial.write(cod);    
		  Serial.write(0xFE) ;
    }
    else {
      digitalWrite(BUZZ, LOW);                        //disattivo il buzzer
      analogWrite(R, 0);
      analogWrite(G, 256);                            //imposto il led verde
      analogWrite(B, 0);
    }
  state = allarme ;
  }
}
void invio() {

  //manda la latitudine su seriale con codice 2
  Serial.write(0xFF) ;
  Serial.write(2);
  Serial.write(lat.binary, 4) ; 
  Serial.write(0xFE) ;
  //manda la longitudine su seriale con codice 3
  Serial.write(0xFF) ;
  Serial.write(3);
  Serial.write(lon.binary, 4) ;
  Serial.write(0xFE) ;

  if(temp.floattante != DEVICE_DISCONNECTED_C) {
    //manda la temperatura su seriale con codice 1
    Serial.write(0xFF) ;
    Serial.write(1);    
	  Serial.write(temp.binary, 4) ;
		Serial.write(0xFE) ;    
  }
  //manda la frequenza cardiaca su seriale con codice 4
  Serial.write(0xFF) ;
  Serial.write(4) ;
  Serial.write(pulse.binary, 8) ;
  Serial.write(0xFE) ;
}

int timer(unsigned long int time) {

  static unsigned long int t1, dt ;
  int ret = 0 ;
  dt = millis() - t1 ;
  if(dt >= time) {
    t1 = millis() ;
    ret = 1 ;
  }
  return ret ;
}