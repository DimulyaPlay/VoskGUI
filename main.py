from vosk import Model, KaldiRecognizer
import sys
import json
import os
import time
import wave


#  https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
model = Model(r"C:\Users\CourtUser\Desktop\release\VoskGUI\vosk-model-small-ru-0.22")

wf = wave.open(r'test.wav', "rb")
rec = KaldiRecognizer(model, 16000)

result = ''
last_n = False

while True:
    data = wf.readframes(16000)
    if len(data) == 0:
        break

    if rec.AcceptWaveform(data):
        res = json.loads(rec.Result())

        if res['text'] != '':
            result += f" {res['text']}"
            last_n = False
        elif not last_n:
            result += '\n'
            last_n = True

res = json.loads(rec.FinalResult())
result += f" {res['text']}"

print(result)
