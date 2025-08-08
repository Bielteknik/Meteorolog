import serial
import time

def get_distance():
    try:
        with serial.Serial('COM4', 9600, timeout=1) as ser:
            ser.reset_input_buffer()
            start_time = time.time()
            while ser.in_waiting < 4:
                if time.time() - start_time > 2:
                    print("Timeout: Veri alınamadı.")
                    return None

            data = ser.read(4)

            if len(data) != 4:
                print("Hatalı veri uzunluğu:", len(data))
                return None

            if data[0] != 0xFF:
                print("Başlık baytı geçersiz:", data[0])
                return None

            checksum = (data[0] + data[1] + data[2]) & 0xFF
            if checksum != data[3]:
                print("Checksum hatası")
                return None

            distance_mm = (data[1] << 8) + data[2]
            distance_cm = distance_mm / 10.0

            return distance_cm

    except serial.SerialException as e:
        print("Seri port hatası:", e)
        return None

# Test
while True:
    distance = get_distance()
    if distance is not None:
        print(f"Mesafe: {distance:.1f} cm")
    else:
        print("Mesafe okunamadı.")
    time.sleep(1)
