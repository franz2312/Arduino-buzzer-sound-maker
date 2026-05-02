# Arduino-music-maker
you could create your on musics and play them on the arduino!

This code needs a python3, tk, arduino ide sofware

----------------
How to use this?
----------------

1: First, flash the .ino file located in the folder named "arduino serial player" to your Arduino Uno/Nano.

2: Then run the Python script named app.py in the Arduino Music Maker folder.

3: After that, before you start your song, find the location of the Arduino (Example: if you are on Linux: tyyUSB0/ACM0, if you are on Windows: COM3/4)
and type it in the serial port section and after pressing the connect button, you're ready!

WARNING: Make sure the buzzer pin you select supports PWM; otherwise, problems may occur.

Pin 9 is selected by default (supports PWM).
