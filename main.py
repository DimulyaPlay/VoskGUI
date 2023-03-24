from vosk import Model, KaldiRecognizer
import sys
import json
import os
import time
import wave
from pydub import AudioSegment
ffmpeg_path = 'ffmpeg.exe'
# загрузка файла MP3
# sound = AudioSegment.from_mp3(r"C:\Users\Dmitry\Downloads\X2Download.app - Финал Четырех Кубка России по баскетболу (192 kbps).mp3")
# AudioSegment.converter = ffmpeg_path
# # сохранение файла WAV
# sound.export("test.wav", format="wav")
#  https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
model = Model(r"vosk-model-small-ru-0.22")

wf = wave.open(r'test.wav', "rb")
sample_rate = wf.getframerate()
print(sample_rate)
rec = KaldiRecognizer(model, sample_rate)

result = ''
last_n = False
print('start recognition')
while True:
    data = wf.readframes(sample_rate)
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
