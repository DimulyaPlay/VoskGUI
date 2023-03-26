from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QFileDialog, QVBoxLayout, QComboBox
from PyQt5.QtGui import QIcon
from vosk import Model, KaldiRecognizer, SetLogLevel
import os
import wave
import json
import threading
import subprocess
import pyaudio
import queue
#  pyinstaller --noconfirm --onefile --windowed --icon "C:/Users/dimas/VoskGUI/icon.png" --add-data "C:\Python38\Lib\site-packages\vosk;vosk" --add-data "C:/Users/dimas/VoskGUI/ffmpeg.exe;." --add-data "C:/Users/dimas/VoskGUI/ffprobe.exe;." --add-data "C:/Users/dimas/VoskGUI/icon.png;." --add-data "C:/Users/dimas/VoskGUI/vosk-model-small-ru-0.22;vosk-model-small-ru-0.22/"  "C:/Users/dimas/VoskGUI/converter.py"


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class WorkerFile(threading.Thread):
    def __init__(self, filename, model, text_edit, sr):
        super(WorkerFile, self).__init__()
        self.filename = filename
        self.model = model
        self.text_edit = text_edit
        self.sr = sr
        self.stop_event = threading.Event()

    def run(self):
        if self.filename.endswith(".mp3"):
            new_filename = os.path.splitext(self.filename)[0] + ".wav"
            subprocess.call(['ffmpeg', '-y', '-i', self.filename, new_filename], creationflags=subprocess.CREATE_NO_WINDOW)
            self.filename = new_filename
        wf = wave.open(self.filename, "rb")
        rec = KaldiRecognizer(self.model, wf.getframerate())
        if self.sr == 'Исходный Samplerate':
            self.sr = wf.getframerate()
        else:
            self.sr = int(self.sr)
        while True:
            if self.stop_event.is_set():
                self.text_edit.append('\n\nРаспознавание было остановлено пользователем.')
                return
            data = wf.readframes(self.sr)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result['text']
                self.text_edit.append(text)
        result = json.loads(rec.FinalResult())
        text = result['text']
        self.text_edit.append(text)
        self.text_edit.append('\n\nРаспознавание завершено.')

    def stop(self):
        self.stop_event.set()
        process_button.setDisabled(False)
        rec_button.setDisabled(False)


class WorkerLive(threading.Thread):
    def __init__(self, model, text_edit):
        super(WorkerLive, self).__init__()
        self.model = model
        self.text_edit = text_edit
        self.stop_event = threading.Event()
        self.rec = KaldiRecognizer(self.model, 16000)
        self.q = queue.Queue()
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=2000)

    def run(self):
        self.text_edit.append('Распознавание с микрофона началось\n\n')
        while True:
            if self.stop_event.is_set():
                self.text_edit.append('\n\nРаспознавание было остановлено пользователем.')
                return
            data = self.stream.read(2000)
            if len(data) == 0:
                break
            if self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.Result())
                text = result['text']
                self.text_edit.append(text)

    def stop(self):
        self.stop_event.set()
        process_button.setDisabled(False)
        rec_button.setDisabled(False)


def process_file():
    file_dialog = QFileDialog()
    filename, _ = file_dialog.getOpenFileName(None, "Выберите аудиофайл", "", "Audio Files (*.wav *.mp3)")
    if not filename:
        return
    model = Model(resource_path("vosk-model-small-ru-0.22"))
    sr = combo_box.currentText()
    worker_thread = WorkerFile(filename, model, text_edit, sr)
    stop_button.clicked.connect(worker_thread.stop)
    worker_thread.start()


def process_live():
    process_button.setDisabled(True)
    rec_button.setDisabled(True)
    model = Model(resource_path("vosk-model-small-ru-0.22"))
    worker_thread = WorkerLive(model, text_edit)
    stop_button.clicked.connect(worker_thread.stop)
    worker_thread.start()


def closeEvent(self, event):
    QApplication.quit()
    event.accept()


app = QApplication([])
window = QWidget()
window.setWindowTitle("Распознавание речи. Vosk RUS recognition GUI by Dmitry Sosnin")
window.setWindowIcon(QIcon(resource_path('icon.png')))
window.closeEvent = closeEvent

text_edit = QTextEdit()
text_edit.setReadOnly(True)

combo_box = QComboBox()
combo_box.addItems(['4000', '8000', '16000', 'Исходный Samplerate'])

process_button = QPushButton("Обработать файл")
process_button.clicked.connect(process_file)

rec_button = QPushButton("С микрофона")
rec_button.clicked.connect(process_live)

stop_button = QPushButton("Остановить")

clear_button = QPushButton('Очистить вывод')
clear_button.clicked.connect(lambda: text_edit.clear())

layout = QVBoxLayout()
layout.addWidget(text_edit)
layout.addWidget(combo_box)
layout.addWidget(process_button)
layout.addWidget(rec_button)
layout.addWidget(stop_button)
layout.addWidget(clear_button)

window.setLayout(layout)
window.show()
app.exec_()
