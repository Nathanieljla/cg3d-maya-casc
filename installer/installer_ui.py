# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'installer.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QProgressBar, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QTextEdit,
    QVBoxLayout, QWidget, QWizard)

from installer.promotes import (LastPage, PathsPage)

class Ui_Wizard(object):
    def setupUi(self, Wizard):
        if not Wizard.objectName():
            Wizard.setObjectName(u"Wizard")
        Wizard.resize(664, 632)
        Wizard.setWizardStyle(QWizard.ModernStyle)
        Wizard.setOptions(QWizard.HelpButtonOnRight|QWizard.NoBackButtonOnLastPage|QWizard.NoBackButtonOnStartPage|QWizard.NoCancelButton)
        self.wizardPage1 = PathsPage()
        self.wizardPage1.setObjectName(u"wizardPage1")
        self.verticalLayout_2 = QVBoxLayout(self.wizardPage1)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.cascaduer_group = QVBoxLayout()
        self.cascaduer_group.setObjectName(u"cascaduer_group")
        self.groupBox_2 = QGroupBox(self.wizardPage1)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setCheckable(False)
        self.gridLayout_2 = QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.casc_install_set = QPushButton(self.groupBox_2)
        self.casc_install_set.setObjectName(u"casc_install_set")

        self.gridLayout_2.addWidget(self.casc_install_set, 2, 2, 1, 1)

        self.cassc_install_label = QLabel(self.groupBox_2)
        self.cassc_install_label.setObjectName(u"cassc_install_label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cassc_install_label.sizePolicy().hasHeightForWidth())
        self.cassc_install_label.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.cassc_install_label, 2, 0, 1, 1)

        self.casc_json_label = QLabel(self.groupBox_2)
        self.casc_json_label.setObjectName(u"casc_json_label")
        sizePolicy.setHeightForWidth(self.casc_json_label.sizePolicy().hasHeightForWidth())
        self.casc_json_label.setSizePolicy(sizePolicy)
        self.casc_json_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.casc_json_label, 1, 0, 1, 1)

        self.casc_json_value = QLineEdit(self.groupBox_2)
        self.casc_json_value.setObjectName(u"casc_json_value")

        self.gridLayout_2.addWidget(self.casc_json_value, 1, 1, 1, 1)

        self.casc_json_set = QPushButton(self.groupBox_2)
        self.casc_json_set.setObjectName(u"casc_json_set")

        self.gridLayout_2.addWidget(self.casc_json_set, 1, 2, 1, 1)

        self.casc_install_value = QLineEdit(self.groupBox_2)
        self.casc_install_value.setObjectName(u"casc_install_value")

        self.gridLayout_2.addWidget(self.casc_install_value, 2, 1, 1, 1)


        self.cascaduer_group.addWidget(self.groupBox_2)


        self.verticalLayout_2.addLayout(self.cascaduer_group)

        self.maya_group = QGroupBox(self.wizardPage1)
        self.maya_group.setObjectName(u"maya_group")
        self.maya_group.setCheckable(False)
        self.gridLayout = QGridLayout(self.maya_group)
        self.gridLayout.setObjectName(u"gridLayout")
        self.py_path_set = QPushButton(self.maya_group)
        self.py_path_set.setObjectName(u"py_path_set")

        self.gridLayout.addWidget(self.py_path_set, 0, 3, 1, 1)

        self.maya_mod_set = QPushButton(self.maya_group)
        self.maya_mod_set.setObjectName(u"maya_mod_set")

        self.gridLayout.addWidget(self.maya_mod_set, 1, 3, 1, 1)

        self.py_path_value = QLineEdit(self.maya_group)
        self.py_path_value.setObjectName(u"py_path_value")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.py_path_value.sizePolicy().hasHeightForWidth())
        self.py_path_value.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.py_path_value, 0, 2, 1, 1)

        self.maya_mod_label = QLabel(self.maya_group)
        self.maya_mod_label.setObjectName(u"maya_mod_label")
        self.maya_mod_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.maya_mod_label, 1, 0, 1, 1)

        self.maya_mod_value = QLineEdit(self.maya_group)
        self.maya_mod_value.setObjectName(u"maya_mod_value")
        sizePolicy1.setHeightForWidth(self.maya_mod_value.sizePolicy().hasHeightForWidth())
        self.maya_mod_value.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.maya_mod_value, 1, 2, 1, 1)

        self.py_path_label = QLabel(self.maya_group)
        self.py_path_label.setObjectName(u"py_path_label")
        self.py_path_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.py_path_label, 0, 0, 1, 2)

        self.maya_install_set = QPushButton(self.maya_group)
        self.maya_install_set.setObjectName(u"maya_install_set")

        self.gridLayout.addWidget(self.maya_install_set, 2, 3, 1, 1)

        self.find_module_button = QPushButton(self.maya_group)
        self.find_module_button.setObjectName(u"find_module_button")

        self.gridLayout.addWidget(self.find_module_button, 3, 2, 1, 1)

        self.maya_install_label = QLabel(self.maya_group)
        self.maya_install_label.setObjectName(u"maya_install_label")
        self.maya_install_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.maya_install_label, 2, 0, 1, 1)

        self.maya_install_value = QLineEdit(self.maya_group)
        self.maya_install_value.setObjectName(u"maya_install_value")

        self.gridLayout.addWidget(self.maya_install_value, 2, 2, 1, 1)


        self.verticalLayout_2.addWidget(self.maya_group)

        self.progress_group = QVBoxLayout()
        self.progress_group.setObjectName(u"progress_group")
        self.progress_group.setContentsMargins(-1, 0, -1, 0)
        self.progress_label = QLabel(self.wizardPage1)
        self.progress_label.setObjectName(u"progress_label")

        self.progress_group.addWidget(self.progress_label)

        self.progress_bar = QProgressBar(self.wizardPage1)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        self.progress_group.addWidget(self.progress_bar)


        self.verticalLayout_2.addLayout(self.progress_group)

        self.console_group = QHBoxLayout()
        self.console_group.setObjectName(u"console_group")
        self.console_group.setContentsMargins(-1, 8, -1, 8)
        self.console_spacer = QWidget(self.wizardPage1)
        self.console_spacer.setObjectName(u"console_spacer")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.console_spacer.sizePolicy().hasHeightForWidth())
        self.console_spacer.setSizePolicy(sizePolicy2)

        self.console_group.addWidget(self.console_spacer)

        self.console_output = QTextEdit(self.wizardPage1)
        self.console_output.setObjectName(u"console_output")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(1)
        sizePolicy3.setHeightForWidth(self.console_output.sizePolicy().hasHeightForWidth())
        self.console_output.setSizePolicy(sizePolicy3)

        self.console_group.addWidget(self.console_output)


        self.verticalLayout_2.addLayout(self.console_group)

        self.action_group = QHBoxLayout()
        self.action_group.setObjectName(u"action_group")
        self.action_group.setContentsMargins(-1, 4, -1, 4)
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.action_group.addItem(self.horizontalSpacer_2)

        self.install_option = QRadioButton(self.wizardPage1)
        self.install_option.setObjectName(u"install_option")
        self.install_option.setChecked(True)

        self.action_group.addWidget(self.install_option)

        self.remove_option = QRadioButton(self.wizardPage1)
        self.remove_option.setObjectName(u"remove_option")

        self.action_group.addWidget(self.remove_option)

        self.horizontalSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.action_group.addItem(self.horizontalSpacer)


        self.verticalLayout_2.addLayout(self.action_group)

        Wizard.addPage(self.wizardPage1)
        self.wizardPage2 = LastPage()
        self.wizardPage2.setObjectName(u"wizardPage2")
        self.verticalLayout = QVBoxLayout(self.wizardPage2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.result_output = QTextEdit(self.wizardPage2)
        self.result_output.setObjectName(u"result_output")

        self.verticalLayout.addWidget(self.result_output)

        Wizard.addPage(self.wizardPage2)

        self.retranslateUi(Wizard)

        QMetaObject.connectSlotsByName(Wizard)
    # setupUi

    def retranslateUi(self, Wizard):
        Wizard.setWindowTitle(QCoreApplication.translate("Wizard", u"Maya Cascadeur Bridge", None))
        self.wizardPage1.setTitle(QCoreApplication.translate("Wizard", u"Install Options", None))
        self.wizardPage1.setSubTitle("")
        self.groupBox_2.setTitle(QCoreApplication.translate("Wizard", u"Cascadeur", None))
        self.casc_install_set.setText(QCoreApplication.translate("Wizard", u"Browse", None))
        self.cassc_install_label.setText(QCoreApplication.translate("Wizard", u"Install Location", None))
        self.casc_json_label.setText(QCoreApplication.translate("Wizard", u"Settings File", None))
        self.casc_json_set.setText(QCoreApplication.translate("Wizard", u"Browse", None))
        self.maya_group.setTitle(QCoreApplication.translate("Wizard", u"Maya", None))
        self.py_path_set.setText(QCoreApplication.translate("Wizard", u"Browse", None))
        self.maya_mod_set.setText(QCoreApplication.translate("Wizard", u"Browse", None))
        self.maya_mod_label.setText(QCoreApplication.translate("Wizard", u"Module File", None))
        self.py_path_label.setText(QCoreApplication.translate("Wizard", u"Mayapy Location", None))
        self.maya_install_set.setText(QCoreApplication.translate("Wizard", u"Browse", None))
        self.find_module_button.setText(QCoreApplication.translate("Wizard", u"Advanced Search Option -> Search Maya", None))
        self.maya_install_label.setText(QCoreApplication.translate("Wizard", u"Install Location", None))
        self.progress_label.setText("")
        self.console_output.setHtml(QCoreApplication.translate("Wizard", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
        self.install_option.setText(QCoreApplication.translate("Wizard", u"Install/Upgrade", None))
        self.remove_option.setText(QCoreApplication.translate("Wizard", u"Remove", None))
        self.wizardPage2.setTitle(QCoreApplication.translate("Wizard", u"Install Status", None))
    # retranslateUi

