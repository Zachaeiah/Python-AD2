import ctypes                     # import the C compatible data types
from sys import platform, path    # this is needed to check the OS type and get the PATH
from os import sep                # OS specific file path separators

# load the dynamic library, get constants path (the path is OS specific)
if platform.startswith("win"):
    # on Windows
    dwf = ctypes.cdll.dwf
    constants_path = "C:" + sep + "Program Files (x86)" + sep + "Digilent" + sep + "WaveFormsSDK" + sep + "samples" + sep + "py"
elif platform.startswith("darwin"):
    # on macOS
    lib_path = sep + "Library" + sep + "Frameworks" + sep + "dwf.framework" + sep + "dwf"
    dwf = ctypes.cdll.LoadLibrary(lib_path)
    constants_path = sep + "Applications" + sep + "WaveForms.app" + sep + "Contents" + sep + "Resources" + sep + "SDK" + sep + "samples" + sep + "py"
else:
    # on Linux
    dwf = ctypes.cdll.LoadLibrary("libdwf.so")
    constants_path = sep + "usr" + sep + "share" + sep + "digilent" + sep + "waveforms" + sep + "samples" + sep + "py"
 
# import constants
path.append(constants_path)

import dwfconstants as constants
import device
 
def open_AD2():
    """
        open the first available device
    """
    # this is the device handle - it will be used by all functions to "address" the connected device
    device_handle = ctypes.c_int()

    # connect to the first available device
    dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(device_handle))
    data.handle = device_handle
    return data

def open_oscilloscope(device_data, sampling_frequency=20e06, buffer_size=8921, offset=0, amplitude_range=50):
    """
        initialize the oscilloscope
        parameters: - device data
                    - sampling frequency in Hz, default is 20MHz
                    - buffer size, default is 8192
                    - offset voltage in Volts, default is 0V
                    - amplitude range in Volts, default is ±5V
    """
    # enable all channels
    dwf.FDwfAnalogInChannelEnableSet(device_data.handle, ctypes.c_int(0), ctypes.c_bool(True))
 
    # set offset voltage (in Volts)
    dwf.FDwfAnalogInChannelOffsetSet(device_data.handle, ctypes.c_int(0), ctypes.c_double(offset))
 
    # set range (maximum signal amplitude in Volts)
    dwf.FDwfAnalogInChannelRangeSet(device_data.handle, ctypes.c_int(0), ctypes.c_double(amplitude_range))
 
    # set the buffer size (data point in a recording)
    dwf.FDwfAnalogInBufferSizeSet(device_data.handle, ctypes.c_int(buffer_size))
 
    # set the acquisition frequency (in Hz)
    dwf.FDwfAnalogInFrequencySet(device_data.handle, ctypes.c_double(sampling_frequency))
 
    # disable averaging (for more info check the documentation)
    dwf.FDwfAnalogInChannelFilterSet(device_data.handle, ctypes.c_int(-1), constants.filterDecimate)
    #data.sampling_frequency = sampling_frequency
    #data.buffer_size = buffer_size
    return

def measure_oscilloscope(device_data, channel):
    """
        measure a voltage
        parameters: - device data
                    - the selected oscilloscope channel (1-2, or 1-4)
 
        returns:    - the measured voltage in Volts
    """
    # set up the instrument
    dwf.FDwfAnalogInConfigure(device_data.handle, ctypes.c_bool(False), ctypes.c_bool(False))
 
    # read data to an internal buffer
    dwf.FDwfAnalogInStatus(device_data.handle, ctypes.c_bool(False), ctypes.c_int(0))
 
    # extract data from that buffer
    voltage = ctypes.c_double()   # variable to store the measured voltage
    dwf.FDwfAnalogInStatusSample(device_data.handle, ctypes.c_int(channel - 1), ctypes.byref(voltage))
 
    # store the result as float
    voltage = voltage.value
    return voltage

