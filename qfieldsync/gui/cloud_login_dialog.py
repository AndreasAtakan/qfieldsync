# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QFieldCloudDialog
                                 A QGIS plugin
 Sync your projects to QField on android
                             -------------------
        begin                : 2020-08-01
        git sha              : $Format:%H$
        copyright            : (C) 2020 by OPENGIS.ch
        email                : info@opengis.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
from typing import Dict

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtNetwork import QNetworkReply
from qgis.PyQt.uic import loadUiType

from qfieldsync.core import Preferences
from qfieldsync.core.cloud_api import QFieldCloudNetworkManager


CloudLoginDialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), '../ui/cloud_login_dialog.ui'))


class CloudLoginDialog(QDialog, CloudLoginDialogUi):
    authenticated = pyqtSignal(str)

    def __init__(self, network_manager, parent=None):
        """Constructor.
        """
        super(CloudLoginDialog, self).__init__(parent=parent)
        self.setupUi(self)
        self.preferences = Preferences()
        self.network_manager = network_manager

        self.loginButton.clicked.connect(self.on_login_button_clicked)
        self.cancelButton.clicked.connect(lambda: self.hide())


    def authenticate(self) -> None:
        last_token = self.preferences.value('qfieldCloudLastToken')

        self.usernameLineEdit.setEnabled(True)
        self.passwordLineEdit.setEnabled(True)
        self.rememberMeCheckBox.setEnabled(True)
        self.loginButton.setEnabled(True)

        if self.parent():
            self.parent().setEnabled(False)
            self.setEnabled(True)


        if last_token:
            self.usernameLineEdit.setEnabled(False)
            self.passwordLineEdit.setEnabled(False)
            self.rememberMeCheckBox.setEnabled(False)
            self.loginButton.setEnabled(False)

            self.network_manager.set_token(last_token)

            reply = self.network_manager.get_user(last_token)
            reply.finished.connect(self.on_get_user_reply_finished(reply)) # pylint: disable=no-value-for-parameter
        else:
            if not self.usernameLineEdit.text():
                self.usernameLineEdit.setText(self.preferences.value('qfieldCloudLastUsername'))
            self.show()

    def on_login_button_clicked(self) -> None:
        self.loginButton.setEnabled(False)
        self.rememberMeCheckBox.setEnabled(False)

        username = self.usernameLineEdit.text()
        password = self.passwordLineEdit.text()

        reply = self.network_manager.login(username, password)
        reply.finished.connect(self.on_login_reply_finished(reply)) # pylint: disable=no-value-for-parameter


    @QFieldCloudNetworkManager.reply_wrapper
    @QFieldCloudNetworkManager.read_json
    def on_get_user_reply_finished(self, reply: QNetworkReply, payload: Dict) -> None:
        if self.parent():
            self.parent().setEnabled(True)
            self.setEnabled(True)

        if reply.error() != QNetworkReply.NoError or payload is None:
            self.preferences.set_value('qfieldCloudLastToken', '')
            self.network_manager.set_token('')
            
            self.loginFeedbackLabel.setText(self.tr('Token reuse failed: %1').format(QFieldCloudNetworkManager.error_reason(reply)))
            self.loginFeedbackLabel.setVisible(True)
            self.usernameLineEdit.setEnabled(True)
            self.passwordLineEdit.setEnabled(True)
            self.rememberMeCheckBox.setEnabled(True)
            self.loginButton.setEnabled(True)
            return

        self.authenticated.emit(payload['username'])

        self.close()

    @QFieldCloudNetworkManager.reply_wrapper
    @QFieldCloudNetworkManager.read_json
    def on_login_reply_finished(self, reply: QNetworkReply, payload: Dict) -> None:
        if self.parent():
            self.parent().setEnabled(True)
            self.setEnabled(True)

        if reply.error() != QNetworkReply.NoError or payload is None:
            self.loginFeedbackLabel.setText(self.tr('Login failed: {}').format(QFieldCloudNetworkManager.error_reason(reply)))
            self.loginFeedbackLabel.setVisible(True)
            self.usernameLineEdit.setEnabled(True)
            self.passwordLineEdit.setEnabled(True)
            self.rememberMeCheckBox.setEnabled(True)
            self.loginButton.setEnabled(True)
            return

        self.network_manager.set_token(payload['token'])

        if self.rememberMeCheckBox.isChecked():
            self.preferences.set_value('qfieldCloudLastToken', payload['token'])

        self.preferences.set_value('qfieldCloudLastUsername', payload['username'])

        self.usernameLineEdit.setEnabled(False)
        self.passwordLineEdit.setEnabled(False)
        self.rememberMeCheckBox.setEnabled(False)

        self.authenticated.emit(payload['username'])

        self.close()