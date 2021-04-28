import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QMenu, \
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QDialog, QRadioButton, QSpinBox, \
    QDoubleSpinBox, QTabWidget, QComboBox, QMessageBox
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QSize, QTimer
import pyqtgraph as pg

import numpy as np
from datetime import datetime
import time

from S15lib.instruments import usb_counter_fpga as tdc1
from S15lib.instruments import serial_connection

"""[summary]
    This is the GUI for the usb counter TDC1. It processes data from TDC1's three different modes - singles, pairs and timestamp - and displays
    the data in a live-updating graph.

    Usage:
    Live Start button can be used to start the graphing without any logging.
    Select logfile and Start logging buttons are used to log data to a csv file in addition to plotting.
"""


PLT_SAMPLES = 500 # plot samples

class logWorker(QtCore.QObject):
    """[summary]
    Worker object for threading the logging process to ensure the GUI does not freeze up while data is being logged and plotted.

    Args:
        QtCore (QObject): [description]
    """
    # Worker Signals
    data_is_logged = QtCore.pyqtSignal(tuple, str, list)
    histogram_logged = QtCore.pyqtSignal(dict)
    coincidences_data_logged = QtCore.pyqtSignal('PyQt_PyObject') # Replace 'PyQt_PyObject' with object?
    thread_finished = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self):
        super(logWorker, self).__init__()
        self.active_flag = False
        self.radio_flags = [0,0,0,0] # 0 represents unchecked radio button
        self.int_time = 1
    
    # Connected to MainWindow.logging_requested
    @QtCore.pyqtSlot(str, str, bool, str, object)
    def log_which_data(self, file_name: str, \
        device_path: str, log_flag: bool, dev_mode: str, tdc1_dev: object):
        print('logging signal received')
        self.active_flag = True
        if dev_mode == 'singles':
            print('initiating singles log...')
            self.log_counts_data(file_name, \
        device_path, log_flag, dev_mode, tdc1_dev)
        elif dev_mode == 'pairs':
            print('initiating coincidences log...')
            self.log_coincidences_data(file_name, \
        device_path, log_flag, dev_mode, tdc1_dev)
        elif dev_mode == 'timestamp':
            print('initiating timestamp log')
            self.log_timestamp_data(file_name, \
        device_path, log_flag, dev_mode, tdc1_dev)

    def log_counts_data(self, file_name: str, \
        device_path: str, log_flag: bool, dev_mode: str, tdc1_dev: object):
        start = time.time()
        now = start
        if log_flag == True and self.active_flag == True:
            try:
                open(file_name)
            except IOError:
                # --- Add functionality to handle empty files --- #
                f = open(file_name, 'w')
                f.write('#time_stamp,counts\n')
            while self.active_flag == True:
                counts = tdc1_dev.get_counts(self.int_time)
                now = time.time()
                self.data_is_logged.emit(counts, dev_mode, self.radio_flags)
                with open(file_name, 'a+') as f:
                    # Organising data into pairs
                    time_data: str = datetime.now().isoformat()
                    data_pairs = '{},{}\n'.format(time_data, counts)
                    f.write(data_pairs)
                if self.active_flag == False:
                    break
        elif log_flag == False:
            while self.active_flag == True:
                a = time.time()
                counts = tdc1_dev.get_counts(self.int_time)
                print('this is counts:' + str(counts))
                self.data_is_logged.emit(counts, dev_mode, self.radio_flags)
                b = time.time()
                print('time taken this loop: ' + str(b-a))
                if self.active_flag == False:
                    break
        self.thread_finished.emit('Finished logging')

    def log_coincidences_data(self, file_name: str, \
        device_path: str, log_flag: bool, dev_mode: str, tdc1_dev: object):
        """[summary]
        Logs the data from TDC1 Timestamp unit when in Coincidences mode. See log_counts_data function for more information.
        """
        start = time.time()
        now = start
        if log_flag == True and self.active_flag == True:
            try:
                open(file_name)
            except IOError:
                # --- Add functionality to handle empty files --- #
                f = open(file_name, 'w')
                f.write('#time_stamp,coincidences\n')
            while self.active_flag == True:
                coincidences = tdc1_dev.get_counts_and_coincidences(self.int_time)
                now = time.time()
                self.data_is_logged.emit(coincidences, dev_mode, self.radio_flags)
                with open(file_name, 'a+') as f:
                    # Organising data into pairs
                    time_data: str = datetime.now().isoformat()
                    data_pairs = '{},{}\n'.format(time_data, counts)
                    f.write(data_pairs)
                if self.active_flag == False:
                    break
        elif log_flag == False:
            while self.active_flag == True:
                coincidences = tdc1_dev.get_counts_and_coincidences(self.int_time)
                now = time.time()
                self.data_is_logged.emit(coincidences, dev_mode, self.radio_flags)
                if self.active_flag == False:
                        break
        self.thread_finished.emit('Finished logging')

    # Modify this to plot without logging
    def log_timestamp_and_plot_g2(self, file_name: str, \
        device_path: str, log_flag: bool, dev_mode: str, tdc1_dev: object):
        # Performs all the actions of log_counts_data PLUS gathering the data to plot histogram
        # tdc1_dev.get_timestamps() automatically puts device in timestamp mode (3)
        start = time.time()
        now = start
        if log_flag == True and self.active_flag == True:
            try:
                open(file_name)
            except IOError:
                f = open(file_name, 'w')
                f.write('#time_stamp,channel\n')
            while self.active_flag == True:
                timestamps = tdc1_dev.get_timestamps(self.int_time)
                # get_timestamps -> Tuple[List[float], List[str]]
                for i in len(timestamps):
                    data_pairs = '{},{}\n'.format(timestamps[0][i], timestamps[1][i])
                    f.write(data_pairs)
                if self.active_flag == False:
                    break
        g2_dict = tdc1_dev.count_g2(self.int_time)
        self.histogram_logged.emit(g2_dict)