def record_oscilloscope(device_data, channel):
    """
        record an analog signal
        parameters: - device data
                    - the selected oscilloscope channel (1-2, or 1-4)
        returns:    - buffer - a list with the recorded voltages
                    - time - a list with the time moments for each voltage in seconds (with the same index as "buffer")
    """
    # set up the instrument
    dwf.FDwfAnalogInConfigure(device_data.handle, ctypes.c_bool(False), ctypes.c_bool(True))
 
    # read data to an internal buffer
    while True:
        status = ctypes.c_byte()    # variable to store buffer status
        dwf.FDwfAnalogInStatus(device_data.handle, ctypes.c_bool(True), ctypes.byref(status))
 
        # check internal buffer status
        if status.value == constants.DwfStateDone.value:
                # exit loop when ready
                break
 
    # copy buffer
    buffer = (ctypes.c_double * data.buffer_size)()   # create an empty buffer
    dwf.FDwfAnalogInStatusData(device_data.handle, ctypes.c_int(channel - 1), buffer, ctypes.c_int(data.buffer_size))
 
    # calculate aquisition time
    time = range(0, data.buffer_size)
    time = [moment / data.sampling_frequency for moment in time]
 
    # convert into list
    buffer = [float(element) for element in buffer]
    return buffer, time

def close_oscilloscope(device_data):
    """
        reset the scope
    """
    dwf.FDwfAnalogInReset(device_data.handle)
    return

class function:
    """ function names """
    custom = constants.funcCustom
    sine = constants.funcSine
    square = constants.funcSquare
    triangle = constants.funcTriangle
    noise = constants.funcNoise
    dc = constants.funcDC
    pulse = constants.funcPulse
    trapezium = constants.funcTrapezium
    sine_power = constants.funcSinePower
    ramp_up = constants.funcRampUp
    ramp_down = constants.funcRampDown

def generate_function(device_data, channel, function, offset, frequency=1e03, amplitude=1, symmetry=50, wait=0, run_time=0, repeat=0, data=[]):
    """
        generate an analog signal
        parameters: - device data
                    - the selected wavegen channel (1-2)
                    - function - possible: custom, sine, square, triangle, noise, ds, pulse, trapezium, sine_power, ramp_up, ramp_down
                    - offset voltage in Volts
                    - frequency in Hz, default is 1KHz
                    - amplitude in Volts, default is 1V
                    - signal symmetry in percentage, default is 50%
                    - wait time in seconds, default is 0s
                    - run time in seconds, default is infinite (0)
                    - repeat count, default is infinite (0)
                    - data - list of voltages, used only if function=custom, default is empty
    """
    # enable channel
    channel = ctypes.c_int(channel - 1)
    dwf.FDwfAnalogOutNodeEnableSet(device_data.handle, channel, constants.AnalogOutNodeCarrier, ctypes.c_bool(True))
 
    # set function type
    dwf.FDwfAnalogOutNodeFunctionSet(device_data.handle, channel, constants.AnalogOutNodeCarrier, function)
 
    # load data if the function type is custom
    if function == constants.funcCustom:
        data_length = len(data)
        buffer = (ctypes.c_double * data_length)()
        for index in range(0, len(buffer)):
            buffer[index] = ctypes.c_double(data[index])
        dwf.FDwfAnalogOutNodeDataSet(device_data.handle, channel, constants.AnalogOutNodeCarrier, buffer, ctypes.c_int(data_length))
 
    # set frequency
    dwf.FDwfAnalogOutNodeFrequencySet(device_data.handle, channel, constants.AnalogOutNodeCarrier, ctypes.c_double(frequency))
 
    # set amplitude or DC voltage
    dwf.FDwfAnalogOutNodeAmplitudeSet(device_data.handle, channel, constants.AnalogOutNodeCarrier, ctypes.c_double(amplitude))
 
    # set offset
    dwf.FDwfAnalogOutNodeOffsetSet(device_data.handle, channel, constants.AnalogOutNodeCarrier, ctypes.c_double(offset))
 
    # set symmetry
    dwf.FDwfAnalogOutNodeSymmetrySet(device_data.handle, channel, constants.AnalogOutNodeCarrier, ctypes.c_double(symmetry))
 
    # set running time limit
    dwf.FDwfAnalogOutRunSet(device_data.handle, channel, ctypes.c_double(run_time))
 
    # set wait time before start
    dwf.FDwfAnalogOutWaitSet(device_data.handle, channel, ctypes.c_double(wait))
 
    # set number of repeating cycles
    dwf.FDwfAnalogOutRepeatSet(device_data.handle, channel, ctypes.c_int(repeat))
 
    # start
    dwf.FDwfAnalogOutConfigure(device_data.handle, channel, ctypes.c_bool(True))
    return

