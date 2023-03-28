from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QCheckBox, QPushButton, QVBoxLayout, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import pyaudio
import os, sys


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class MicrophoneSelectionWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self.setWindowIcon(QIcon(resource_path('icon.png')))
        # Получение списка микрофонов с их индексами
        self.mic_dict = {}
        self.p = pyaudio.PyAudio()
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            host_api_info = self.p.get_host_api_info_by_index(dev["hostApi"])
            if dev['maxInputChannels'] > 0 and host_api_info["name"] == "MME":
                self.mic_dict[dev['index']] = dev['name'].encode('cp1251').decode('utf-8')
        self.initUI()
        self.show()

    def initUI(self):
        # Заголовок окна
        self.setWindowTitle("Выберите микрофоны")
        # Описание окна
        self.description = QLabel("Выберите микрофон(ы), которые хотите использовать:")
        self.description.setAlignment(Qt.AlignTop)
        # Чекбоксы для выбора микрофонов
        self.mic_checkboxes = []
        for index, name in self.mic_dict.items():
            checkbox = QCheckBox(name)
            checkbox.index = index  # сохраним индекс микрофона в самом виджете
            checkbox.setChecked(index in self.parent.mic_chosen)
            self.mic_checkboxes.append(checkbox)
        # Кнопка применения настроек
        self.split_channels = QCheckBox('Анализировать левый и правый каналы раздельно')
        self.apply_button = QPushButton("Применить")
        self.apply_button.clicked.connect(self.apply_settings)
        # Размещение виджетов на окне
        vbox = QVBoxLayout()
        vbox.addWidget(self.description)
        for checkbox in self.mic_checkboxes:
            vbox.addWidget(checkbox)
        vbox.addWidget(self.split_channels)
        vbox.addWidget(self.apply_button)
        self.setLayout(vbox)

    def apply_settings(self):
        # Сбор выбранных микрофонов и их индексов
        for checkbox in self.mic_checkboxes:
            if checkbox.isChecked():
                self.parent.mic_chosen[checkbox.index] = self.mic_dict[checkbox.index]
        self.parent.split_channels = self.split_channels.isChecked()
        # Закрытие окна и возврат списка индексов микрофонов
        self.close()




