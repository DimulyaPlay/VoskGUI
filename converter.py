from PyQt5.QtWidgets import QApplication, QPushButton, QTextEdit, QFileDialog, QMainWindow, QComboBox
from PyQt5 import uic
from PyQt5.QtGui import QIcon
from vosk import Model, KaldiRecognizer
import os
import wave
import json
import threading
import subprocess
import pyaudio
from micselection import *
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
    def __init__(self, filename, model, text_edit, sr, b1, b2):
        super(WorkerFile, self).__init__()
        self.filename = filename
        self.model = model
        self.text_edit = text_edit
        self.sr = sr
        self.stop_event = threading.Event()
        self.b1 = b1
        self.b2 = b2

    def run(self):
        self.b1.setDisabled(True)
        self.b2.setDisabled(True)
        # if self.filename.lower().endswith(".mp3"):
        new_filename = os.path.splitext(self.filename)[0] + "_new.wav"
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
        self.b1.setDisabled(False)
        self.b2.setDisabled(False)

    def stop(self):
        self.stop_event.set()
        self.b1.setDisabled(False)
        self.b2.setDisabled(False)


class WorkerLive(threading.Thread):
    def __init__(self, model, text_edit, b1, b2, mic_chosen):
        super(WorkerLive, self).__init__()
        self.model = model
        self.text_edit = text_edit
        self.stop_event = threading.Event()
        self.mic_list = mic_chosen
        if not self.mic_list:
            print('default mic')
            try:
                self.stream = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=1, rate=16000, input=True,
                                                     frames_per_buffer=2000)
            except Exception as e:
                self.text_edit.append('Не обнаружен микрофон по умолчанию')
                self.stream = None
            self.rec = KaldiRecognizer(self.model, 16000)
        else:
            print('choosen mic')
            try:
                self.stream = [pyaudio.PyAudio().open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=index,
                    frames_per_buffer=2000) for index in self.mic_list]
            except Exception as e:
                self.text_edit.append('Не удается организовать чтение с выбранных устройств, проверьте подключение')
                self.stream = None
            self.rec = [KaldiRecognizer(self.model, 16000) for _ in range(len(self.mic_list))]
        self.b1 = b1
        self.b2 = b2

    def run(self):
        if self.stream is None:
            return
        self.b1.setDisabled(True)
        self.b2.setDisabled(True)
        self.text_edit.append('Распознавание с микрофона началось\n\n')
        while True:
            if self.stop_event.is_set():
                self.text_edit.append('\n\nРаспознавание было остановлено пользователем.')
                return
            if not self.mic_list:
                data = self.stream.read(2000)
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result['text']
                    self.text_edit.append(text)
            else:
                data = [device.read(2000) for device in self.stream]
                for recognizer, audio_data in zip(self.rec, data):
                    if recognizer.AcceptWaveform(audio_data):
                        result = json.loads(recognizer.Result())
                        text = result['text']
                        self.text_edit.append(text)

    def stop(self):
        self.stop_event.set()
        self.b1.setDisabled(False)
        self.b2.setDisabled(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path('main_window.ui'), self)
        self.setWindowTitle("Распознавание речи. Vosk RUS recognition GUI by Dmitry Sosnin")
        self.setWindowIcon(QIcon(resource_path('icon.png')))
        self.text_edit = self.findChild(QTextEdit, 'textEdit')
        self.combo_box = self.findChild(QComboBox, 'comboBox')
        self.combo_box.addItems(['4000', '8000', '16000', 'Исходный Samplerate'])
        self.process_button = self.findChild(QPushButton, 'pushButton_fromFile')
        self.process_button.clicked.connect(self.process_file)
        self.rec_button = self.findChild(QPushButton, 'pushButton_fromMic')
        self.rec_button.clicked.connect(self.process_live)
        self.stop_button = self.findChild(QPushButton, 'pushButton_stop')
        self.choose_mics = self.findChild(QPushButton, 'pushButton_chooseMic')
        self.choose_mics.clicked.connect(self.choose_mics_window)
        clear_button = self.findChild(QPushButton, 'pushButton_clear')
        clear_button.clicked.connect(lambda: self.text_edit.clear())
        self.model = Model(resource_path("vosk-model-small-ru-0.22"))
        self.mic_chosen = []
        self.show()

    def process_file(self):
        print(self.mic_chosen)
        file_dialog = QFileDialog(self)
        filename, _ = file_dialog.getOpenFileName(None, "Выберите аудиофайл", "", "Audio Files (*.wav *.mp3)")
        if not filename:
            return
        sr = self.combo_box.currentText()
        worker_thread = WorkerFile(filename, self.model, self.text_edit, sr, self.process_button, self.rec_button)
        self.stop_button.clicked.connect(worker_thread.stop)
        worker_thread.start()

    def process_live(self):
        worker_thread = WorkerLive(self.model, self.text_edit, self.process_button, self.rec_button, self.mic_chosen)
        self.stop_button.clicked.connect(worker_thread.stop)
        worker_thread.start()

    def choose_mics_window(self):
        mw = MicrophoneSelectionWindow(self)

    def closeEvent(self, event):
        QApplication.quit()
        event.accept()


app = QApplication([])
window = MainWindow()
app.exec_()
