"""
Home screen
===========

Module storing an implementation of a home screen and all values associated with it.
"""
from ..common import get_hardware_info, Log, dm
from .utils import Screen, Colour, get_manager, new_camera_update_func
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *


# Declare screen-specific clock intervals for the indicators
HARDWARE_READINGS_INTERVAL = 3000
CONNECTION_READINGS_INTERVAL = 1000

# Declare the initial reading to display on the indicators
DEFAULT_READING = "_"


class _Indicator(QWidget):
    """
    Indicator widget used to represent a single indicator.

    Functions
    ---------

    The following list shortly summarises each function:

        * __init__ - a constructor to create the widget and all associated values
        * text - a property to access text in the body
        * _set_style - method used to update the style of an indicator
        * _set_text - method used to format and update text in the body (exposed via `text` property)

    Usage
    -----

    You should create an indicator and set it's header and body (footer is optional)::

        ind = _Indicator("Header (title)", "{}% (body)", "Footer (optional)")

    The indicator should then be added to the :class:`_Indicators` class to be displayed on the screen.

    ..warning::

        You must include "{}" placeholder in the indicator's body.
    """

    def __init__(self, header: str, body: str, footer: str = ""):
        """
        Standard constructor.

        :param header: Header text displayed above the values
        :param body: Body containing the values
        :param footer: Footer text displayed below the values, empty by default
        :raises: ValueError on missing placeholder
        """
        super(_Indicator, self).__init__()

        # Raise an error early if no placeholder in body
        if "{}" not in body:
            raise ValueError("Indicator's body must include \"{}\" placeholder characters")

        # Remember passed values and initialise the display text (body with substituted placeholder)
        self._header = header
        self._body = body
        self._footer = footer
        self._text = ""

        # Create the QT objects and set the layout
        self._layout = QVBoxLayout()
        self._header_label = QLabel()
        self._body_label = QLabel()
        self._footer_label = QLabel()
        self._layout.addWidget(self._header_label)
        self._layout.addWidget(self._body_label)
        self._layout.addWidget(self._footer_label)
        self.setLayout(self._layout)

        # Set the style and initially update the visible items to
        self._set_style()
        self._header_label.setText(self._header)
        self._footer_label.setText(self._footer)
        self._set_text(DEFAULT_READING)

    @property
    def text(self) -> str:
        """
        Getter for unformatted, but with the placeholder replaced, text
        """
        return self._text

    @text.setter
    def text(self, value):
        """
        Setter for the body text.

        Sets both str and QT versions.

        :param value: New text to display
        """
        self._text = self._body.format(value)
        self._set_text(value)

    def _set_style(self):
        """
        Styling method used to ensure all items are visually matching the expected outcome.
        """
        r, g, b, _ = Colour.ACCENT.value

        # Set the alignments to center, to display all text in the middle
        self._body_label.setAlignment(Qt.AlignCenter)
        self._header_label.setAlignment(Qt.AlignHCenter)
        self._footer_label.setAlignment(Qt.AlignHCenter)

        # Set spacing to 0 to remove the default margin
        self._layout.setSpacing(0)

        # Expanding size policy allows the widget to take full available space in the layout
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Each element has its own style sheet for maximum flexibility
        self.setStyleSheet(f"""
            QWidget {{ 
                background-color: rgb({r}, {g}, {b});
            }}""")
        self._header_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 30px;
            }""")
        self._footer_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 30px;
            }""")
        self._body_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 60px;
            }""")

        # Make sure the body takes as much of the space as possible by making the header and footer as small as possible
        self._header_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self._footer_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        # Rich text flag is mandatory due to the HTML code injections within the label's text
        self._body_label.setTextFormat(Qt.RichText)

    def _set_text(self, value):
        """
        Formats and updates passed text to display it as the indicator's body.

        :param value: New text to be displayed
        """

        # Text must be formatted in QT-parsable format, to apply styling on the fly.
        index = self._body.rfind("{}") + 2
        text = self._body[:index] + "<span style=\"font-size:30px;\">" + self._body[index:] + "</span>"
        text = text.replace("\n", "<br>")

        # Replace placeholder "{}" with passed value
        text = text.format(value)

        # Update the indicator's body
        self._body_label.setText(text)


class _Indicators(QHBoxLayout):
    """
    Indicators class used to store all indicators in a horizontal layout.

    Functions
    ---------

    The following list shortly summarises each function:

        * __init__ - a constructor to create all indicators and add them to the layout
        * hardware - getter for hardware indicators
        * connections - getter for connection indicators

    """

    class _HardwareIndicators:
        """
        Helper class used to bundle hardware-related indicators.

        Exposes update function to update the indicators correctly.
        """

        def __init__(self):
            """
            Standard constructor.
            """
            self._processes = _Indicator("Processes", "{}")
            self._threads = _Indicator("Threads", "{}")
            self._cpu = _Indicator("CPU", "{}%")
            self._memory = _Indicator("Memory", "{}%")

            self.indicators = [self._processes, self._threads, self._cpu, self._memory]

        def update(self):
            """
            Method used to update hardware indicators' values.
            """
            processes, threads, cpu_load, memory_usage = get_hardware_info(get_manager().references.parent_pid)
            Log.hardware(processes, threads, cpu_load, memory_usage)

            self._processes.text = processes
            self._threads.text = threads
            self._cpu.text = cpu_load
            self._memory.text = memory_usage

    class _ConnectionIndicators:
        """
        Helper class used to bundle connection-related indicators.

        Exposes update function to update the indicators correctly.
        """

        def __init__(self):
            """
            Standard constructor.
            """
            self._pi = _Indicator("Raspberry Pi", "{}", "Status")
            self._ard_o = _Indicator("Arduino O", "{}", "Reachable?")
            self._ard_i = _Indicator("Arduino I", "{}", "Reachable?")
            self._ard_o_status = _Indicator("Arduino O", "{}", "Status")
            self._ard_i_status = _Indicator("Arduino I", "{}", "Status")

            # TODO: Access violation because there is no method in place at the moment to automatically scale things
            #  correctly, and leave them in a fixed width state
            self._pi._body_label.setStyleSheet("""
                        QLabel {
                            color: white;
                            font-size: 20px;
                        }""")

            self.indicators = [self._pi, self._ard_o, self._ard_i, self._ard_o_status, self._ard_i_status]

        def update(self):
            """
            Method used to update connection indicators' values.
            """
            pi_status = get_manager().references.connection.status.name
            o_connection, i_connection = dm.received["A_O"], dm.received["A_I"]
            o_status, i_status = dm.received["S_O"], dm.received["S_I"]

            self._pi.text = pi_status
            self._ard_o.text = o_connection
            self._ard_i.text = i_connection
            self._ard_o_status.text = o_status
            self._ard_i_status.text = i_status

    def __init__(self):
        """
        Standard constructor.

        Stores each list of indicators and adds all widgets within them to itself.
        """
        super(_Indicators, self).__init__()
        self._hardware_indicators = self._HardwareIndicators()
        self._connection_indicators = self._ConnectionIndicators()

        for indicator in self._hardware_indicators.indicators + self._connection_indicators.indicators:
            self.addWidget(indicator)

    @property
    def hardware(self) -> _HardwareIndicators:
        """
        Getter for hardware indicators
        """
        return self._hardware_indicators

    @property
    def connections(self) -> _ConnectionIndicators:
        """
        Getter for connection indicators
        """
        return self._connection_indicators


class Home(Screen):
    """
    Home screen used to display 3 main video streams and various indicators with the information about CPU, memory
    and the connections' statuses.

    Functions
    ---------

    The following list shortly summarises each function:

        * __init__ - a constructor to create all QT objects and class-specific fields
        * _config - a method to place all items created in __init__
        * _set_style - a method to re-style some of the components to display correctly
        * post_init - default implementation of the inherited method
        * on_switch - a method which connects the stream slots on switch and starts system-wide and home-specific clocks
        * on_exit - a method which disconnects the slots on exit and stops some of the clocks
        * _update_main_camera - helper function to display main camera's frame
        * _update_top_camera - helper function to display top camera's frame
        * _update_bottom_camera - helper function to display bottom camera's frame

    Usage
    -----

    This screen can be switched to as many times as needed.
    """

    def __init__(self):
        """
        Standard constructor.
        """
        super(Home, self).__init__()

        # Clocks used to update the sensor readings and the connections
        self._hardware_readings_clock = QTimer()
        self._connection_readings_clock = QTimer()

        # Basic layout consists of vertical box layout, within which there are two rows (cameras and indicators)
        self._layout = QVBoxLayout()
        self._cameras = QGridLayout()
        self._indicators = _Indicators()

        # Within the cameras section, there are 3 cameras provided (main and two side cameras)
        self._main_camera = QLabel()
        self._top_camera = QLabel()
        self._bottom_camera = QLabel()

        # Create the video stream frame update functions
        self._update_main_camera = new_camera_update_func(self._main_camera, "Main in Home")
        self._update_top_camera = new_camera_update_func(self._top_camera, "Top-facing in Home")
        self._update_bottom_camera = new_camera_update_func(self._bottom_camera, "Bottom-facing in Home")

        self._config()
        self.setLayout(self._layout)

    def _config(self):
        """
        Standard configuration method.
        """
        super()._config()

        # Main camera takes the height of 2 side cameras and 2/3 of the width of the screen
        self._cameras.addWidget(self._main_camera, 0, 0, 2, 1)
        self._cameras.addWidget(self._top_camera, 0, 1)
        self._cameras.addWidget(self._bottom_camera, 1, 1)
        self._cameras.setColumnStretch(0, 2)
        self._cameras.setColumnStretch(1, 1)

        # Cameras take 3/4 of the height of the screen
        self._layout.addLayout(self._cameras)
        self._layout.addLayout(self._indicators)
        self._layout.setStretch(0, 3)
        self._layout.setStretch(1, 1)

        # Connect the clock timers to the functions
        self._hardware_readings_clock.setInterval(HARDWARE_READINGS_INTERVAL)
        self._hardware_readings_clock.timeout.connect(self._indicators.hardware.update)
        self._connection_readings_clock.setInterval(CONNECTION_READINGS_INTERVAL)
        self._connection_readings_clock.timeout.connect(self._indicators.connections.update)

    def _set_style(self):
        """
        Standard styling method.
        """
        super()._set_style()

        # The cameras should take as much space as possible (frames get scaled anyway)
        self._main_camera.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._top_camera.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._bottom_camera.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def post_init(self):
        """
        Default inherited.
        """
        super().post_init()

    def on_switch(self):
        """
        This screen is accessed immediately after the loading screen, hence it will have a lot of start-up
        functionalities. Currently the following are implemented:

            1. Display the menu bar (and the line break) as it should only be disabled in the loading screen.
            2. Start the connection check clock
            3. Start the hardware readings clock for indicators
            4. Connect the stream slots to the functions emitting frame signals
        """
        super().on_switch()

        # Set/Start global items - connections checker and menu bar
        self.manager.bar.setVisible(True)
        self.manager.line_break.setVisible(True)
        self.manager.references.connection_clock.start()

        # Initially update the readings
        self._indicators.hardware.update()
        self._indicators.connections.update()

        # Start indicator clocks
        self._hardware_readings_clock.start()
        self._connection_readings_clock.start()

        # Connect stream slots
        self.manager.references.main_camera.frame_received.connect(self._update_main_camera)
        self.manager.references.top_camera.frame_received.connect(self._update_top_camera)
        self.manager.references.bottom_camera.frame_received.connect(self._update_bottom_camera)

    def on_exit(self):
        """
        Stop the clocks and disconnect the streams.
        """
        super().on_exit()

        # Stop indicator clocks
        self._hardware_readings_clock.stop()
        self._connection_readings_clock.stop()

        # Disconnect stream slots
        self.manager.references.main_camera.frame_received.disconnect(self._update_main_camera)
        self.manager.references.top_camera.frame_received.disconnect(self._update_top_camera)
        self.manager.references.bottom_camera.frame_received.disconnect(self._update_bottom_camera)
