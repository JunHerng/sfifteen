# sfifteen tdc1 GUI (1.0)

INSTALLATION

1. Follow instructions at https://github.com/s-fifteen-instruments/pyS15 and install S15lib python package.
2. Other package requirements: numpy, pyqt5, pyqtgraph, datetime, time.
3. Run tdc1_gui.py.

HOW TO USE

1. Ensure device is connected to PC.
2. Select device port from drop down menu.
3. Select mode - singles/pairs. (This is NOT equivalent to the TDC1 mode. For instance the pairs mode uses the TDC1's timestamp mode (3) for its g2 calculations. The modes correspond to the tabs - singles:counts, pairs:coincidences.)
4. Select log file if logging is desired. Leave empty if not desired.
5. Select integration time (singles) / acquisition time (pairs) by pressing the arrows or typing in manually.
6. Hit 'Live Start' button.
7. If in singles mode, select the respective radio buttons to see the plots.
8. If in pairs mode, switch to the 'coincidences' tab to view the histogram.
9. Use mouse to interact with the graph - Click and drag to pan, scroll to zoom, right click for more viewing options.