class MainWindow(QMainWindow):
    """[summary]
    Main window class containing the main window and its associated methods. 
    Args:
        QMainWindow (QObject): See qt documentation for more info.
    """
    # Send logging parameters to worker method
    # int str str bool str object
    logging_requested = QtCore.pyqtSignal(str, str, bool, str, object)
    
    def __init__(self, *args, **kwargs):
        """[summary]
        Function to initialise the Main Window, which will hold all the subsequent widgets to be created.
        """
        super(MainWindow, self).__init__(*args, **kwargs)

        self.integration_time = 1
        self._logfile_name = '' # Track the logfile(csv) being used by GUI
        self.device_path = '' # Device path, eg. 'COM4'
        self.log_flag = False  # Flag to track if data is being logged to csv file
        self._tdc1_dev = None  # tdc1 device object
        self._dev_mode = '' # 0 = 'singles', 1 = 'pairs', 3 = 'timestamp'
        self._plot_tab = 0  # Counts graph = 0, Coincidences graph = 1
        self.acq_flag = False # Track if data is being acquired
        self.logger = None # Variable that will hold the logWorker object
        self._radio_flags = [1,1,1,1] # Tracking which radio buttons are selected. All 1s by default

        self.initUI() # UI is initialised afer the class variables are defined

        

    
    def initUI(self):
        """[summary]
        Contains all the UI elements and associated functionalities.
        """
        
        #---------Buttons---------#
        self.liveStart_Button = QtWidgets.QPushButton("Live Start", self)
        self.liveStart_Button.clicked.connect(self.liveStart)
        self.liveStart_Button.setFixedSize(QSize(115, 23))

        self.selectLogfile_Button = QtWidgets.QPushButton("Select Logfile", self)
        self.selectLogfile_Button.clicked.connect(self.selectLogfile)
        self.selectLogfile_Button.setFixedSize(QSize(115, 23))

        #self.startLogging_Button = QtWidgets.QPushButton("Start Logging", self)
        #self.startLogging_Button.clicked.connect(self.startLogging)
        #self.startLogging_Button.setFixedSize(QSize(115, 23))
        #self.startLogging_Button.setEnabled(False)

        self.updateDeviceMode_Button = QtWidgets.QPushButton("Update Device Mode", self)
        self.updateDeviceMode_Button.clicked.connect(self.updateDeviceMode)

        # setAutoExclusive method is used to toggle the radio buttons independently.
        self.radio1_Button = QRadioButton("Channel 1", self)
        self.radio1_Button.setStyleSheet('color: red')
        self.radio1_Button.setAutoExclusive(False)
        #self.radio1_Button.setChecked(True)
        self.radio1_Button.toggled.connect(lambda: self.displayPlot1(self.radio1_Button))
        self.radio2_Button = QRadioButton("Channel 2", self)
        self.radio2_Button.setStyleSheet('color: green')
        self.radio2_Button.setAutoExclusive(False)
        #self.radio2_Button.setChecked(True)
        self.radio2_Button.toggled.connect(lambda: self.displayPlot2(self.radio2_Button))
        self.radio3_Button = QRadioButton("Channel 3", self)
        self.radio3_Button.setStyleSheet('color: blue')
        self.radio3_Button.setAutoExclusive(False)
        #self.radio3_Button.setChecked(True)
        self.radio3_Button.toggled.connect(lambda: self.displayPlot3(self.radio3_Button))
        self.radio4_Button = QRadioButton("Channel 4", self)
        self.radio4_Button.setStyleSheet('color: black')
        self.radio4_Button.setAutoExclusive(False)
        #self.radio4_Button.setChecked(True)
        self.radio4_Button.toggled.connect(lambda: self.displayPlot4(self.radio4_Button))
        #---------Buttons---------#


        #---------Labels---------#
        self.deviceLabel = QtWidgets.QLabel("Device:", self)
        self.deviceModeLabel = QtWidgets.QLabel("Device Mode:", self)
        self.deviceModeText = QtWidgets.QLabel("")

        self.logfileLabel = QtWidgets.QLabel('')

        self.integrationLabel = QtWidgets.QLabel("Integration time (ms):", self)
        #---------Labels---------#


        #---------Interactive Fields---------#
        self.integrationSpinBox = QSpinBox(self)
        self.integrationSpinBox.setRange(0, 65535)
        self.integrationSpinBox.setValue(1000) # Default 1000ms = 1s
        self.integrationSpinBox.setKeyboardTracking(False) # Makes sure valueChanged signal only fires when you want it to
        self.integrationSpinBox.valueChanged.connect(self.update_intTime)

        dev_list = serial_connection.search_for_serial_devices(
            tdc1.TimeStampTDC1.DEVICE_IDENTIFIER)
        self.devCombobox = QComboBox(self)
        self.devCombobox.addItems(dev_list)

        dev_modes = ['singles', 'pairs', 'timestamp']
        self.modesCombobox = QComboBox(self)
        self.modesCombobox.addItems(dev_modes)
        self.modesCombobox.currentTextChanged.connect(self.updateDeviceMode)
        self.modesCombobox.setEnabled(False)

        #---------Interactive Fields---------#


        #---------PLOTS---------#
        # Initiating plot data variables
        # Plot 1 - Four channel counts plot
        self.x = []
        self.y1 = []
        self.y2 = []
        self.y3 = []
        self.y4 = []
        self.y_data = [self.y1, self.y2, self.y3, self.y4]

        # Plot 2 - Time difference histogram (Channel cross-correlation)
        self.x0 = []
        self.y0 = []
        
        font = QtGui.QFont("Arial", 18)     
        labelStyle = '<span style=\"color:black;font-size:25px\">'

        # Setting up plot window 1 (Plot Widget)
        self.tdcPlot = pg.PlotWidget(title = "Three plot curves")
        self.tdcPlot.setBackground('w')
        self.tdcPlot.setLabel('left', labelStyle + 'Counts')
        self.tdcPlot.setLabel('bottom', labelStyle + 'Sample Number')
        self.tdcPlot.getAxis('left').tickFont = font
        self.tdcPlot.getAxis('bottom').tickFont = font
        self.tdcPlot.getAxis('bottom').setPen(color='k')
        self.tdcPlot.getAxis('left').setPen(color='k')
        self.tdcPlot.showGrid(y=True)
        
        # Setting up plot window 2 (Plot Widget)
        self.tdcPlot2 = pg.PlotWidget(title = "Coincidences Histogram")
        self.tdcPlot2.setBackground('w')
        self.tdcPlot2.setLabel('left', labelStyle + 'Coincidences')
        self.tdcPlot2.setLabel('bottom', labelStyle + 'Time Delay')
        self.tdcPlot2.getAxis('left').tickFont = font
        self.tdcPlot2.getAxis('bottom').tickFont = font
        self.tdcPlot2.getAxis('bottom').setPen(color='k')
        self.tdcPlot2.getAxis('left').setPen(color='k')
        self.tdcPlot2.showGrid(y=True)

        # Setting up data plots (Plot data item)
        self.lineStyle1 = pg.mkPen(width=2, color='r') # Red
        self.lineStyle2 = pg.mkPen(width=2, color='g') # Green
        self.lineStyle3 = pg.mkPen(width=2, color='b') # Blue
        self.lineStyle4 = pg.mkPen(width=2, color='k') # Black
        self.lineStyle0 = pg.mkPen(width=2, color='r')

        # Plotting the graph - https://pyqtgraph.readthedocs.io/en/latest/plotting.html for organisation of plotting classes
        # Take note: multiple plotDataItems can sit on one plotWidget
        self.linePlot1 = self.tdcPlot.plot(self.x, self.y1, pen=self.lineStyle1)
        self.linePlot2 = self.tdcPlot.plot(self.x, self.y2, pen=self.lineStyle2)
        self.linePlot3 = self.tdcPlot.plot(self.x, self.y3, pen=self.lineStyle3)
        self.linePlot4 = self.tdcPlot.plot(self.x, self.y4, pen=self.lineStyle4)
        self.histogramPlot = self.tdcPlot2.plot(self.x0, self.y0, pen=self.lineStyle0, symbol = 'x', symbolPen = 'b', symbolBrush = 0.2)
        self.linePlots = [self.linePlot1, self.linePlot2, self.linePlot3, self.linePlot4]

        #self.tdcPlotLegend = pg.LegendItem()
        #self.tdcPlotLegend.addItem(self.linePlot1, 'Channel 1')
        #elf.tdcPlotLegend.addItem(self.linePlot2, 'Channel 2')
        #self.tdcPlotLegend.addItem(self.linePlot3, 'Channel 3')
        #self.tdcPlotLegend.addItem(self.linePlot4, 'Channel 4')
        #self.tdcPlotLegend.setParentItem(self.tdcPlot)
        #---------PLOTS---------#

        
        #---------Main Window---------#
        self.setWindowTitle("TDC-1")    
        #---------Main Window---------#


        #---------Tabs---------#
        self.tabs = QTabWidget()

        self.tab1 = QWidget()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tdcPlot)
        self.tab1.setLayout(self.layout)
        self.tabs.addTab(self.tab1, "Counts")

        self.tab2 = QWidget()
        self.layout2 = QVBoxLayout()
        self.layout2.addWidget(self.tdcPlot2)
        self.tab2.setLayout(self.layout2)
        self.tabs.addTab(self.tab2, "Coincidences")
        self.tabs.currentChanged.connect(self.update_plot_tab)
        #---------Tabs---------#


        #Layout
        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        self.grid.addWidget(self.deviceLabel, 0, 0)
        self.grid.addWidget(self.devCombobox, 0, 1)
        self.grid.addWidget(self.deviceModeLabel, 0, 2)
        self.grid.addWidget(self.modesCombobox, 0, 3)
        self.grid.addWidget(self.integrationLabel, 1, 0)
        self.grid.addWidget(self.integrationSpinBox, 1, 1)
        self.grid.addWidget(self.updateDeviceMode_Button, 1, 2)
        self.grid.addWidget(self.liveStart_Button, 2, 0)
        #self.grid.addWidget(self.startLogging_Button, 2, 1)
        self.grid.addWidget(self.selectLogfile_Button, 2, 2)
        self.grid.addWidget(self.logfileLabel, 2, 3)
        self.grid.addWidget(self.tabs, 4, 0, 5, 4)

        self.radioLayout = QHBoxLayout()
        self.radioLayout.addWidget(self.radio1_Button)
        self.radioLayout.addWidget(self.radio2_Button)
        self.radioLayout.addWidget(self.radio3_Button)
        self.radioLayout.addWidget(self.radio4_Button)
        self.grid.addLayout(self.radioLayout, 3, 0, 1, 2)

        #Main Widget (on which the grid is to be implanted)
        self.mainwidget = QWidget()
        self.mainwidget.layout = self.grid
        self.mainwidget.setLayout(self.mainwidget.layout)
        self.setCentralWidget(self.mainwidget)

    # Connected to updateDeviceMode_Button
    @QtCore.pyqtSlot()
    def updateDeviceMode(self):
        modez: str = self._tdc1_dev.mode
        self._dev_mode = modez
        self.deviceModeText.setText(modez)

    # Update plot index on plot tab change
    @QtCore.pyqtSlot()
    def update_plot_tab(self):
        self._plot_tab = self.tabs.currentIndex()

    # Update integration time on spinbox value change
    @QtCore.pyqtSlot(int)
    def update_intTime(self, int_time: int):
        # Convert to seconds
        self.integration_time = int_time * 1e-3
        if self.logger:
            self.logger.int_time = int_time * 1e-3

    # Click Live Start button to get started!
    @QtCore.pyqtSlot()
    # Connected to self.liveStart_button.clicked
    def liveStart(self):
        # === Add in more functions to reset GUI to base state === #
        #If currently live plotting
        if self.acq_flag is True and self.liveStart_Button.text() == "Live Stop":
            self.acq_flag = False
            self.logger.active_flag = False # Sets logger flag to break the while loop
            self.selectLogfile_Button.setEnabled(True)
            self.modesCombobox.setEnabled(False)
            self.liveStart_Button.setText("Live Start")
            self._tdc1_dev = None # Destroy tdc1_dev object
            
            #if self._logfile_name != '':
            #   self.startLogging_Button.setEnabled(True)
        #If not currently live plotting
        else:
            self._tdc1_dev = tdc1.TimeStampTDC1(self.devCombobox.currentText())
            self.device_path = self.devCombobox.currentText()
            self._dev_mode = self._tdc1_dev.mode
            self.acq_flag = True
            # Initialise empty lists to hold data
            self.x = []
            self.y1 = []
            self.y2 = []
            self.y3 = []
            self.y4 = []
            self.x0 = []
            self.y0 = []
            self.selectLogfile_Button.setEnabled(False)
            self.modesCombobox.setEnabled(True)
            self.liveStart_Button.setText("Live Stop")
            self.startLogging()


    # Logging
    def startLogging(self):
        """[summary]
        Creation process of worker object and QThread.
        """
        #slbtext = self.startLogging_Button.text()

        #self.startLogging_Button.setText("Stop Logging")
        # Create worker instance and a thread
        self.logger = logWorker()
        self.logger_thread = QtCore.QThread(self) # QThread is not a thread, but a thread MANAGER

        # Assign worker to the thread and start the thread
        self.logger.moveToThread(self.logger_thread)
        self.logger_thread.start() # This is where the thread is actually created, I think

        self.logger.int_time = int(self.integrationSpinBox.text()) * 1e-3 # Convert to seconds

        # Connect signals and slots AFTER moving the object to the thread
        self.logging_requested.connect(self.logger.log_which_data)
        self.logger.data_is_logged.connect(self.update_data_from_thread)
        self.logger.histogram_logged.connect(self.updateHistogram)
        #self.log_flag = True
        self.logging_requested.emit(self._logfile_name, \
        self.device_path, self.log_flag, self._dev_mode, self._tdc1_dev)
        print('logging signal emitted')

    @QtCore.pyqtSlot()
    def selectLogfile(self):
        default_filetype = 'csv'
        start = datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss ") + "_TDC1." + default_filetype
        self._logfile_name = QtGui.QFileDialog.getSaveFileName(
            self, "Save to log file", start)[0]
        self.logfileLabel.setText(self._logfile_name)
        if self._logfile_name != '':
            #self.startLogging_Button.setEnabled(True)
            self.log_flag = True

            
    # Updating data
    # Connected to data_is_logged signal
    @QtCore.pyqtSlot(tuple, str, list)
    def update_data_from_thread(self, data: tuple, dev_mode: str, radio_flags: list):
        if len(self.x) == PLT_SAMPLES:
            self.x = self.x[1:]
            self.x.append(self.x[-1] + 1)
            self.y1 = self.y1[1:]
            self.y2 = self.y2[1:]
            self.y3 = self.y3[1:]
            self.y4 = self.y4[1:]
        else:
            self.x.append(len(self.x) + 1) # Takes care of empty list case as well
        self.y1.append(data[0])
        self.y2.append(data[1])
        self.y3.append(data[2])
        self.y4.append(data[3])
        self.y_data = [self.y1, self.y2, self.y3, self.y4]
        self._radio_flags = radio_flags
        self.updatePlots(self._radio_flags)
    
    
    # Updating plots 1-4
    def updatePlots(self, radio_flags: list):
        for i in range(len(radio_flags)):
            if radio_flags[i] == 1:
                self.linePlots[i].setData(self.x, self.y_data[i])

    
    # Radio button slots (functions)
    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot1(self, b: QRadioButton):
        if self.acq_flag == True:
            if b.isChecked() == True:
                # Possible to clear self.x and self.y1 without disrupting the worker loop?
                self.updatePlots(self._radio_flags)
                self.linePlot1.setPen(self.lineStyle1)
                self.logger.radio_flags[0] = 1
                self._radio_flags[0] = 1
            elif b.isChecked() == False:
                # set data to empty lists to delete plots
                # Try setData(self.x, []), see if mismatch list size gives error
                # If that doesn't work, might have to use x1, x2, x3, x4 to manipulate graphs separately
                self.linePlot1.setPen(None)
                self.logger.radio_flags[0] = 0
                self._radio_flags[0] = 0

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot2(self, b: QRadioButton):
        if self.acq_flag == True:
            if b.isChecked() == True:
                self.updatePlots(self._radio_flags)
                self.linePlot2.setPen(self.lineStyle2)
                self.logger.radio_flags[1] = 1
                self._radio_flags[1] = 1
            elif b.isChecked() == False:
                self.linePlot2.setPen(None)
                self.logger.radio_flags[1] = 0
                self._radio_flags[1] = 0

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot3(self, b: QRadioButton):
        if self.acq_flag == True:
            if b.isChecked() == True:
                self.updatePlots(self._radio_flags)
                self.linePlot3.setPen(self.lineStyle3)
                self.logger.radio_flags[2] = 1
                self._radio_flags[2] = 1
            elif b.isChecked() == False:
                self.linePlot3.setPen(None)
                self.logger.radio_flags[2] = 0
                self._radio_flags[2] = 0

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot4(self, b: QRadioButton):
        if self.acq_flag == True:
            if b.isChecked():
                self.updatePlots(self._radio_flags)
                self.linePlot4.setPen(self.lineStyle4)
                self.logger.radio_flags[3] = 1
                self._radio_flags[3] = 1
            elif b.isChecked() == False:
                self.linePlot4.setPen(None)
                self.logger.radio_flags[3] = 0
                self._radio_flags[3] = 0
    
    # Histogram
    # Connected to histogram_logged signal
    def updateHistogram(self, g2_data: dict):
        # {int - ch_start counts, int- ch_stop counts, int - actual acq time, float - time bins, float - histogram values}
        # time bins and histogram vals are both np arrays...?
        # work off the assumption that it's true
        self.x0 = g2_data('time_bins')
        self.y0 = g2_data('histogram')
        print(type(self.x0))
        print(type(self.yo))
        if len(self.x0) >= PLT_SAMPLES:
            del_index = np.arange(PLT_SAMPLES, len(self.x0))
            np.delete(self.x0, del_index)
            np.delete(self.y0, del_index) # Shorten the plot data to 500 data points
        # Update the graph
            self.histogramPlot.setData(self.x0, self.y0)

    @QtCore.pyqtSlot(str)
    def changeDevMode(self, mode: str):
        self._tdc1_dev.mode = mode
        # Add in a qmessagebox to confirm manual mode switch
        # Reset all data and plots on confirmation
        self.acq_flag = False
        self.logger.active_flag = False

    def resetDataAndPlots(self):
        self.x0=[]
        self.y0=[]
        self.x=[]
        self.y1=[]
        self.y2=[]
        self.y3=[]
        self.y4=[]
        self.linePlot1.setData(self.x, self.y1)
        self.linePlot2.setData(self.x, self.y2)
        self.linePlot3.setData(self.x, self.y3)
        self.linePlot4.setData(self.x, self.y4)
        self.histogramPlot.setData(self.x0, self.y0)



def main():
        app = QApplication(sys.argv)
        win = MainWindow()
        win.show()
        sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()


######################
# Things to Note     #
######################

# 1. Only communicate with worker via Signals and Slots
#   - Do not call any of its methods from the main thread


######################
# Code Outline       #
######################

# 1. This code processes and plots data from TDC1 timestamp unit
# 2. There are two classes: logWorker and MainWindow
#   - logWorker handles the data logging to the csv file via a separate thread
#   - MainWindow contains the GUI as well as graph plotting functions
