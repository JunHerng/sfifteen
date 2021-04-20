import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QMenu, \
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QDialog, QRadioButton, QSpinBox, \
    QTabWidget, QComboBox
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QSize, QTimer
import pyqtgraph as pg

import numpy as np # for sample graph
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
    Worker object for threading the logging process to ensure the GUI does not freeze up while data is being logged.

    Args:
        QtCore (QObject): [description]
    """
    # The worker will emit a signal containing the Counts/Coincidences depending on mode
    data_is_logged = QtCore.pyqtSignal(tuple, str)
    coincidences_data_logged = QtCore.pyqtSignal('PyQt_PyObject') # Replace 'PyQt_PyObject' with object?
    thread_finished = QtCore.pyqtSignal('PyQt_PyObject')
    
    def _init__(self):
        super().__init__(self) #Calls QObject.__init__()

    def log_which_data(self, integration_time: int, file_name: str, total_time: int, \
        sampling_rate: int, device_path: str, log_flag: bool, dev_mode: str):
        if dev_mode == 'singles':
            self.log_counts_data(integration_time, file_name, total_time, \
        sampling_rate, device_path, log_flag, dev_mode)
        elif dev_mode == 'pairs':
            self.log_coincidences_data(integration_time, file_name, total_time, \
        sampling_rate, device_path, log_flag, dev_mode)

    # int, str, int, int, str, bool
    def log_counts_data(self, integration_time: int, file_name: str, total_time: int, \
        sampling_rate: int, device_path: str, log_flag: bool, dev_mode: str):
        """[summary]
        Logs the data from TDC1 Timestamp unit when in Counts mode. The required Args are received from the connected pyqt signal.
        Two signals are emitted: plot_data_logged at the end of each loop, thread_finished when all loops are done.

        Args:
            integration time (int): Wavelength of measurement
            file_name (str): Csv file used to record data
            total_time (int): Total experimental run time
            sampling_rate (int): How often the data is sampled
            device_path (str): Location of device. Eg. 'COM4' on windows os.
            log_flag (bool): Begin data logging if True, do not log if False.
        """
        start = time.time()
        now = start
        try:
            open(file_name)
        except IOError:
            # --- Add functionality to handle empty files --- #
            f = open(file_name, 'w')
            f.write('#time_stamp,counts\n')
        while (now-start) < total_time and log_flag is False:
            counts = tdc1.TimeStampTDC1.get_counts()
            time.sleep(1/sampling_rate)
            now = time.time()
            data_is_logged.emit(counts, dev_mode)
            with open(file_name, 'a+') as f:
                # Organising data into pairs
                time_data: str = datetime.now().isoformat()
                data_pairs = '{},{}\n'.format(time_data, counts)
                f.write(data_pairs)
        self.thread_finished.emit('Finished logging')

    # int, str, int, int, str, bool
    def log_coincidences_data(self, integration_time: int, file_name: str, total_time: int, \
        sampling_rate: int, device_path: str, log_flag: bool, dev_mode: str):
        """[summary]
        Logs the data from TDC1 Timestamp unit when in Coincidences mode. See log_counts_data function for more information.
        """
        start = time.time()
        now = start
        try:
            open(file_name)
        except IOError:
            # --- Add functionality to handle empty files --- #
            f = open(file_name, 'w')
            f.write('#time_stamp,coincidences\n')
        while (now-start) < total_time and log_flag is True:
            counts = tdc1.TimeStampTDC1.get_pairs()
            time.sleep(1/sampling_rate)
            now = time.time()
            data_is_logged.emit(coincidences, dev_mode)
            with open(file_name, 'a+') as f:
                #organising data into pairs
                data_pairs = '{},{}\n'.format(datetime.now().isoformat(), coincidences)
                f.write(data_pairs)
        self.thread_finished.emit('Finished logging')


class MainWindow(QMainWindow):
    """[summary]
    Main window class containing the main window and its associated methods. 
    Args:
        QMainWindow (QObject): See qt documentation for more info.
    """
    # Send logging parameters to worker method
    logging_requested = QtCore.pyqtSignal(int, str, int, int, str, bool, str)
    
    def __init__(self, *args, **kwargs):
        """[summary]
        Function to initialise the Main Window, which will hold all the subsequent widgets to be created.
        """
        super(MainWindow, self).__init__(*args, **kwargs)
        

        self.integration_time = 100
        self._logfile_name = '' # Track the logfile(csv) being used by GUI
        self.total_time = 100  # Total acquisition time
        self.plot_refresh_rate = 10  # Times to update the plot per second
        self.device_path = '' # Device path, eg. 'COM4'
        self.log_flag = False  # Flag to track if data is being logged to csv file
        self._tdc1_dev = None  # tdc1 device object
        self._dev_mode = '' # 0 = 'singles', 1 = 'pairs', 2 = 'timestamp'
        self._plot_tab = 0  # Counts graph = 0, Coincidences graph = 1

        self.acq_flag = False # Track if data is being acquired live
        self.initUI() # UI is initialised afer the class variables are defined

        #---------Worker Init---------#

        #Create worker instance and a thread
        self.logger = logWorker()
        self.logger_thread = QtCore.QThread()

        #Assign worker to the thread and start the thread
        self.logger.moveToThread(self.logger_thread)
        self.logger_thread.start()

        #Connect signals and slots AFTER moving the object to the thread
        self.logging_requested.connect(self.logger.log_which_data)
        self.logger.data_is_logged.connect(self.drawWhichPlot)

        #---------Worker Init---------#

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

        self.startLogging_Button = QtWidgets.QPushButton("Start Logging", self)
        self.startLogging_Button.clicked.connect(self.startLogging)
        self.startLogging_Button.setFixedSize(QSize(115, 23))
        self.startLogging_Button.setEnabled(False)

        self.updateDeviceMode_Button = QtWidgets.QPushButton("Update Device Mode", self)
        self.updateDeviceMode_Button.clicked.connect(self.updateDeviceMode)

        # setAutoExclusive method is used to toggle the radio buttons independently.
        self.radio1_Button = QRadioButton("Channel 1", self)
        self.radio1_Button.setAutoExclusive(False)
        self.radio1_Button.toggled.connect(lambda: self.displayPlot1(self.radio1_Button))
        self.radio2_Button = QRadioButton("Channel 2", self)
        self.radio2_Button.setAutoExclusive(False)
        self.radio1_Button.toggled.connect(lambda: self.displayPlot2(self.radio2_Button))
        self.radio3_Button = QRadioButton("Channel 3", self)
        self.radio3_Button.setAutoExclusive(False)
        self.radio1_Button.toggled.connect(lambda: self.displayPlot3(self.radio3_Button))
        self.radio4_Button = QRadioButton("Channel 4", self)
        self.radio4_Button.setAutoExclusive(False)
        self.radio1_Button.toggled.connect(lambda: self.displayPlot4(self.radio4_Button))

        #---------Buttons---------#

        

        #---------Labels---------#

        self.deviceLabel = QtWidgets.QLabel("Device:", self)
        self.deviceModeLabel = QtWidgets.QLabel("Device Mode:", self)
        self.deviceModeText = QtWidgets.QLabel("")

        self.plotRateLabel = QtWidgets.QLabel("Plot Refresh Rate (1/s):", self)

        self.logfileLabel = QtWidgets.QLabel('')

        self.acquisitionLabel = QtWidgets.QLabel("Acquisition time (s):", self)

        # Temporarily shelved labels for Total counts and coincidences
        #self.countsLabel = QtWidgets.QLabel("Total Counts:", self)
        #self.countsLabel.setFont(QFont("Calibri", 28, QFont.Bold))
        #self.countsLabel.setStyleSheet("color:red")
        #self.countsLabel.setAlignment(QtCore.Qt.AlignRight)
        #self.countsLabel.setAlignment(QtCore.Qt.AlignVCenter)

        #self.countsUpdateLabel = QtWidgets.QLabel("", self)   #update with integers live
        #self.countsUpdateLabel.setFont(QFont("Calibri", 28))
        #self.countsUpdateLabel.setText("0")

        #self.coincidencesLabel = QtWidgets.QLabel("Total Coincidences:", self)
        #self.coincidencesLabel.setFont(QFont("Calibri", 28, QFont.Bold))
        #self.coincidencesLabel.setStyleSheet("color:red")
        #self.coincidencesLabel.setAlignment(QtCore.Qt.AlignRight)

        #self.coincidencesUpdateLabel = QtWidgets.QLabel("", self)   #update with integers live
        #self.coincidencesUpdateLabel.setFont(QFont("Calibri", 28))
        #self.coincidencesUpdateLabel.setText("0")

        #---------Labels---------#



        #---------Interactive Fields---------#

        self.plotRateSpinbox = QSpinBox(self)
        self.plotRateSpinbox.setRange(10, 10000)
        self.plotRateSpinbox.valueChanged.connect(self.update_plotRate)

        self.acquisitionSpinBox = QSpinBox(self)
        self.acquisitionSpinBox.setRange(10, 1000000)
        self.acquisitionSpinBox.setValue(300)
        self.acquisitionSpinBox.setSingleStep(300)
        self.acquisitionSpinBox.valueChanged.connect(self.update_TotalTime)

        dev_list = serial_connection.search_for_serial_devices(
            tdc1.TimeStampTDC1.DEVICE_IDENTIFIER)
        self.devCombobox = QComboBox(self)
        self.devCombobox.addItems(dev_list)

        font = QtGui.QFont("Arial", 18)     
        labelStyle = '<span style=\"color:black;font-size:25px\">'

        self.tdcPlot = pg.PlotWidget(title = "Three plot curves")
        self.tdcPlot.setBackground('w')
        self.tdcPlot.setLabel('left', labelStyle + 'Counts')
        self.tdcPlot.setLabel('bottom', labelStyle + 'Sample Number')
        self.tdcPlot.getAxis('left').tickFont = font
        self.tdcPlot.getAxis('bottom').tickFont = font
        self.tdcPlot.getAxis('bottom').setPen(color='k')
        self.tdcPlot.getAxis('left').setPen(color='k')
        self.tdcPlot.showGrid(y=True)

        self.tdcPlot2 = pg.PlotWidget(title = "Coincidences Histogram")
        self.tdcPlot2.setBackground('w')
        self.tdcPlot2.setLabel('left', labelStyle + 'Coincidences')
        self.tdcPlot2.setLabel('bottom', labelStyle + 'Channels')
        self.tdcPlot2.getAxis('left').tickFont = font
        self.tdcPlot2.getAxis('bottom').tickFont = font
        self.tdcPlot2.getAxis('bottom').setPen(color='k')
        self.tdcPlot2.getAxis('left').setPen(color='k')
        self.tdcPlot2.showGrid(y=True)

        # Settings up x-axis (Plot 2)
        self.channelsAxis = ['1-2', '1-3', '1-4', '2-3', '2-4', '3-4']
        self.xdict = dict(enumerate(self.channelsAxis))
        self.tdcPlot2.getAxis('bottom').setTicks([self.xdict.items()])
        self.tdcPlot2.setXRange(0, 5) # Value chosen via trial and error. The interaction between X Range and custom axis intervals is nebulous.

        #---------Interactive Fields---------#


        
        #---------Main Window---------#

        #self.setGeometry(300, 300, 400, 300)
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
        self.grid.addWidget(self.deviceModeText, 0, 3)
        self.grid.addWidget(self.updateDeviceMode_Button, 0, 4)
        #self.grid.addWidget(self.countsLabel, 0, 2, 1, 1)
        #self.grid.addWidget(self.countsUpdateLabel, 0, 3)
        #self.grid.addWidget(self.coincidencesLabel, 1, 2, 1, 1)
        #self.grid.addWidget(self.coincidencesUpdateLabel, 1, 3)
        self.grid.addWidget(self.plotRateLabel, 1, 0)
        self.grid.addWidget(self.plotRateSpinbox, 1, 1)
        self.grid.addWidget(self.acquisitionLabel, 1, 2)
        self.grid.addWidget(self.acquisitionSpinBox, 1, 3)
        self.grid.addWidget(self.liveStart_Button, 2, 0)
        self.grid.addWidget(self.startLogging_Button, 2, 1)
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

        #Timer to update plot (Live Start)
        self.timer = QTimer()
        self.timer.setInterval(self.plot_refresh_rate)
        self.timer.timeout.connect(self.live_update_which_data)

    # Connected to updateDeviceMode_Button
    @QtCore.pyqtSlot()
    def updateDeviceMode(self):
        mode: str = tdc1.TimeStampTDC1.mode()
        self._dev_mode = mode
        self.deviceModeText = mode
    
    # Update plot interval on spinbox value change
    @QtCore.pyqtSlot(int)
    def update_plotRate(self, interval: int):
        self.timer.setInterval(interval)
        self.plot_refresh_rate = interval

    # Update plot index on plot tab change
    @QtCore.pyqtSlot()
    def update_plot_tab(self):
        self._plot_tab = self.tabs.currentIndex()

    # Update total acquisition time on spinbox value change
    @QtCore.pyqtSlot(int)
    def update_TotalTime(self, acq_time: int):
        self.total_time = acq_time

    # Click Live Start button to get started!
    @QtCore.pyqtSlot()
    def liveStart(self):
        # === Add in more functions to reset GUI to base state === #
        #If currently live plotting
        if self.acq_flag is True:
            self.acq_flag = False
            self.timer.stop()
            self.selectLogfile_Button.setEnabled(False)
            self.liveStart_Button.setText("Live Start")
            if self._logfile_name != '':
                self.startLogging_Button.setEnabled(True)
        #If not currently live plotting
        else:
            self.acq_flag = True
            self.timer.start()
            self.x = []
            self.y1 = []
            self.y2 = []
            self.y3 = []
            self.y4 = []
            self.x0 = list(self.xdict.keys())
            self.y0 = []
            self.selectLogfile_Button.setEnabled(True)
            self.liveStart_Button.setText("Live Stop")

    # Logging
    @QtCore.pyqtSlot()
    def selectLogfile(self):
        default_filetype = 'csv'
        start = datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss ") + "_TDC1." + default_filetype
        self._logfile_name = QtGui.QFileDialog.getSaveFileName(
            self, "Save to log file", start)[0]
        self.logfileLabel.setText(self._logfile_name)
        if self.timer.isActive() == False and self._logfile_name != '':
            self.startLogging_Button.setEnabled(True)

    @QtCore.pyqtSlot()
    def startLogging(self):
        """[summary]
        Slot for startLogging button. Starts/stops logging depending on the state of the button when clicked.
        """
        slbtext = self.startLogging_Button.text()

        if slbtext == "Start Logging":
            self.startLogging_Button.setText("Stop Logging")
            self.log_flag = True
            self.liveStart_Button.setEnabled(False)
            self.selectLogfile_Button.setEnabled(False)
            self.logging_requested.emit(self.integration_time, self._logfile_name, self.total_time, \
            self.sampling_rate, self.device_path, self.log_flag, self._dev_mode)
        elif slbtext == "Stop Logging":
            self.startLogging_Button.setText("Start Logging")
            self.log_flag = False
            self.liveStart_Button.setEnabled(True)
            self.selectLogfile_Button.setEnabled(True)
            self.logger_thread = None
            
    # Plotting without logging
    # Connected to timer.timeout
    def live_update_which_data(self):
        if self._dev_mode = 'singles':
            self.live_update_counts_data
        elif self._dev_mode = 'pairs':
            self.live_update_coincidences_data

    def live_update_counts_data(self):
        counts, _ = self._tdc1_dev.get_counts(self.total_time)   # === get counts from tdc1 === # 
        self.drawPlot(counts)

    def live_update_coincidences_data(self):
        #coincidences, _ = self._tdc1_dev.get_pairs()
        self.drawPlot2(coincidences)

    # Plotting with logging
    # Connected to worker.data_is_logged, which is emitted by the worker every loop. This function then determines 
    # which graph to plot.
    @QtCore.pyqtSlot(tuple, str)
    def drawWhichPlot(self, data: tuple, dev_mode: str):
        if dev_mode == 'singles':
            self.drawPlot(data)
        elif dev_mode == 'pairs':
            self.drawPlot2(data)

    def drawPlot(self, counts: tuple):
        """[summary]
        Plots up to 4 graphs on the same graph widget. Number of graphs displayed can be toggled with individual radio buttons.
        Args:
            counts (tuple): tuple of counts from channel 1 to 4
        """
        if len(self.x) == PLT_SAMPLES:
            self.x = self.x[1:]
            self.x.append(self.x[-1] + 1)
            self.y1 = self.y1[1:]
            self.y2 = self.y2[1:]
            self.y3 = self.y3[1:]
            self.y4 = self.y4[1:]
        else:
            self.x.append(len(self.x) + 1) # Takes care of empty list case as well
        self.y1.append(counts[0])
        self.y2.append(counts[1])
        self.y3.append(counts[2])
        self.y4.append(counts[3])

        self.lineStyle1 = pg.mkPen(width=2, color='r') # Red
        self.lineStyle2 = pg.mkPen(width=2, color='g') # Green
        self.lineStyle3 = pg.mkPen(width=2, color='b') # Blue
        self.lineStyle4 = pg.mkPen(width=2, color='k') # Black
        self.y_range = max(max(self.y1), max(self.y2), max(self.y3), max(self.y4)) * 1.2

        # Plotting the graph - https://pyqtgraph.readthedocs.io/en/latest/plotting.html for organisation of plotting classes
        # Take note: multiple plotDataItems can sit on one plotWidget
        self.tdcPlot.setYRange(self.y_range)
        self.linePlot1 = self.tdcPlot.plot(self.x, self.y1, pen=self.lineStyle1)
        self.linePlot2 = self.tdcPlot.plot(self.x, self.y2, pen=self.lineStyle2)
        self.linePlot3 = self.tdcPlot.plot(self.x, self.y3, pen=self.lineStyle3)
        self.linePlot4 = self.tdcPlot.plot(self.x, self.y4, pen=self.lineStyle4)

    # Radio button slots (functions)
    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot1(self, b: QRadioButton):
        if b.isChecked:
            self.linePlot1.setPen(self.lineStyle1)
        else:
            self.linePlot1.setPen(None)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot2(self, b: QRadioButton):
        if b.isChecked:
            self.linePlot2.setPen(self.lineStyle2)
        else:
            self.linePlot2.setPen(None)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot3(self, b: QRadioButton):
        if b.isChecked:
            self.linePlot3.setPen(self.lineStyle3)
        else:
            self.linePlot3.setPen(None)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def displayPlot4(self, b: QRadioButton):
        if b.isChecked:
            self.linePlot4.setPen(self.lineStyle4)
        else:
            self.linePlot4.setPen(None)
    
    # Connected to worker.coincidences_data_logged signal(pyqt_pyobject) -> Probably a list/tuple, check with Mathias
    # Histogram
    def drawPlot2(self, coincidences: tuple):

        self.y0 = self.y0 + list(coincidences)
        lineStyle = pg.mkPen(width=2, color='r')

        # Plotting the graph
        self.histogramPlot = self.tdcPlot2.plot(self.x0, self.y0, pen=lineStyle, symbol = 'x', symbolPen = 'b', symbolBrush = 0.2)


    #@QtCore.pyqtSlot()
    # Consider using numpy arrays
    #def start_pwr_plot(self):
        # Plot 1
    #    self.x = []
    #    self.y1 = []
    #    self.y2 = []
    #    self.y3 = []
    #    self.y4 = []
    #    # Plot 2
    #    self.x0 = list(self.xdict.keys())
    #    self.y0 = []
    #    self._prev_pwr = 0
    #    self._tdc1_dev = tdc1.TimeStampTDC1(self.comboBox.currentText())
    #    self.timer.start()
    #   return


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
# 3. 


######################
# Questions          #
######################
# 1. Line 250 - What is PLT Samples? Why is it 500?
# 2. Line 222 - What is 'start' argument for?
