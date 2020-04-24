# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(586, 531)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.splitter.setLineWidth(1)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setOpaqueResize(True)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setObjectName("splitter")
        self.explorer_frame = QtWidgets.QFrame(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(10)
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setHeightForWidth(self.explorer_frame.sizePolicy().hasHeightForWidth())
        self.explorer_frame.setSizePolicy(sizePolicy)
        self.explorer_frame.setMinimumSize(QtCore.QSize(0, 400))
        self.explorer_frame.setStyleSheet("")
        self.explorer_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.explorer_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.explorer_frame.setObjectName("explorer_frame")
        self.gridLayout = QtWidgets.QGridLayout(self.explorer_frame)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        self.explorer_container_layout = QtWidgets.QGridLayout()
        self.explorer_container_layout.setContentsMargins(-1, 20, -1, -1)
        self.explorer_container_layout.setSpacing(0)
        self.explorer_container_layout.setObjectName("explorer_container_layout")
        self.gridLayout.addLayout(self.explorer_container_layout, 1, 0, 1, 1)
        self.terminal_group = QtWidgets.QGroupBox(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.terminal_group.sizePolicy().hasHeightForWidth())
        self.terminal_group.setSizePolicy(sizePolicy)
        self.terminal_group.setMinimumSize(QtCore.QSize(0, 0))
        self.terminal_group.setObjectName("terminal_group")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.terminal_group)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.terminal_frame = QtWidgets.QFrame(self.terminal_group)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.terminal_frame.sizePolicy().hasHeightForWidth())
        self.terminal_frame.setSizePolicy(sizePolicy)
        self.terminal_frame.setMinimumSize(QtCore.QSize(0, 300))
        self.terminal_frame.setStyleSheet("background:black;")
        self.terminal_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.terminal_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.terminal_frame.setLineWidth(0)
        self.terminal_frame.setObjectName("terminal_frame")
        self.horizontalLayout.addWidget(self.terminal_frame)
        self.verticalLayout.addWidget(self.splitter)
        self.button_toggle_terminal = QtWidgets.QPushButton(self.centralwidget)
        self.button_toggle_terminal.setMaximumSize(QtCore.QSize(16777215, 32))
        self.button_toggle_terminal.setDefault(False)
        self.button_toggle_terminal.setFlat(False)
        self.button_toggle_terminal.setObjectName("button_toggle_terminal")
        self.verticalLayout.addWidget(self.button_toggle_terminal)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.button_toggle_terminal.setText(_translate("MainWindow", "↓"))
