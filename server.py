import socket
import struct
import threading
import time
import sys


MAGIC_COOKIE = 0xABCDDCBA
MESSAGE_TYPE_OFFER = 0x02
MESSAGE_TYPE_REQUEST = 0x03
MESSAGE_TYPE_PAYLOAD = 0x04


def build_payload_packet(total_segments, current_segment, payload_size = 1024) -> bytes:

    header = struct.pack("!IbQQ", MAGIC_COOKIE, MESSAGE_TYPE_PAYLOAD, total_segments, current_segment)
    payload_data = b"x" * payload_size
    return header + payload_data




def handle_tcp_client(client_socket: socket.socket, client_address: tuple):

    try:
        print(f"[TCP] Connected to {client_address}")
        data = b""
        while True:
            chunk = client_socket.recv(1024)
            if not chunk:
                break
            data += chunk
            if b"\n" in chunk:
                break
        file_size_str = data.strip().decode()
        file_size = int(file_size_str)
        print(f"[TCP] Client {client_address} requested {file_size} bytes")

        bytes_sent = 0
        buffer_size = 4096
        chunk_data = b"x" * buffer_size  # Dummy data

        start_time = time.time()

        while bytes_sent < file_size:
            send_size = min(buffer_size, file_size - bytes_sent)
            client_socket.sendall(chunk_data[:send_size])
            bytes_sent += send_size

        duration = time.time() - start_time
        speed = (bytes_sent * 8) / duration  # bits per second
        print(f"[TCP] Sent {bytes_sent} bytes to {client_address} in {duration:.2f}s at {speed:.2f} bits/sec")
    except Exception as e:
        print(f"[TCP] Error with client {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"[TCP] Connection to {client_address} closed")







def handle_udp_client(udp_socket: socket.socket, client_address: tuple, file_size: int):
    try:

        print(f"[UDP] Handling request from {client_address} for {file_size} bytes")

        total_segments = (file_size + 1023) // 1024
        start_time = time.time()

        segment_number = 1
        while segment_number <= total_segments:
            payload_packet = build_payload_packet(total_segments, segment_number)
            udp_socket.sendto(payload_packet, client_address)
            segment_number += 1

        duration = time.time() - start_time
        speed_bps = (file_size * 8) / duration if duration > 0 else 0
        print(
            f"[UDP] Sent {total_segments} segments to {client_address} "
            f"in {duration:.2f}s at {speed_bps:.2f} bits/sec"
        )

    except Exception as e:
        print(f"[UDP] Error with client {client_address}: {e}")








def handle_udp_requests(udp_socket: socket.socket) -> None:

    while True:
        try:

            data, client_address = udp_socket.recvfrom(1024)
            print(f"[UDP] Received data from {client_address}")

            if len(data) < 13:
                print(f"[UDP] Invalid packet size from {client_address}")
                continue

            magic_cookie, message_type, file_size = struct.unpack("!IBQ", data[:13])

            if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_REQUEST:
                print(f"[UDP] Valid request from {client_address} for {file_size} bytes")
                threading.Thread(
                    target=handle_udp_client,
                    args=(udp_socket, client_address, file_size),
                    daemon=True
                ).start()
            else:
                print(f"[UDP] Invalid request format from {client_address}")

        except Exception as e:
            print(f"[UDP] Error receiving data: {e}")








def main():

    try:

        TCP_PORT: int = 3333
        UDP_PORT: int = 4444


        hostname: str = socket.gethostname()
        server_ip: str = socket.gethostbyname(hostname)
        print(f"Server started, listening on IP address {server_ip}")
        print(f"UDP Port: {UDP_PORT}, TCP Port: {TCP_PORT}")


        udp_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('', UDP_PORT))

        threading.Thread(
            target=handle_udp_requests,
            args=(udp_socket,),
            daemon=True
        ).start()


        tcp_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_socket.bind(('', TCP_PORT))
        tcp_socket.listen(5)
        print(f"TCP server listening on port {TCP_PORT}")


        while True:
            client_socket, client_address = tcp_socket.accept()
            threading.Thread(
                target=handle_tcp_client,
                args=(client_socket, client_address),
                daemon=True
            ).start()

    except KeyboardInterrupt:
        print(f"\nServer shutting down...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        sys.exit(0)

if __name__ == "__main__":
    main()