def close_function(device_data, channel=0):
    """
        reset a wavegen channel, or all channels (channel=0)
    """
    channel = ctypes.c_int(channel - 1)
    dwf.FDwfAnalogOutReset(device_data.handle, channel)
    return

def _switch_variable_(device_data, master_state, positive_state, negative_state, positive_voltage, negative_voltage):
    """
        turn the power supplies on/off
        parameters: - device data
                    - master switch - True = on, False = off
                    - positive supply switch - True = on, False = off
                    - negative supply switch - True = on, False = off
                    - positive supply voltage in Volts
                    - negative supply voltage in Volts
    """
    # set positive voltage
    positive_voltage = max(0, min(5, positive_voltage))
    dwf.FDwfAnalogIOChannelNodeSet(device_data.handle, ctypes.c_int(0), ctypes.c_int(1), ctypes.c_double(positive_voltage))
 
    # set negative voltage
    negative_voltage = max(-5, min(0, negative_voltage))
    dwf.FDwfAnalogIOChannelNodeSet(device_data.handle, ctypes.c_int(1), ctypes.c_int(1), ctypes.c_double(negative_voltage))
 
    # enable/disable the positive supply
    dwf.FDwfAnalogIOChannelNodeSet(device_data.handle, ctypes.c_int(0), ctypes.c_int(0), ctypes.c_int(positive_state))
 
    # enable the negative supply
    dwf.FDwfAnalogIOChannelNodeSet(device_data.handle, ctypes.c_int(1), ctypes.c_int(0), ctypes.c_int(negative_state))
 
    # start/stop the supplies - master switch
    dwf.FDwfAnalogIOEnableSet(device_data.handle, ctypes.c_int(master_state))
    return

def _switch_variable_(device_data, master_state, positive_state, negative_state, positive_voltage, negative_voltage):
    """
        turn the power supplies on/off
        parameters: - device data
                    - master switch - True = on, False = off
                    - positive supply switch - True = on, False = off
                    - negative supply switch - True = on, False = off
                    - positive supply voltage in Volts
                    - negative supply voltage in Volts
    """
    # set positive voltage
    positive_voltage = max(0, min(5, positive_voltage))
    dwf.FDwfAnalogIOChannelNodeSet(device_data.handle, ctypes.c_int(0), ctypes.c_int(1), ctypes.c_double(positive_voltage))
 
    # set negative voltage
    negative_voltage = max(-5, min(0, negative_voltage))
    dwf.FDwfAnalogIOChannelNodeSet(device_data.handle, ctypes.c_int(1), ctypes.c_int(1), ctypes.c_double(negative_voltage))
 
    # enable/disable the positive supply
    dwf.FDwfAnalogIOChannelNodeSet(device_data.handle, ctypes.c_int(0), ctypes.c_int(0), ctypes.c_int(positive_state))
 
    # enable the negative supply
    dwf.FDwfAnalogIOChannelNodeSet(device_data.handle, ctypes.c_int(1), ctypes.c_int(0), ctypes.c_int(negative_state))
 
    # start/stop the supplies - master switch
    dwf.FDwfAnalogIOEnableSet(device_data.handle, ctypes.c_int(master_state))
    return

def close(device_data):
    """
        close a specific device
    """
    dwf.FDwfDeviceClose(device_data.handle)
    return

