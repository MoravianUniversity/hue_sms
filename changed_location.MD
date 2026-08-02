# Information for Users 

## Use

This file contains the instructions on how to set up the program to work, when the location of the Hue bridge and/or the
computer running the file has been changed. The following steps are created under the assumption that the steps laid out
in the `developers.MD` file have been followed. 


## Setup Process

These steps must be followed both after the Hue bridge has been plugged in, and before the program has been run.  If you
 know for certain what IP is assigned to the Hue Bridge, then you may skip directly to Step 3.

1. **If you do not currently have the Philips HUE app installed on a device, do so now.**
2. **Use the app to search for the bridge's IP address (Note that both the device and bridge must be on the same network).**
3. **Once the IP address is determined, add it to `settings.toml` in the project root as `light_ip`.**
4. **Run the SMS server (`python -m hue_sms.web.hue_flask`), while pressing and releasing the sync button on the Hue Bridge.**

Following Step 4, your device should be able to run the program.  If it does not initially work, repeat Step 4 before 
attempting an alternate solution.

