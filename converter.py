from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QFileDialog, QVBoxLayout
from PyQt5.QtGui import QIcon
from vosk import Model, KaldiRecognizer, SetLogLevel
import os
import wave
import json
import threading
import subprocess
#  pyinstaller --noconfirm --onefile --windowed --icon "C:/Users/dimas/VoskGUI/icon.png" --add-data "C:\Python38\Lib\site-packages\vosk;vosk" --add-data "C:/Users/dimas/VoskGUI/ffmpeg.exe;." --add-data "C:/Users/dimas/VoskGUI/ffprobe.exe;." --add-data "C:/Users/dimas/VoskGUI/icon.png;." --add-data "C:/Users/dimas/VoskGUI/vosk-model-small-ru-0.22;vosk-model-small-ru-0.22/"  "C:/Users/dimas/VoskGUI/converter.py"


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class WorkerThread(threading.Thread):
    def __init__(self, filename, model, text_edit):
        super(WorkerThread, self).__init__()
        self.filename = filename
        self.model = model
        self.text_edit = text_edit
        self.stop_event = threading.Event()

    def run(self):
        if self.filename.endswith(".mp3"):
            new_filename = os.path.splitext(self.filename)[0] + ".wav"
            subprocess.call(['ffmpeg', '-y', '-i', self.filename, new_filename])
            self.filename = new_filename
        wf = wave.open(self.filename, "rb")
        rec = KaldiRecognizer(self.model, wf.getframerate())
        while True:
            if self.stop_event.is_set():
                self.text_edit.append('\n\nРаспознавание было остановлено пользователем.')
                return
            data = wf.readframes(4000)
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


def process_file():
    file_dialog = QFileDialog()
    filename, _ = file_dialog.getOpenFileName(None, "Выберите аудиофайл", "", "Audio Files (*.wav *.mp3)")
    if not filename:
        return
    model = Model(resource_path("vosk-model-small-ru-0.22"))
    worker_thread = WorkerThread(filename, model, text_edit)
    stop_button.clicked.connect(worker_thread.stop)
    worker_thread.start()


app = QApplication([])
window = QWidget()
window.setWindowTitle("Распознавание речи. Vosk RUS recognition GUI by Dmitry Sosnin")
window.setWindowIcon(QIcon(resource_path('icon.png')))

text_edit = QTextEdit()
text_edit.setReadOnly(True)

process_button = QPushButton("Обработать")
process_button.clicked.connect(process_file)

stop_button = QPushButton("Остановить")

layout = QVBoxLayout()
layout.addWidget(text_edit)
layout.addWidget(process_button)
layout.addWidget(stop_button)

window.setLayout(layout)
window.show()
app.exec_()