def main():

    ramp_measurements = []
    opamp_measurements = []
    Times = []
    power_up = -5
    amplitude = 5
    amplitude_slope = 0.05
    rmap_steps = int(amplitude/amplitude_slope)
    time_per_measurement = 1e-6
    cycles = 1

    fliped = False

    # connect to the device
    device_data = device.open()
    time.sleep(0.5)

    #open_oscilloscope
    open_oscilloscope(device_data)

    _switch_variable_(device_data = device_data, master_state = True, positive_state = True, negative_state = True, positive_voltage = 5, negative_voltage = -5)
    time.sleep(0.5)

    print("starting")

    # Setup function generater
    generate_function(device_data = device_data, channel = 1, function = function.dc, offset = power_up, frequency=0, amplitude=0)
    time.sleep(0.5)

    #begin timer
    start_time = time.time()

    for j in range(0, cycles, 1):

        for i in range(0, rmap_steps*2 , 1):
            # measure oscilloscope on channel 1
            measurement = measure_oscilloscope(device_data = device_data, channel = 1)
            ramp_measurements.append(measurement)

            """
                make op-amp measurements for VTD
            """

            # measure oscilloscope on channel 2
            measurement = measure_oscilloscope(device_data = device_data, channel = 2)
            opamp_measurements.append(measurement)
            """
                make op-amp measurements for VTD
            """

            # increase voltage input
            power_up += amplitude_slope
            generate_function(device_data = device_data, channel = 1, function = function.dc, offset = power_up, frequency=0, amplitude=0)

            # take time measurement
            Times.append((time.time() - start_time))

            # delay between measurements
            time.sleep(time_per_measurement)

        for i in range(0, rmap_steps*2 , 1):

            # measure oscilloscope on channel 1
            measurement = measure_oscilloscope(device_data = device_data, channel = 1)
            ramp_measurements.append(measurement)

            """
                make op-amp measurements for VTD
            """

            # measure oscilloscope on channel 2
            measurement = measure_oscilloscope(device_data = device_data, channel = 2)
            opamp_measurements.append(measurement)

            """
                make op-amp measurements for VTD
            """

            # decrease voltage input
            power_up -= amplitude_slope
            generate_function(device_data = device_data, channel = 1, function = function.dc, offset = power_up, frequency=0, amplitude=0)
            
            # take time measurement
            Times.append((time.time() - start_time))

            # delay between measurements
            time.sleep(time_per_measurement)

        print(f"Cycle #{j+1} Time:{time.time() - start_time}")

    fig, axis = plt.subplots(2,1, figsize=(8,8))

    ax = axis[0]

    ax.set_xlim(min(Times), max(Times))
    ax.set_ylim(min(ramp_measurements), max(ramp_measurements))

    ax.xaxis.set_major_formatter(FormatStrFormatter('% 1.1f'))
   
    ax.set_title("Vin Vs Vout")

    ax.set_xlabel("Time [S]", fontsize=16)
    ax.set_ylabel("Voltage [V]", fontsize=16)

    ax.plot(Times, ramp_measurements,label='V_in', color = 'blue', linewidth = 1)
    ax.plot(Times, opamp_measurements,label='V_out', color = 'orange', linewidth = 1)

    ax.legend(fontsize=10, fancybox=False, edgecolor='black', bbox_to_anchor =(1.1, 1))


    ax = axis[1]

    ax.set_xlim(0, max(ramp_measurements))
    ax.set_ylim(min(opamp_measurements), max(opamp_measurements))

    ax.xaxis.set_major_formatter(FormatStrFormatter('% 1.1f'))
   
    ax.set_title("VTD of V_out")

    ax.set_xlabel("V_in [V]", fontsize=16)
    ax.set_ylabel("V_out [V]", fontsize=16)

    ax.set_xticks(np.linspace(0,5,20))
    ax.set_yticks(np.linspace(-5,5,10))

    ax.plot(ramp_measurements, opamp_measurements,label='V_out', color = 'green', linewidth = 1)

    ax.legend(fontsize=10, fancybox=False, edgecolor='black', bbox_to_anchor =(1.1, 1))

    fig.tight_layout()
    plt.show()

    close_function(device_data, channel = 1)
    close_oscilloscope(device_data)
    close(device_data)

    data = [(Times[i], ramp_measurements[i], opamp_measurements[i]) for i in range(0, len(Times), 1)]
    print(data)

if __name__ == "__main__":
    main()

