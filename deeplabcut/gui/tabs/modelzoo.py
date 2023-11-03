#
# DeepLabCut Toolbox (deeplabcut.org)
# © A. & M.W. Mathis Labs
# https://github.com/DeepLabCut/DeepLabCut
#
# Please see AUTHORS for contributors.
# https://github.com/DeepLabCut/DeepLabCut/blob/master/AUTHORS
#
# Licensed under GNU Lesser General Public License v3.0
#
from functools import partial

import deeplabcut
from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Signal, QTimer, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from deeplabcut.gui.components import (
    DefaultTab,
    VideoSelectionWidget,
    _create_label_widget,
    _create_grid_layout,
)
from deeplabcut.gui.utils import move_to_separate_thread
from deeplabcut.modelzoo.utils import parse_available_supermodels


class RegExpValidator(QRegularExpressionValidator):
    validationChanged = Signal(QRegularExpressionValidator.State)

    def validate(self, input_, pos):
        state, input_, pos = super().validate(input_, pos)
        self.validationChanged.emit(state)
        return state, input_, pos


class ModelZoo(DefaultTab):
    def __init__(self, root, parent, h1_description):
        super().__init__(root, parent, h1_description)
        self._val_pattern = QRegularExpression(r"(\d{3,5},\s*)+\d{3,5}")
        self._set_page()

    @property
    def files(self):
        return self.video_selection_widget.files

    def _set_page(self):
        self.main_layout.addWidget(_create_label_widget("Video Selection", "font:bold"))
        self.video_selection_widget = VideoSelectionWidget(self.root, self)
        self.main_layout.addWidget(self.video_selection_widget)

        model_settings_layout = _create_grid_layout(margins=(20, 0, 0, 0))

        section_title = _create_label_widget(
            "Supermodel Settings", "font:bold", (0, 50, 0, 0)
        )

        model_combo_text = QtWidgets.QLabel("Supermodel name")
        self.model_combo = QtWidgets.QComboBox()
        supermodels = parse_available_supermodels()
        self.model_combo.addItems(supermodels.keys())

        self.adapt_checkbox = QtWidgets.QCheckBox("Use video adaptation")
        self.adapt_checkbox.setChecked(True)

        pseudo_threshold_label = QtWidgets.QLabel("Pseudo-label confidence threshold")
        self.pseudo_threshold_spinbox = QtWidgets.QDoubleSpinBox(
            decimals=2,
            minimum=0.01,
            maximum=1.0,
            singleStep=0.05,
            value=0.1,
            wrapping=True,
        )
        self.pseudo_threshold_spinbox.setMaximumWidth(300)

        adapt_iter_label = QtWidgets.QLabel("Number of adaptation iterations")
        self.adapt_iter_spinbox = QtWidgets.QSpinBox()
        self.adapt_iter_spinbox.setRange(100, 10000)
        self.adapt_iter_spinbox.setValue(1000)
        self.adapt_iter_spinbox.setSingleStep(100)
        self.adapt_iter_spinbox.setGroupSeparatorShown(True)
        self.adapt_iter_spinbox.setMaximumWidth(300)

        model_settings_layout.addWidget(section_title, 0, 0)
        model_settings_layout.addWidget(model_combo_text, 1, 0)
        model_settings_layout.addWidget(self.model_combo, 1, 1)
        model_settings_layout.addWidget(self.adapt_checkbox, 2, 0)
        model_settings_layout.addWidget(pseudo_threshold_label, 3, 0)
        model_settings_layout.addWidget(self.pseudo_threshold_spinbox, 3, 1)
        model_settings_layout.addWidget(adapt_iter_label, 4, 0)
        model_settings_layout.addWidget(self.adapt_iter_spinbox, 4, 1)
        self.main_layout.addLayout(model_settings_layout)

        self.run_button = QtWidgets.QPushButton("Run")
        self.run_button.clicked.connect(self.run_video_adaptation)
        self.main_layout.addWidget(self.run_button, alignment=Qt.AlignRight)

        self.help_button = QtWidgets.QPushButton("Help")
        self.help_button.clicked.connect(self.show_help_dialog)
        self.main_layout.addWidget(self.help_button, alignment=Qt.AlignLeft)

    def show_help_dialog(self):
        dialog = QtWidgets.QDialog(self)
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel(deeplabcut.video_inference_superanimal.__doc__, self)
        layout.addWidget(label)
        dialog.setLayout(layout)
        dialog.exec_()

    def run_video_adaptation(self):
        videos = list(self.files)
        if not videos:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("You must select a video file")
            msg.setWindowTitle("Error")
            msg.setMinimumWidth(400)
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg.exec_()
            return

        supermodel_name = self.model_combo.currentText()
        videotype = self.video_selection_widget.videotype_widget.currentText()

        func = partial(
            deeplabcut.video_inference_superanimal,
            videos,
            supermodel_name,
            videotype=videotype,
            video_adapt=self.adapt_checkbox.isChecked(),
            pseudo_threshold=self.pseudo_threshold_spinbox.value(),
            adapt_iterations=self.adapt_iter_spinbox.value(),
        )

        self.worker, self.thread = move_to_separate_thread(func)
        self.worker.finished.connect(lambda: self.run_button.setEnabled(True))
        self.worker.finished.connect(lambda: self.root._progress_bar.hide())
        self.thread.start()
        self.run_button.setEnabled(False)
        self.root._progress_bar.show()
