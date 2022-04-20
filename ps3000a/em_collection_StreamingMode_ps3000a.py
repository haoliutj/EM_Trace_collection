#
# Copyright (C) 2018-2020 Pico Technology Ltd. See LICENSE file for terms.
#
# PS3000 Series (A API) STREAMING MODE EXAMPLE
# This example demonstrates how to call the ps3000a driver API functions in order to open a device, setup 1 channel (i.e. channel A) and collects streamed data (1 buffer).
# This data is then plotted as mV against time in ns.

# This is function borrowed from ps3000aStreamingExample.py and customized to automatically collect data and return data
# return sampled data as np.array

import ctypes
import numpy as np
from picosdk.ps3000a import ps3000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok
import time as time_handle
import os


def data_collect(plt_flag=False):
    """
    automatically collect data through ps3000a (e.g., ps3206D)
    return sampled data as np.array
    """
    
    # Create chandle and status ready for use
    chandle = ctypes.c_int16()
    status = {}

    # Open PicoScope 3000 Series device
    status["openunit"] = ps.ps3000aOpenUnit(ctypes.byref(chandle), None)

    try:
        assert_pico_ok(status["openunit"])
    except: # PicoNotOkError:

        powerStatus = status["openunit"]

        if powerStatus == 286:
            status["changePowerSource"] = ps.ps3000aChangePowerSource(chandle, powerStatus)
        elif powerStatus == 282:
            status["changePowerSource"] = ps.ps3000aChangePowerSource(chandle, powerStatus)
        else:
            raise

        assert_pico_ok(status["changePowerSource"])


    enabled = 1
    disabled = 0
    analogue_offset = 0.0

    # Set up channel A
    # handle = chandle
    # channel = PS3000A_CHANNEL_A = 0
    # enabled = 1
    # coupling type = PS3000A_DC = 1
    # range = PS3000A_2V = 7
    # analogue offset = 0 V
    channel_range = ps.PS3000A_RANGE['PS3000A_2V']
    status["setChA"] = ps.ps3000aSetChannel(chandle,
                                            ps.PS3000A_CHANNEL['PS3000A_CHANNEL_A'],
                                            enabled,
                                            ps.PS3000A_COUPLING['PS3000A_DC'],
                                            channel_range,
                                            analogue_offset)
    assert_pico_ok(status["setChA"])


    # Size of capture
    sizeOfOneBuffer = 5000
    numBuffersToCapture = 1

    totalSamples = sizeOfOneBuffer * numBuffersToCapture

    # Create buffers ready for assigning pointers for data collection
    bufferAMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
    
    # memory segment location to store sampled data 
    memory_segment = 0

    # Set data buffer location for data collection from channel A
    # handle = chandle
    # source = PS3000A_CHANNEL_A = 0
    # pointer to buffer max = ctypes.byref(bufferAMax)
    # pointer to buffer min = ctypes.byref(bufferAMin)
    # buffer length = maxSamples
    # segment index = 0
    # ratio mode = PS3000A_RATIO_MODE_NONE = 0
    status["setDataBuffersA"] = ps.ps3000aSetDataBuffers(chandle,
                                                         ps.PS3000A_CHANNEL['PS3000A_CHANNEL_A'],
                                                         bufferAMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                         None,
                                                         sizeOfOneBuffer,
                                                         memory_segment,
                                                         ps.PS3000A_RATIO_MODE['PS3000A_RATIO_MODE_NONE'])
    assert_pico_ok(status["setDataBuffersA"])

   
    # Begin streaming mode:
    sampleInterval = ctypes.c_int32(250)
    sampleUnits = ps.PS3000A_TIME_UNITS['PS3000A_US']
    # We are not triggering:
    maxPreTriggerSamples = 0
    autoStopOn = 1
    # No downsampling:
    downsampleRatio = 1
    status["runStreaming"] = ps.ps3000aRunStreaming(chandle,
                                                    ctypes.byref(sampleInterval),
                                                    sampleUnits,
                                                    maxPreTriggerSamples,
                                                    totalSamples,
                                                    autoStopOn,
                                                    downsampleRatio,
                                                    ps.PS3000A_RATIO_MODE['PS3000A_RATIO_MODE_NONE'],
                                                    sizeOfOneBuffer)
    assert_pico_ok(status["runStreaming"])

    actualSampleInterval = sampleInterval.value
    actualSampleIntervalNs = actualSampleInterval * 1000

#     print("Capturing at sample interval %s ns" % actualSampleIntervalNs)

    # We need a big buffer, not registered with the driver, to keep our complete capture in.
    bufferCompleteA = np.zeros(shape=totalSamples, dtype=np.int16)
    
    nextSample = 0
    autoStopOuter = False
    wasCalledBack = False


    def streaming_callback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
        nonlocal nextSample, autoStopOuter, wasCalledBack
        
#         print(f"nextSample {nextSample}")
#         print(f"autoStopOuter {autoStopOuter}")
        
        wasCalledBack = True
        destEnd = nextSample + noOfSamples
        sourceEnd = startIndex + noOfSamples
        bufferCompleteA[nextSample:destEnd] = bufferAMax[startIndex:sourceEnd]

        nextSample += noOfSamples
        if autoStop:
            autoStopOuter = True


    # Convert the python function into a C function pointer.
    cFuncPtr = ps.StreamingReadyType(streaming_callback)

    # Fetch data from the driver in a loop, copying it out of the registered buffers and into our complete one.
    while nextSample < totalSamples and not autoStopOuter:
        wasCalledBack = False
        status["getStreamingLastestValues"] = ps.ps3000aGetStreamingLatestValues(chandle, cFuncPtr, None)
        if not wasCalledBack:
            # If we weren't called back by the driver, this means no data is ready. Sleep for a short while before trying
            # again.
            time_handle.sleep(0.01)

#     print(f"Capturing at sample interval {actualSampleIntervalNs} ns; Done grabbing values!")

    # Find maximum ADC count value
    # handle = chandle
    # pointer to value = ctypes.byref(maxADC)
    maxADC = ctypes.c_int16()
    status["maximumValue"] = ps.ps3000aMaximumValue(chandle, ctypes.byref(maxADC))
    assert_pico_ok(status["maximumValue"])

    # Convert ADC counts data to mV
    adc2mVChAMax = adc2mV(bufferCompleteA, channel_range, maxADC)

    # Create time data
    time_x = np.linspace(0, (totalSamples - 1) * actualSampleIntervalNs, totalSamples)


    # Plot data from channel A and B
    if plt_flag:
        os.makedirs('./results/',exist_ok=True)
        plt.plot(time_x, adc2mVChAMax[:])
        plt.xlabel('Time (ns)')
        plt.ylabel('Voltage (mV)')
        plt.savefig('./results/sampled_trace.png')

    # Stop the scope
    # handle = chandle
    status["stop"] = ps.ps3000aStop(chandle)
    assert_pico_ok(status["stop"])

    # Disconnect the scope
    # handle = chandle
    status["close"] = ps.ps3000aCloseUnit(chandle)
    assert_pico_ok(status["close"])

#     # Display status returns
#     print(status)
    
    #return sampled data
    return np.array(adc2mVChAMax)


if __name__ == '__main__':
    trace = data_collect(plt_flag=True)
    ## print information of smapled data
    print(f"shape of sampled data {trace.shape}")
    print(f"max {max(trace)}, min {min(trace)}")


