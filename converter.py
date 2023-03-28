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
#  pyinstaller --noconfirm --onefile --windowed --icon "C:/Users/CourtUser/Desktop/release/VoskGUI/icon.png" --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/blue-document-music.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/cross.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/eraser.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/ffmpeg.exe;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/ffprobe.exe;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/icon.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/main_window.ui;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/microphone.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/microphone--pencil.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/vosk-model-small-ru-0.22;vosk-model-small-ru-0.22/" --add-data "C:/Python38/Lib/site-packages/vosk;vosk/"  "C:/Users/CourtUser/Desktop/release/VoskGUI/converter.py"


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
    def __init__(self, model, text_edit, b1, b2, mic_chosen, split_channels):
        super(WorkerLive, self).__init__()
        self.model = model
        self.text_edit = text_edit
        self.stop_event = threading.Event()
        self.mic = mic_chosen
        self.split_channels = split_channels
        channels = 2 if split_channels else 1
        try:
            self.stream = pyaudio.PyAudio().open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=16000,
                input=True,
                input_device_index=self.mic,
                frames_per_buffer=2000)
        except Exception:
            [i.append('Не удается организовать чтение с выбранных устройств, проверьте подключение') for i in self.text_edit]
            self.stream = None
        self.rec = KaldiRecognizer(self.model, 16000)
        self.b1 = b1
        self.b2 = b2

    def run(self):
        if self.stream is None:
            return
        self.b1.setDisabled(True)
        self.b2.setDisabled(True)
        [i.append('Распознавание с микрофона началось\n') for i in self.text_edit]
        while True:
            if self.stop_event.is_set():
                [i.append('\nРаспознавание было остановлено пользователем.') for i in self.text_edit]
                return
            data = self.stream.read(2000)
            if self.split_channels:
                # получаем данные из левого канала
                data_left = data[0::2]
                if self.rec.AcceptWaveform(data_left):
                    result = json.loads(self.rec.Result())
                    text = result['text']
                    if text != '':
                        self.text_edit[0].append(text)
                # получаем данные из правого канала
                data_right = data[1::2]
                if self.rec.AcceptWaveform(data_right):
                    result = json.loads(self.rec.Result())
                    text = result['text']
                    if text != '':
                        self.text_edit[1].append(text)

            elif self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.Result())
                text = result['text']
                if text != '':
                    [i.append(text) for i in self.text_edit]

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
        self.mic_chosen = {}
        self.threads = {}
        self.split_channels = False
        self.show()

    def process_file(self):
        file_dialog = QFileDialog(self)
        filename, _ = file_dialog.getOpenFileName(None, "Выберите аудиофайл", "", "Audio Files (*.wav *.mp3)")
        if not filename:
            return
        sr = self.combo_box.currentText()
        worker_thread = WorkerFile(filename, self.model, self.text_edit, sr, self.process_button, self.rec_button)
        self.stop_button.clicked.connect(worker_thread.stop)
        worker_thread.start()

    def process_live(self):
        if self.mic_chosen:
            mow = TextMultiOutputWindow(self, self.mic_chosen, self.split_channels)
            for micidx, micname in self.mic_chosen.items():
                text_field = [mow.text_fields[str(micidx) + '_L'], mow.text_fields[str(micidx) + '_R']] if self.split_channels else [mow.text_fields[micidx]]
                self.threads[micidx] = WorkerLive(self.model, text_field, self.process_button, self.rec_button, micidx, self.split_channels)
                self.stop_button.clicked.connect(self.threads[micidx].stop)
                self.threads[micidx].start()
        else:
            self.threads[0] = WorkerLive(self.model, [self.text_edit], self.process_button, self.rec_button, None, self.split_channels)
            self.stop_button.clicked.connect(self.threads[0].stop)
            self.threads[0].start()

    def choose_mics_window(self):
        MicrophoneSelectionWindow(self)

    def closeEvent(self, event):
        for th in list(self.threads.values()):
            th.stop()
        QApplication.quit()
        event.accept()


class TextMultiOutputWindow(QDialog):
    def __init__(self, parent, field_names, split_channels):
        super().__init__(parent=parent)
        self.setWindowTitle('Помикрофонный вывод')
        # создаем словарь для хранения текстовых полей
        self.text_fields = {}
        self.setWindowIcon(QIcon(resource_path('icon.png')))
        # создаем макет вертикального размещения
        layout = QVBoxLayout()
        channels = ['_L', '_R']

        # для каждого переданного имени поля создаем текстовое поле и добавляем его на макет
        for idx, name in field_names.items():
            if split_channels:
                for ch in channels:
                    label = QLabel(name + ch + ":")
                    text_field = QTextEdit()
                    text_field.setReadOnly(True)
                    self.text_fields[str(idx)+ch] = text_field
                    layout.addWidget(label)
                    layout.addWidget(text_field)
            else:
                label = QLabel(name + ":")
                text_field = QTextEdit()
                text_field.setReadOnly(True)
                self.text_fields[idx] = text_field
                layout.addWidget(label)
                layout.addWidget(text_field)

        # устанавливаем макет для окна
        self.setLayout(layout)
        self.show()


app = QApplication([])
window = MainWindow()
app.exec_()
