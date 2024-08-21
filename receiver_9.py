#!/usr/bin/python
# -- coding: UTF-8 --

import sys
import sx126x
import threading
import time
import select
import termios
import tty
import json
from azure.iot.device import IoTHubDeviceClient, Message

# Replace with your Azure IoT Hub connection string
CONNECTION_STRING = "HostName=MyIOTLoraHat.azure-devices.net;DeviceId=MyIoTLora;SharedAccessKey=rny+HZs42PbM433fc5i2eCp3NfFBZOojHAIoTJSOsnE="

# Initialize the IoT Hub client
client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

# Save old terminal settings and set to cbreak mode
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Set up the LoRa node
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=868, addr=0, power=22, rssi=True, air_speed=2400, relay=False)

# Flag to control sending and receiving
running = True

def send_to_cloud(voltage, current, energy, power):
    """Send the collected data to Azure IoT Hub."""
    try:
        # Prepare the message payload
        message_payload = {
            "voltage": voltage,
            "current": current,
            "energy": energy,
            "power": power
        }
        message_json = json.dumps(message_payload)
        msg = Message(message_json)
        client.send_message(msg)
        print(f"Sent to Azure: {message_json}")

    except Exception as e:
        print(f"Error sending to Azure: {e}")

def receive_message():
    """Thread to receive messages from LoRa and process them."""
    global running
    while running:
        try:
            message = node.receive()
            if message:
                decoded_message = message.decode(errors='ignore')
                print(f"Received from LoRa: {decoded_message}")

                # Parse the message to extract values
                try:
                    # Expected message format: "Voltage:{voltage}V,Current:{current}A,Energy:{energy}Wh,Power:{power}W"
                    data = {}
                    # Split the message by commas to handle each key-value pair
                    for part in decoded_message.split(','):
                        if ':' in part:
                            key, value = part.split(':', 1)
                            data[key] = value

                    # Extract values, defaulting to 'N/A' if not found
                    voltage = data.get('Voltage', 'N/A').strip('V')
                    current = data.get('Current', 'N/A').strip('A')
                    energy = data.get('Energy', 'N/A').strip('Wh')
                    power = data.get('Power', 'N/A').strip('W')

                    # Send the extracted values to Azure IoT Hub
                    send_to_cloud(voltage, current, energy, power)

                except Exception as parse_error:
                    print(f"Error parsing message: {parse_error}")

            time.sleep(0.1)  # Polling delay

        except Exception as e:
            print(f"Error receiving message: {e}")
            time.sleep(1)  # Wait a bit before retrying on error

def main():
    global running

    print("Press 'q' to quit")

    # Start receiving in a separate thread
    receive_thread = threading.Thread(target=receive_message)
    receive_thread.start()

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)
            if c == 'q':
                running = False
                break

    # Wait for the receiving thread to finish
    receive_thread.join()

    # Restore terminal settings
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    print("Exiting...")

    # Shutdown the IoT Hub client
    client.shutdown()

if __name__ == "__main__":
    main()
