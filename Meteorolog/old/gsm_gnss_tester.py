import serial
import time
import sys

# --- Configuration ---
# The default serial port for Raspberry Pi's GPIO header is /dev/serial0
# If you use a USB-to-Serial adapter, it might be /dev/ttyUSB0
SERIAL_PORT = "/dev/serial0"
# MC60 module typically uses a baud rate of 115200
BAUD_RATE = 115200

# --- Helper Function ---
def send_at_command(ser, command, expected_response="OK", timeout=1):
    """
    Sends an AT command to the modem and prints the response.
    Returns True if the expected response is received, False otherwise.
    """
    # Clean any previous data in the buffer
    ser.reset_input_buffer()
    
    # Construct the full command with carriage return and newline
    full_command = command + '\r\n'
    
    print(f"[-->] Sending: {command}")
    ser.write(full_command.encode('ascii'))
    
    # Wait for the modem to process the command
    time.sleep(timeout)
    
    # Read all available data from the serial port
    response = ser.read_all().decode('ascii', errors='ignore')
    
    print(f"[<--] Received:\n---\n{response.strip()}\n---")
    
    if expected_response in response:
        print(f"[INFO] Command successful (found '{expected_response}').\n")
        return True
    else:
        print(f"[WARN] Command failed or did not return the expected response ('{expected_response}').\n")
        return False

# --- Main Script ---
def main():
    print("--- D-IoT MC60 GSM/GNSS Module Test ---")
    print(f"Attempting to open serial port {SERIAL_PORT} at {BAUD_RATE} bps...")

    ser = None  # Initialize ser to None
    try:
        # Initialize the serial connection
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print("[OK] Serial port opened successfully.\n")

        # --- TEST 1: Basic Communication ---
        print("--- Test 1: Basic Communication ---")
        if not send_at_command(ser, "AT"):
            print("[FAIL] Module is not responding. Check power, physical connections, and raspi-config settings.")
            sys.exit(1) # Exit the script if the module doesn't respond

        # --- TEST 2: SIM Card Status ---
        print("--- Test 2: SIM Card Status ---")
        # The expected response for a ready SIM is "+CPIN: READY"
        if not send_at_command(ser, "AT+CPIN?", "READY"):
            print("[FAIL] SIM card not ready. Check if it's inserted correctly, active, and has PIN lock disabled.")
            sys.exit(1)

        # --- TEST 3: Network Registration ---
        print("--- Test 3: Network Registration ---")
        # We wait up to 30 seconds for network registration
        for i in range(30):
            print(f"Checking network registration (attempt {i+1}/30)...")
            # +CREG: 0,1 means registered on home network
            # +CREG: 0,5 means registered on roaming
            if send_at_command(ser, "AT+CREG?", "+CREG: 0,1", timeout=1) or \
               send_at_command(ser, "AT+CREG?", "+CREG: 0,5", timeout=1):
                print("[OK] Module successfully registered to the network.")
                break
            if i == 29:
                print("[FAIL] Could not register to the network. Check antenna and signal coverage.")
                sys.exit(1)

        # --- TEST 4: Signal Quality ---
        print("--- Test 4: Signal Quality ---")
        send_at_command(ser, "AT+CSQ")

        # --- TEST 5: GNSS (GPS) Power and Data ---
        print("--- Test 5: GNSS (GPS) Functionality ---")
        if send_at_command(ser, "AT+CGNSPWR=1"):
            print("[INFO] GNSS power is ON. Waiting for a satellite fix...")
            print("[INFO] This can take several minutes and requires a clear view of the sky.")
            # Wait a bit for the fix
            time.sleep(20)
            send_at_command(ser, "AT+CGNSINF", "CGNSINF:")
        else:
            print("[WARN] Failed to turn on GNSS power.")

    except serial.SerialException as e:
        print(f"\n[ERROR] Serial Port Error: {e}")
        print("Please ensure that:")
        print("1. The D-IoT module is correctly seated on the Raspberry Pi.")
        print("2. The serial port is enabled via 'sudo raspi-config' (and serial console is disabled).")
        print("3. The user has permission to access the serial port (try running with 'sudo').")
        
    except KeyboardInterrupt:
        print("\n[INFO] Program interrupted by user.")

    finally:
        if ser and ser.is_open:
            # Turn off GNSS to save power before closing
            print("\n--- Cleaning up ---")
            send_at_command(ser, "AT+CGNSPWR=0")
            ser.close()
            print("[OK] Serial port closed.")
        print("--- Test finished ---")


if __name__ == "__main__":
    main()