#include <Arduino.h>

const int MAX_NOTES = 256;
int noteFreqs[MAX_NOTES];
int noteDurations[MAX_NOTES];
int noteCount = 0;

int buzzerPin = 9;
int tempoGapMs = 90;
bool shouldStop = false;

void clearSong() {
  noteCount = 0;
  shouldStop = false;
}

void playLoadedSong() {
  for (int i = 0; i < noteCount; i++) {
    if (shouldStop) {
      noTone(buzzerPin);
      shouldStop = false;
      return;
    }

    int f = noteFreqs[i];
    int d = noteDurations[i];
    if (f <= 0) {
      noTone(buzzerPin);
      delay(d);
    } else {
      tone(buzzerPin, f, d);
      delay(d);
      noTone(buzzerPin);
    }
    delay(tempoGapMs);
  }
}

void parsePlayCommand(String line) {
  // Format: PLAY|<pin>|<gap>|<freq:dur,freq:dur,...>
  int p1 = line.indexOf('|');
  int p2 = line.indexOf('|', p1 + 1);
  int p3 = line.indexOf('|', p2 + 1);

  if (p1 < 0 || p2 < 0 || p3 < 0) {
    Serial.println("ERR:BAD_FORMAT");
    return;
  }

  int parsedPin = line.substring(p1 + 1, p2).toInt();
  int parsedGap = line.substring(p2 + 1, p3).toInt();
  String seq = line.substring(p3 + 1);

  if (parsedPin <= 0 || parsedGap <= 0 || seq.length() == 0) {
    Serial.println("ERR:BAD_VALUES");
    return;
  }

  buzzerPin = parsedPin;
  tempoGapMs = parsedGap;
  pinMode(buzzerPin, OUTPUT);

  clearSong();
  int start = 0;
  while (start < seq.length() && noteCount < MAX_NOTES) {
    int comma = seq.indexOf(',', start);
    if (comma < 0) comma = seq.length();

    String pair = seq.substring(start, comma);
    int colon = pair.indexOf(':');
    if (colon > 0) {
      int freq = pair.substring(0, colon).toInt();
      int dur = pair.substring(colon + 1).toInt();
      if (dur > 0) {
        noteFreqs[noteCount] = freq;
        noteDurations[noteCount] = dur;
        noteCount++;
      }
    }
    start = comma + 1;
  }

  Serial.print("OK:NOTES=");
  Serial.println(noteCount);
  playLoadedSong();
  Serial.println("OK:DONE");
}

void setup() {
  Serial.begin(115200);
  pinMode(buzzerPin, OUTPUT);
  Serial.println("READY");
}

void loop() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  if (line.equals("STOP")) {
    shouldStop = true;
    noTone(buzzerPin);
    Serial.println("OK:STOP");
    return;
  }

  if (line.startsWith("PLAY|")) {
    parsePlayCommand(line);
    return;
  }

  Serial.println("ERR:UNKNOWN_CMD");
}
