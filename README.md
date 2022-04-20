# EM Trace Collection

This repos include instruction and sripts for collecting EM trace with different devices. such as wtih device CW505 H-Field probe, and wtih device osilloscope ps3206D to collect EM trace.


How to collect EM trace, please see the details in the corresponding sub-folder.


# Instruction for collecting EM trace with CW505 H-Field planar probe

```probe_position_exploration_em_trace.ipynb``` is to decide the best postion for probe placed with the real-time visualization of EM trace.

### AES Encryption Pattern
The following figure is the AES encryption pattern, when you see a pattern looks like the pattern in the figure, you should fixed the position of probe. You can start collecting your EM trace of AES encryption.

```em_trace_autoCapture.ipynb``` once the best postion is found, we can automatically collect em trace and save it to npz file



