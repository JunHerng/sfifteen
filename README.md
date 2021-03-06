# sfifteen tdc1 GUI (1.1)

INSTALLATION

1. Follow instructions at https://github.com/s-fifteen-instruments/pyS15 and install S15lib python package.
2. Other package requirements: numpy, pyqt5, pyqtgraph, datetime, time.
3. Run tdc1_gui.py with your compiler of choice (This GUI was developed in Visual Studio Code with Python 3.9.2 64-bit). 

![image](https://user-images.githubusercontent.com/52197879/124213246-cecf5f80-db22-11eb-932d-57dfb3ce32bd.png)

HOW TO USE

1. Ensure device is connected to PC.
2. Select Device from drop down menu.
3. Select GUI Mode - singles/pairs. (This is NOT equivalent to the TDC1 mode. For instance the pairs mode uses the TDC1's timestamp mode (3) for its g2 calculations. The modes correspond to the tabs - singles:counts, pairs:coincidences.)
4. Select Logfile if logging is desired. Leave empty if not desired.
5. Select Integration time (singles) / acquisition time (pairs) by pressing the arrows or typing in manually.
6. Select Plot Samples. This determines how many data points to display on the graph at once.
7. If in Pairs mode, select start and stop channel (Default Start:1, Stop:3), histogram bin width.
8. Hit 'Live Start' button.
9. If in singles mode, select the respective radio buttons to see the plots.
10. If in pairs mode, switch to the 'coincidences' tab to view the histogram. The value in the 'Center' spin box allows you to set the center of the histogram display if you already have a rough idea of the expected time delays in your experimental setup.
![image](https://user-images.githubusercontent.com/52197879/124213839-da6f5600-db23-11eb-8de3-9a1dae546236.png)
11. Use mouse to interact with the graph - Click and drag to pan, scroll to zoom, right click for more viewing options.
