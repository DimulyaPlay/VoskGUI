from PyQt5.QtWidgets import QApplication, QPushButton, QTextEdit, QFileDialog, QMainWindow, QComboBox, QProgressBar
from PyQt5 import uic
from PyQt5.QtGui import QIcon
from vosk import Model, KaldiRecognizer
import os
import wave
import json
import threading
import subprocess
import pyaudio
import numpy as np
from micselection import *

#  pyinstaller --noconfirm --onefile --windowed --icon "C:/Users/dimas/VoskGUI/icon.png" --add-data "C:/Users/dimas/VoskGUI/about_ui.ui;." --add-data "C:/Users/dimas/VoskGUI/main_window.ui;." --add-data "C:/Users/dimas/VoskGUI/avatar.jpg;." --add-data "C:/Users/dimas/VoskGUI/blue-document-music.png;." --add-data "C:/Users/dimas/VoskGUI/cross.png;." --add-data "C:/Users/dimas/VoskGUI/eraser.png;." --add-data "C:/Users/dimas/VoskGUI/microphone.png;." --add-data "C:/Users/dimas/VoskGUI/microphone--pencil.png;." --add-data "C:/Users/dimas/VoskGUI/icon.png;." --add-data "C:/Users/dimas/VoskGUI/ffprobe.exe;." --add-data "C:/Users/dimas/VoskGUI/ffmpeg.exe;." --add-data "C:/Users/dimas/VoskGUI/vosk-model-small-ru-0.22;vosk-model-small-ru-0.22/" --add-data "C:/Python38/Lib/site-packages/vosk;vosk/"  "C:/Users/dimas/VoskGUI/converter.py"
#  pyinstaller --noconfirm --onefile --windowed --icon "C:/Users/CourtUser/Desktop/release/VoskGUI/icon.png" --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/avatar.jpg;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/blue-document-music.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/cross.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/eraser.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/ffmpeg.exe;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/ffprobe.exe;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/icon.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/main_window.ui;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/microphone.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/microphone--pencil.png;." --add-data "C:/Users/CourtUser/Desktop/release/VoskGUI/vosk-model-small-ru-0.22;vosk-model-small-ru-0.22/" --add-data "C:/Python38/Lib/site-packages/vosk;vosk/"  "C:/Users/CourtUser/Desktop/release/VoskGUI/converter.py"


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class WorkerFile(threading.Thread):
    def __init__(self, filename, model, text_edit, sr, b1, b2, progress_bar):
        super(WorkerFile, self).__init__()
        self.filename = filename
        self.model = model
        self.text_edit = text_edit
        self.sr = sr
        self.stop_event = threading.Event()
        self.b1 = b1
        self.b2 = b2
        self.progress_bar = progress_bar

    def run(self):
        self.b1.setDisabled(True)
        self.b2.setDisabled(True)
        self.new_filename = os.path.splitext(self.filename)[0] + "_new.wav"
        ffmpeg_args = ['ffmpeg', '-y', '-i', self.filename]
        if self.sr != 'Исходный Samplerate':
            ffmpeg_args.extend(['-ar', str(self.sr)])
        ffmpeg_args.append(self.new_filename)
        subprocess.call(ffmpeg_args, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            wf = wave.open(self.new_filename, "rb")
        except Exception as e:
            self.text_edit.append(str(e))
            return
        total_frames = wf.getnframes()
        self.sr = wf.getframerate()
        try:
            rec = KaldiRecognizer(self.model, wf.getframerate())
        except Exception as e:
            self.text_edit.append(str(e))
            return
        frames_ready = 0
        progress = 0
        while True:
            if self.stop_event.is_set():
                wf.close()
                try:
                    os.unlink(self.new_filename)
                except Exception as e:
                    self.text_edit.append(str(e))
                    pass
                self.text_edit.append('\nРаспознавание было остановлено пользователем.')
                return
            data = wf.readframes(self.sr)
            frames_ready += self.sr
            progress = frames_ready/total_frames*100
            self.progress_bar.setValue(int(progress))
            if len(data) == 0:
                break
            try:
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result['text']
                    if text != '':
                        self.text_edit.append(text)
            except:
                self.text_edit.append('Не удается передать данные в модель')
                break
        wf.close()
        try:
            os.unlink(self.new_filename)
        except Exception as e:
            self.text_edit.append(str(e))
            pass
        result = json.loads(rec.FinalResult())
        text = result['text']
        self.text_edit.append(text)
        self.text_edit.append('\nРаспознавание завершено.')
        self.b1.setDisabled(False)
        self.b2.setDisabled(False)
        self.progress_bar.setValue(0)

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
        channels = 1
        if split_channels:
            channels = 2
            self.rec2 = KaldiRecognizer(self.model, 16000)
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
                data = np.frombuffer(data, dtype=np.int16)
                left_channel = data[::2]
                right_channel = data[1::2]
                if self.rec.AcceptWaveform(left_channel.tobytes()):
                    result = json.loads(self.rec.Result())
                    text = result['text']
                    if text != '':
                        self.text_edit[0].append(text)
                # получаем данные из правого канала
                if self.rec2.AcceptWaveform(right_channel.tobytes()):
                    result = json.loads(self.rec2.Result())
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
        self.setWindowTitle("МАТ - Многоканальный автоматический транскрибитор. Vosk RUS GUI by Dmitry Sosnin")
        self.setWindowIcon(QIcon(resource_path('icon.png')))
        self.text_edit = self.findChild(QTextEdit, 'textEdit')
        self.text_edit.textChanged.connect(
            lambda fname=os.getcwd() + '\\' + 'default_mic.txt': write_to_txt(fname, self.text_edit))
        self.text_edit.dropEvent = self.process_file_from_drop
        self.progress_bar = self.findChild(QProgressBar, 'progressBar')
        self.combo_box = self.findChild(QComboBox, 'comboBox')
        self.combo_box.addItems(['16000', 'Исходный Samplerate'])
        self.process_button = self.findChild(QPushButton, 'pushButton_fromFile')
        self.process_button.clicked.connect(self.process_file)
        self.rec_button = self.findChild(QPushButton, 'pushButton_fromMic')
        self.rec_button.clicked.connect(self.process_live)
        self.stop_button = self.findChild(QPushButton, 'pushButton_stop')
        self.choose_mics = self.findChild(QPushButton, 'pushButton_chooseMic')
        self.choose_mics.clicked.connect(self.choose_mics_window)
        clear_button = self.findChild(QPushButton, 'pushButton_clear')
        clear_button.clicked.connect(lambda: self.text_edit.clear())
        donate_button = self.findChild(QPushButton, 'pushButton')
        donate_button.clicked.connect(lambda: AboutWindow(self))
        self.model = Model(resource_path("vosk-model-small-ru-0.22"))
        self.mic_chosen = {}
        self.threads = {}
        self.split_channels = False
        self.show()

    def process_file_from_button(self):
        file_dialog = QFileDialog(self)
        filename, _ = file_dialog.getOpenFileName(None, "Выберите аудиофайл",
                                                  "", )  # "Audio Files (*.wav *.mp3 *.wma *.m4a)"
        if filename:
            self.process_file(filename)

    def process_file_from_drop(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        print(files)
        self.process_file(files[0])

    def process_file(self, filename):
        sr = self.combo_box.currentText()
        self.worker_thread = WorkerFile(filename, self.model, self.text_edit, sr, self.process_button, self.rec_button, self.progress_bar)
        self.stop_button.clicked.connect(self.worker_thread.stop)
        self.worker_thread.start()

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
        try:
            os.unlink(self.worker_thread.new_filename)
        except Exception:
            pass
        for th in list(self.threads.values()):
            th.stop()
        QApplication.quit()
        event.accept()


def write_to_txt(fname, text_edit):
    with open(fname, 'w') as fle:
        fle.write(text_edit.toPlainText())


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
                    text_field.textChanged.connect(
                        lambda fname=os.getcwd() + '\\' + str(idx) + ch + '.txt': write_to_txt(fname, text_field))
                    text_field.setReadOnly(True)
                    self.text_fields[str(idx)+ch] = text_field
                    layout.addWidget(label)
                    layout.addWidget(text_field)
            else:
                label = QLabel(name + ":")
                text_field = QTextEdit()
                text_field.textChanged.connect(
                    lambda fname=os.getcwd() + '\\' + str(idx) + '.txt': write_to_txt(fname, text_field))
                text_field.setReadOnly(True)
                self.text_fields[idx] = text_field
                layout.addWidget(label)
                layout.addWidget(text_field)

        # устанавливаем макет для окна
        self.setLayout(layout)
        self.show()


class AboutWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)
        uic.loadUi(resource_path('about_ui.ui'), self)
        self.show()


app = QApplication([])
window = MainWindow()
app.exec_()
