#include <LiquidCrystal.h>    //libreria utile per lo schermo lcd
#include <LinkedList.h>       //libreria utile per il salvataggio dei vari allarmi

#define RED 7                 //definisco il pin del led rosso
#define GREEN A0              //definisco il pin del led verde
#define BLUE 8                //definisco il pin del led blu
#define BUZZ A1               //definisco il pin del buzzer

const int rs = 12, en = 11, d4 = 5, d5 = 4, d6 = 3, d7 = 2;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);                  //creazione dell'oggetto LinquidCrystal impostando i vari pin

char dato ;
String msg = "" ;
bool aut = false ;                          

typedef struct {                                            //struttura dati che definisce un allarme
  String id ;
  String error ;
} alarm ;

LinkedList<alarm> lista = LinkedList<alarm>() ;             //creazione della LinkedList
alarm temp ;                                                //variabile temporanea utilizzata per gli allarmi

int iCurrentMsg;                                            //variabili utili alla 
long timeLastSwtichLCD;                                     //temporizzazione degli allarmi 
int iLastSize;                                              //sullo schermo lcd

void setup() {

  Serial.begin(9600) ;
  randomSeed(analogRead(A0));   //parte di setup per led rgb
  lcd.begin(16, 2);             //setup del numero di colonne e di righe dello schermo lcd
  pinMode(GREEN, OUTPUT) ;
  pinMode(BUZZ, OUTPUT) ;

  iCurrentMsg=0;
  timeLastSwtichLCD=millis();
  iLastSize=0;
}

void loop() {
 
  while(Serial.available()>0){                      //finchè c'è almeno un byte sulla seriale
    dato = Serial.read();                           //leggo il valore dalla seriale
    if(dato != '-' && dato != '_' && dato != 'N' && dato != 'F') 
      msg += dato ;
    if(dato == '-') {
      temp.id = msg ;
      msg = "" ;
    }
    if(dato == 'F') { 
      for(int i = 0; i < lista.size(); ++i) {
        alarm a = lista.get(i) ;
        if(a.id == temp.id) {
          lista.remove(i) ;
        }
      }
      temp.id = "" ;
      temp.error = "" ;
      msg = "" ;
    }
    if(dato == 'N') {
      temp.error = "ALLARME UTENTE" ; 
      bool b = false ;
      for(int i = 0; i < lista.size(); ++i) {
        alarm a = lista.get(i) ;
        if(a.id == temp.id) {
          b = true ;
        }
      }
      if(!b) {
        lista.add(temp) ;
      }
      temp.id = "" ;
      temp.error = "" ;
      msg = "" ;
    }
    if(dato == '_') {
      temp.error = msg ;
      bool b = false ;
      for(int i = 0; i < lista.size(); ++i) {
        alarm a = lista.get(i) ;
        if(a.id == temp.id && a.error == temp.error) {
          b = true ;
        }
      }
      if(!b) {
        lista.add(temp) ;
      }
      temp.id = "" ;
      temp.error = "" ;
      msg = "" ;
    }
  } 
 
  UpdateLCD();          //funzione che stampa i vari allarmi
}

void UpdateLCD() {

  if ((iLastSize!=lista.size()) ||  ( millis() > timeLastSwtichLCD + 1000)) { //1000 - un secondo 
    // la lista è cambiata oppure è scaduto il tempo: aggiorniamo
     timeLastSwtichLCD  =millis();
     iLastSize=lista.size();
     
    if(lista.size() != 0){        
      iCurrentMsg = (iCurrentMsg +1) % lista.size();
      
      analogWrite(RED, 256);
      analogWrite(GREEN, 0);
      analogWrite(BLUE, 0);
      digitalWrite(BUZZ, HIGH) ;

      // recupero elemento iCurrentMsg
        alarm a = lista.get(iCurrentMsg) ;
        lcd.clear() ;
        lcd.setCursor(0, 0);
        lcd.print(a.id) ;
        lcd.setCursor(0, 1);
        lcd.print(a.error) ;
    } 
    else {  
      lcd.clear() ;
      analogWrite(RED, 0);
      analogWrite(GREEN, 256);
      analogWrite(BLUE, 0);
      digitalWrite(BUZZ, LOW) ;
    }
  }
}
