import socket
import base64
import time
import getpass
from datetime import datetime
from pyrtcm import RTCMReader, RTCMMessageError, RTCMParseError

# ==========================================
# CONFIGURACIÓN GENERAL DEL MONITOREO
# ==========================================
DEFAULT_HOST = "sbc.igac.gov.co"
DEFAULT_PORT = 2102  # 2101 cluster virtual 
DEFAULT_MOUNTPOINT = "CALI_RTCM3"

MAX_LATENCY_SEC = 3.0

class NTRIPCheckerAlertSystem:
    def __init__(self, host, port, mountpoint, user, password):
        self.host = host
        self.port = port
        self.mountpoint = mountpoint
        self.user = user
        self.password = password
        self.socket = None
        self.last_packet_time = time.time()

    def connect(self):
        """Realiza el handshake NTRIP."""
        print(f"\n[{datetime.now()}] Conectando a {self.host}:{self.port}/{self.mountpoint}...")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(10)

        try:
            self.socket.connect((self.host, self.port))
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Error al conectar: {e}")
            return False

        auth = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        req = (
            f"GET /{self.mountpoint} HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            f"User-Agent: PythonNTRIPChecker/1.0\r\n"
            f"Authorization: Basic {auth}\r\n"
            f"Accept: */*\r\n\r\n"
        )
        self.socket.sendall(req.encode())

        response = self.socket.recv(1024).decode(errors='ignore')
        if "200 OK" in response or "ICY 200 OK" in response:
            print(f"[{datetime.now()}] ¡Conexión NTRIP Exitosa!")
            return True
        else:
            print(f"[{datetime.now()}] Error en respuesta NTRIP: {response.splitlines()[0] if response else 'Sin respuesta'}")
            return False

    def start_monitoring(self):
        if not self.connect():
            return

        rtr = RTCMReader(self.socket)
        self.last_packet_time = time.time()

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_binary_file = f"rtcm_stream_{self.mountpoint}_{timestamp_str}.rtcm3"
        decoded_log_file = f"rtcm_decoded_{self.mountpoint}_{timestamp_str}.txt"

        print(f"[{datetime.now()}] Monitoreando y guardando flujo RTCM3...")
        print(f"📁 Guardando archivo binario en: {raw_binary_file}")
        print(f"📄 Guardando datos decodificados en: {decoded_log_file}\n")

        with open(raw_binary_file, "wb") as bin_file, open(decoded_log_file, "w", encoding="utf-8") as text_file:
            try:
                while True:
                    try:
                        raw_data, parsed_data = rtr.read()

                        if raw_data:
                            bin_file.write(raw_data)
                            bin_file.flush()

                        if parsed_data:
                            current_time = time.time()
                            latency = current_time - self.last_packet_time
                            self.last_packet_time = current_time

                            msg_id = parsed_data.identity
                            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

                            log_entry = f"[{now_str}] Mensaje RTCM {msg_id} ({len(raw_data)} bytes, Latencia: {latency:.3f}s):\n"
                            log_entry += f"{parsed_data}\n" + "-"*80 + "\n"

                            text_file.write(log_entry)
                            text_file.flush()

                            print(f"[{now_str[:8]}] Guardado Msg RTCM: {msg_id} | {len(raw_data)} bytes | Latencia: {latency:.3f}s")

                    except (RTCMMessageError, RTCMParseError) as e:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error de trama / CRC: {e}")

            except KeyboardInterrupt:
                print("\nCaptura y monitoreo detenido por el usuario.")
            finally:
                self.socket.close()
                print("Archivos guardados correctamente en el directorio actual.")

if __name__ == "__main__":
    print("==========================================")
    print("      NTRIP CHECKER & GNSS MONITOR        ")
    print("==========================================")

    # Solicitar únicamente las credenciales al usuario
    user_input = input("Usuario NTRIP: ").strip()
    password_input = getpass.getpass("Contraseña NTRIP (oculta): ").strip()

    # Se utilizan directamente las constantes globales por defecto
    monitor = NTRIPCheckerAlertSystem(
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        mountpoint=DEFAULT_MOUNTPOINT,
        user=user_input,
        password=password_input
    )
    monitor.start_monitoring()