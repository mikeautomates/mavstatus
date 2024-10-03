import socket
from pymavlink import mavutil
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from collections import defaultdict
import ttkbootstrap as ttkb  # This adds modern theming support

# Set up the UDP connection
udp_ip = "0.0.0.0"  # Listen on all interfaces
udp_port = 14550    # Port to listen on

# Create a MAVLink connection
mavlink_connection = mavutil.mavlink_connection(f'udp:{udp_ip}:{udp_port}', autoreconnect=True, dialect='ardupilotmega')

# Severity level mapping to color and description for STATUSTEXT
severity_levels = {
    0: ('EMERGENCY', 'red'),
    1: ('ALERT', 'orange red'),
    2: ('CRITICAL', 'dark orange'),
    3: ('ERROR', 'red'),
    4: ('WARNING', 'orange'),
    5: ('NOTICE', 'green'),
    6: ('INFO', 'blue'),
    7: ('DEBUG', 'gray')
}

# List to store all messages with a maximum limit to prevent performance slowdown
max_messages = 100
all_status_messages = []

# Function to handle STATUSTEXT messages and update the display incrementally
def handle_statustext(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    severity_description, color = severity_levels.get(msg.severity, ('UNKNOWN', 'black'))  # Get both description and color
    message_text = f"{msg.text}"
    severity_tag = f"severity_{msg.severity}"

    # Create the new message entry
    full_message = f"{timestamp:<20} [{severity_description:<12}] {message_text:<60}"

    # Insert only the new message at the top, instead of redrawing everything
    status_text_widget.insert('1.0', full_message + '\n')
    status_text_widget.tag_add(severity_tag, '1.0', '1.end')

    # Limit the number of messages to avoid performance issues
    all_status_messages.insert(0, full_message)
    if len(all_status_messages) > max_messages:
        all_status_messages.pop()
        # Remove the last line in the text widget
        status_text_widget.delete('end-2l', 'end-1l')

# Function to handle HEARTBEAT and SYS_STATUS messages and update the display
def handle_system_status(msg):
    if msg.get_type() == 'HEARTBEAT':
        armed_status = 'ARMED' if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED else 'DISARMED'
        custom_mode = msg.custom_mode
        mode_description = mavutil.mode_string_v10(msg)  # Get mode description based on custom mode

        # Display armed status and flight mode from HEARTBEAT message
        system_info_text_widget.delete('1.0', tk.END)
        system_info_text_widget.insert(tk.END, f"Armed Status: {armed_status}\n")
        system_info_text_widget.insert(tk.END, f"Flight Mode: {mode_description} (Custom Mode: {custom_mode})\n")

    elif msg.get_type() == 'SYS_STATUS':
        battery_voltage = msg.voltage_battery / 1000.0 if msg.voltage_battery != -1 else 'N/A'  # Convert to volts
        load = msg.load / 10.0  # System load in percentage
        cpu_usage = msg.load / 10.0 if msg.load != -1 else 'N/A'

        # Append battery voltage, system load, and CPU usage information in the system info widget
        system_info_text_widget.insert(tk.END, f"Battery Voltage: {battery_voltage:.2f}V\n")
        system_info_text_widget.insert(tk.END, f"System Load: {load:.1f}%\n")
        system_info_text_widget.insert(tk.END, f"CPU Usage: {cpu_usage:.1f}%\n")

# Function to log unknown message types
def log_unknown_message(msg):
    msg_id = msg.get_msgId()
    print(f"Unknown message type received: ID {msg_id}")

# Function to detect incoming messages and handle priority ones
def detect_incoming_messages():
    msg = mavlink_connection.recv_match(blocking=False)
    if msg:
        msg_type = msg.get_type()

        if msg_type == 'STATUSTEXT':  # Handle STATUSTEXT messages immediately
            handle_statustext(msg)
        elif msg_type == 'HEARTBEAT' or msg_type == 'SYS_STATUS':  # Handle HEARTBEAT and SYS_STATUS messages immediately
            handle_system_status(msg)
        else:
            log_unknown_message(msg)

    # Call the function again after 50ms (adjust the interval as needed)
    root.after(50, detect_incoming_messages)

# Function to clear all the current data from the displays and reset the list
def clear_all_data():
    status_text_widget.delete('1.0', tk.END)
    system_info_text_widget.delete('1.0', tk.END)
    all_status_messages.clear()

# Set up the themed Tkinter GUI with ttkbootstrap theme
root = ttkb.Window(themename="cosmo")  # Choose a modern Bootstrap theme

# Create a frame to hold both the STATUSTEXT and SYSTEM INFO windows in one row
top_frame = ttk.Frame(root)
top_frame.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

# Configure a large text display for STATUSTEXT with a scrollbar (left side)
status_text_label = ttk.Label(top_frame, text="STATUSTEXT MESSAGES", font=("Helvetica", 14, "bold"))
status_text_label.grid(row=0, column=0, padx=5, pady=5)
status_text_widget = tk.Text(top_frame, font=("Helvetica", 16), height=20, width=80)
status_scrollbar = ttk.Scrollbar(top_frame, command=status_text_widget.yview)
status_text_widget.configure(yscrollcommand=status_scrollbar.set)
status_text_widget.grid(row=1, column=0, sticky="nsew")
status_scrollbar.grid(row=1, column=1, sticky="ns")

# Configure a large text display for system status (HEARTBEAT and SYS_STATUS) (right side)
system_info_label = ttk.Label(top_frame, text="SYSTEM STATUS", font=("Helvetica", 14, "bold"))
system_info_label.grid(row=0, column=2, padx=5, pady=5)
system_info_text_widget = tk.Text(top_frame, font=("Helvetica", 16), height=20, width=40)
system_info_text_widget.grid(row=1, column=2, sticky="nsew")

# Add a button to clear all data with modern ttkbootstrap styling
clear_button = ttkb.Button(root, text="Clear Data", command=clear_all_data, bootstyle="danger")
clear_button.grid(row=3, column=0, columnspan=3, pady=10)

# Add color tags for severity levels
for severity, (description, color) in severity_levels.items():
    severity_tag = f"severity_{severity}"
    status_text_widget.tag_configure(severity_tag, foreground=color, font=("Helvetica", 16, "bold"))

# Wait for heartbeat and start receiving messages
def wait_for_heartbeat():
    print("Waiting for HEARTBEAT...")
    while True:
        msg = mavlink_connection.recv_match(type='HEARTBEAT', blocking=True)
        if msg:
            print("HEARTBEAT received!")
            # Start detecting messages after receiving heartbeat
            root.after(50, detect_incoming_messages)
            break

# Start the GUI and message detection
wait_for_heartbeat()

# Run the Tkinter main loop
root.mainloop()
