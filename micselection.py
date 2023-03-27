from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QCheckBox, QPushButton, QVBoxLayout, QDialog
from PyQt5.QtCore import Qt
import pyaudio


class MicrophoneSelectionWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
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
        self.apply_button = QPushButton("Применить")
        self.apply_button.clicked.connect(self.apply_settings)
        # Размещение виджетов на окне
        vbox = QVBoxLayout()
        vbox.addWidget(self.description)
        for checkbox in self.mic_checkboxes:
            vbox.addWidget(checkbox)
        vbox.addWidget(self.apply_button)
        self.setLayout(vbox)

    def apply_settings(self):
        # Сбор выбранных микрофонов и их индексов
        selected_mics = []
        for checkbox in self.mic_checkboxes:
            if checkbox.isChecked():
                selected_mics.append(checkbox.index)
        self.parent.mic_chosen = selected_mics
        # Закрытие окна и возврат списка индексов микрофонов
        self.close()




