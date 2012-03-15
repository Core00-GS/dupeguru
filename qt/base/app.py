# Created By: Virgil Dupras
# Created On: 2009-04-25
# Copyright 2012 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

import sys
import logging
import os
import os.path as op
import io

from PyQt4.QtCore import QTimer, QObject, QCoreApplication, QUrl, QProcess, SIGNAL, pyqtSignal
from PyQt4.QtGui import QDesktopServices, QFileDialog, QDialog, QMessageBox, QApplication

from jobprogress import job
from jobprogress.qt import Progress
from hscommon.trans import trget
from hscommon.plat import ISLINUX

from core.app import JobType

from qtlib.about_box import AboutBox
from qtlib.recent import Recent
from qtlib.reg import Registration
from qtlib.util import createActions

from . import platform
from .result_window import ResultWindow
from .directories_dialog import DirectoriesDialog
from .problem_dialog import ProblemDialog
from .ignore_list_dialog import IgnoreListDialog

tr = trget('ui')

JOBID2TITLE = {
    JobType.Scan: tr("Scanning for duplicates"),
    JobType.Load: tr("Loading"),
    JobType.Move: tr("Moving"),
    JobType.Copy: tr("Copying"),
    JobType.Delete: tr("Sending files to the recycle bin"),
}

class SysWrapper(io.IOBase):
    def write(self, s):
        if s.strip(): # don't log empty stuff
            logging.warning(s)

