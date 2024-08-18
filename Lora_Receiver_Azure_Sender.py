#!/usr/bin/python
# -- coding: UTF-8 --

import sys
import sx126x
import threading
import time
import random
import select
import termios
import tty
from azure.iot.device import IoTHubDeviceClient, Message

# Replace with your connection string
CONNECTION_STRING = "HostName=MyIOTLoraHat.azure-devices.net;DeviceId=MyIoTLora;SharedAccessKey=rny+HZs42PbM433fc5i2eCp3NfFBZOojHAIoTJSOsnE="

# Initialize the IoT Hub client
client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

# Save old terminal settings and set to cbreak mode
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Set up the LoRa node
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=868, addr=0, power=22, rssi=True, air_speed=2400, relay=False)

# Flags to control the tasks
running = True

def send_to_cloud():
    """Thread to send random voltage, current, power, and energy data to Azure IoT Hub."""
    while running:
        try:
            # Generate random values for voltage, current, energy, and power
            voltage = round(random.uniform(3.0, 5.0), 2)  # Example range 3.0 to 5.0 volts
            current = round(random.uniform(0.1, 2.0), 2)  # Example range 0.1 to 2.0 amps
            energy = round(random.uniform(0.1, 10.0), 2)  # Example range 0.1 to 10.0 watt-hours
            power = round(voltage * current, 2)           # Power = Voltage * Current

            # Prepare the message
            message = {
                "voltage": voltage,
                "current": current,
                "energy": energy,
                "power": power
            }
            message_payload = str(message)

            # Create and send the message
            msg = Message(message_payload)
            client.send_message(msg)
            print(f"Sent to Azure: {message_payload}")

        except Exception as e:
            print(f"Error sending to Azure: {e}")

        time.sleep(10)  # Wait before sending the next message

def receive_from_lora():
    """Thread to receive data from LoRa and print it."""
    while running:
        try:
            message = node.receive()
            if message:
                # Decode and print the received message
                decoded_message = message.decode(errors='ignore')
                print(f"Received from LoRa: {decoded_message}")

                # Parse the message
                try:
                    # Expected message format: "Voltage:{voltage}V,Current:{current}A,Energy:{energy}Wh,Power:{power}W"
                    parts = decoded_message.split(',')
                    data = {}
                    for part in parts:
                        key, value = part.split(':')
                        data[key] = value

                    # Extract and print each parameter
                    voltage = data.get('Voltage', 'N/A')
                    current = data.get('Current', 'N/A')
                    energy = data.get('Energy', 'N/A')
                    power = data.get('Power', 'N/A')

                    print(f"Voltage: {voltage}V")
                    print(f"Current: {current}A")
                    print(f"Energy: {energy}Wh")
                    print(f"Power: {power}W")

                except Exception as parse_error:
                    print(f"Error parsing message: {parse_error}")

            else:
                print("No message received from LoRa")

            time.sleep(0.1)  # Polling delay

        except Exception as e:
            print(f"Error receiving from LoRa: {e}")

def main():
    global running

    print("Press 'q' to quit")

    # Start the sending and receiving threads
    send_thread = threading.Thread(target=send_to_cloud)
    receive_thread = threading.Thread(target=receive_from_lora)

    send_thread.start()
    receive_thread.start()

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)
            if c == 'q':
                running = False
                break

    # Wait for both threads to finish
    send_thread.join()
    receive_thread.join()

    # Restore terminal settings
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    print("Exiting...")

    # Shutdown the IoT Hub client
    client.shutdown()

if __name__ == "__main__":
    main()