class DupeGuru(QObject):
    MODELCLASS = None
    LOGO_NAME = '<replace this>'
    NAME = '<replace this>'
    
    DETAILS_DIALOG_CLASS = None
    RESULT_WINDOW_CLASS = ResultWindow
    RESULT_MODEL_CLASS = None
    PREFERENCES_CLASS = None
    PREFERENCES_DIALOG_CLASS = None
    
    def __init__(self):
        QObject.__init__(self)
        appdata = str(QDesktopServices.storageLocation(QDesktopServices.DataLocation))
        if not op.exists(appdata):
            os.makedirs(appdata)
        # For basicConfig() to work, we have to be sure that no logging has taken place before this call.
        logging.basicConfig(filename=op.join(appdata, 'debug.log'), level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s')
        if sys.stderr is None: # happens under a cx_freeze environment
            sys.stderr = SysWrapper()
        if sys.stdout is None:
            sys.stdout = SysWrapper()
        self.prefs = self.PREFERENCES_CLASS()
        self.prefs.load()
        self.model = self.MODELCLASS(view=self, appdata=appdata)
        self._setup()
        self.prefsChanged.emit(self.prefs)
    
    #--- Private
    def _setup(self):
        self._setupActions()
        self._update_options()
        self.recentResults = Recent(self, 'recentResults')
        self.recentResults.mustOpenItem.connect(self.model.load_from)
        self.resultWindow = self.RESULT_WINDOW_CLASS(self)
        self._progress = Progress(self.resultWindow)
        self.directories_dialog = DirectoriesDialog(self.resultWindow, self)
        self.details_dialog = self.DETAILS_DIALOG_CLASS(self.resultWindow, self)
        self.problemDialog = ProblemDialog(parent=self.resultWindow, model=self.model.problem_dialog)
        self.ignoreListDialog = IgnoreListDialog(parent=self.resultWindow, model=self.model.ignore_list_dialog)
        self.preferences_dialog = self.PREFERENCES_DIALOG_CLASS(self.resultWindow, self)
        self.about_box = AboutBox(self.resultWindow, self)
                
        self.directories_dialog.show()
        self.model.load()
        
        # The timer scheme is because if the nag is not shown before the application is 
        # completely initialized, the nag will be shown before the app shows up in the task bar
        # In some circumstances, the nag is hidden by other window, which may make the user think
        # that the application haven't launched.
        QTimer.singleShot(0, self.finishedLaunching)
        self.connect(QCoreApplication.instance(), SIGNAL('aboutToQuit()'), self.application_will_terminate)
        self.connect(self._progress, SIGNAL('finished(QString)'), self.job_finished)
    
    def _setupActions(self):
        # Setup actions that are common to both the directory dialog and the results window.
        # (name, shortcut, icon, desc, func)
        ACTIONS = [
            ('actionQuit', 'Ctrl+Q', '', tr("Quit"), self.quitTriggered),
            ('actionPreferences', 'Ctrl+P', '', tr("Preferences"), self.preferencesTriggered),
            ('actionIgnoreList', '', '', tr("Ignore List"), self.ignoreListTriggered),
            ('actionShowHelp', 'F1', '', tr("dupeGuru Help"), self.showHelpTriggered),
            ('actionAbout', '', '', tr("About dupeGuru"), self.showAboutBoxTriggered),
            ('actionRegister', '', '', tr("Register dupeGuru"), self.registerTriggered),
            ('actionCheckForUpdate', '', '', tr("Check for Update"), self.checkForUpdateTriggered),
            ('actionOpenDebugLog', '', '', tr("Open Debug Log"), self.openDebugLogTriggered),
        ]
        createActions(ACTIONS, self)
        
        if ISLINUX:
            self.actionCheckForUpdate.setVisible(False) # This only works on Windows
    
    def _update_options(self):
        self.model.scanner.mix_file_kind = self.prefs.mix_file_kind
        self.model.options['escape_filter_regexp'] = self.prefs.use_regexp
        self.model.options['clean_empty_dirs'] = self.prefs.remove_empty_folders
        self.model.options['ignore_hardlink_matches'] = self.prefs.ignore_hardlink_matches
        self.model.options['copymove_dest_type'] = self.prefs.destination_type
    
    #--- Public
    def add_selected_to_ignore_list(self):
        self.model.add_selected_to_ignore_list()
    
    def remove_selected(self):
        self.model.remove_selected(self)
    
    def askForRegCode(self):
        reg = Registration(self.model)
        reg.ask_for_code()
    
    def confirm(self, title, msg, default_button=QMessageBox.Yes):
        active = QApplication.activeWindow()
        buttons = QMessageBox.Yes | QMessageBox.No
        answer = QMessageBox.question(active, title, msg, buttons, default_button)
        return answer == QMessageBox.Yes
    
    def invokeCustomCommand(self):
        self.model.invoke_custom_command()
    
    def show_details(self):
        self.details_dialog.show()
    
    def showResultsWindow(self):
        self.resultWindow.show()
    
    #--- Signals
    willSavePrefs = pyqtSignal()
    prefsChanged = pyqtSignal(object)
    
    #--- Events
    def finishedLaunching(self):
        self.model.initial_registration_setup()
        if sys.getfilesystemencoding() == 'ascii':
            # No need to localize this, it's a debugging message.
            msg = "Something is wrong with the way your system locale is set. If the files you're "\
               "scanning have accented letters, you'll probably get a crash. It is advised that "\
               "you set your system locale properly."
            QMessageBox.warning(self.directories_dialog, "Wrong Locale", msg)
    
    def application_will_terminate(self):
        self.willSavePrefs.emit()
        self.prefs.save()
        self.model.save()
    
    def checkForUpdateTriggered(self):
        QProcess.execute('updater.exe', ['/checknow'])
    
    def ignoreListTriggered(self):
        self.model.ignore_list_dialog.show()
    
    def job_finished(self, jobid):
        result = self.model._job_completed(jobid, self._progress.last_error)
        if not result:
            self._progress.reraise_if_error()
    
    def openDebugLogTriggered(self):
        debugLogPath = op.join(self.model.appdata, 'debug.log')
        self.open_path(debugLogPath)
    
    def preferencesTriggered(self):
        self.preferences_dialog.load()
        result = self.preferences_dialog.exec()
        if result == QDialog.Accepted:
            self.preferences_dialog.save()
            self.prefs.save()
            self._update_options()
            self.prefsChanged.emit(self.prefs)
    
    def quitTriggered(self):
        self.directories_dialog.close()
    
    def registerTriggered(self):
        reg = Registration(self.model)
        reg.ask_for_code()
    
    def showAboutBoxTriggered(self):
        self.about_box.show()
    
    def showHelpTriggered(self):
        base_path = platform.HELP_PATH
        url = QUrl.fromLocalFile(op.abspath(op.join(base_path, 'index.html')))
        QDesktopServices.openUrl(url)
    
    #--- model --> view
    @staticmethod
    def open_path(path):
        url = QUrl.fromLocalFile(str(path))
        QDesktopServices.openUrl(url)
    
    @staticmethod
    def reveal_path(path):
        DupeGuru.open_path(path[:-1])
    
    def start_job(self, jobid, func, args=()):
        title = JOBID2TITLE[jobid]
        try:
            j = self._progress.create_job()
            args = (j, ) + tuple(args)
            self._progress.run(jobid, title, func, args=args)
        except job.JobInProgressError:
            msg = tr("A previous action is still hanging in there. You can't start a new one yet. Wait a few seconds, then try again.")
            QMessageBox.information(self.resultWindow, 'Action in progress', msg)
    
    def get_default(self, key):
        return self.prefs.get_value(key)
    
    def set_default(self, key, value):
        self.prefs.set_value(key, value)
    
    def setup_as_registered(self):
        self.actionRegister.setVisible(False)
        self.about_box.registerButton.hide()
        self.about_box.registeredEmailLabel.setText(self.model.registration_email)
    
    def show_fairware_nag(self, prompt):
        reg = Registration(self.model)
        reg.show_fairware_nag(prompt)
    
    def show_demo_nag(self, prompt):
        reg = Registration(self.model)
        reg.show_demo_nag(prompt)
    
    def show_message(self, msg):
        window = QApplication.activeWindow()
        QMessageBox.information(window, '', msg)
    
    def ask_yes_no(self, prompt):
        return self.confirm('', prompt)
    
    def open_url(self, url):
        url = QUrl(url)
        QDesktopServices.openUrl(url)
    
    def show_results_window(self):
        self.showResultsWindow()
    
    def show_problem_dialog(self):
        self.problemDialog.show()
    
    def select_dest_folder(self, prompt):
        flags = QFileDialog.ShowDirsOnly
        return QFileDialog.getExistingDirectory(self.resultWindow, prompt, '', flags)
    
