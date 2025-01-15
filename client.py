import socket
import struct
import threading
import time
import sys

# --------------------------
# Constants for Packet Formats
# --------------------------
MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE_REQUEST = 0x3
MESSAGE_TYPE_PAYLOAD = 0x4




# --------------------------
# Helper Functions
# --------------------------

def handle_tcp_transfer(server_ip: str, tcp_port: int, file_size: int, transfer_id: int):

    try:
        print(f"[TCP] Transfer #{transfer_id} started.")
        start_time = time.time()

        # Create and use a TCP connection
        tcp_socket = socket.create_connection((server_ip, tcp_port), timeout=10)
        try:
            size = b"f"* file_size + b"\n"
            tcp_socket.sendall(size.encode())
            received = 0
            while received < file_size:
                data = tcp_socket.recv(4096)
                if not data:
                    break
                received += len(data)
        finally:
            tcp_socket.close()  # Ensure the socket is closed even if there's an exception

        # Calculate duration and speed
        duration = time.time() - start_time
        speed = (file_size * 8) / duration  # bits per second
        print(
            f"[TCP] Transfer #{transfer_id} finished, total time: {duration:.2f}s, speed: {speed:.2f} bits/sec")
    except Exception as e:
        print(f"[TCP] Transfer #{transfer_id} error: {e}")


def handle_udp_transfer(server_ip, udp_port, file_size, transfer_id):

    udp_socket = None
    try:
        print(f"[UDP] Transfer #{transfer_id} started.")

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(1)

        request_packet = struct.pack("!IBQ", MAGIC_COOKIE, MESSAGE_TYPE_REQUEST, file_size)
        udp_socket.sendto(request_packet, (server_ip, udp_port))
        print(f"[UDP] Sent request to {server_ip}:{udp_port} for {file_size} bytes")

        received_segments = set()
        total_segments = (file_size + 1023) // 1024  # Ceiling division
        start_time = time.time()

        while True:
            try:
                data, _ = udp_socket.recvfrom(2048)
                print(f"[UDP] Received packet")

                # Validate packet size
                if len(data) < 21:
                    print(f"[UDP] Received invalid payload size")
                    continue

                header = struct.unpack("!IBQQ", data[:21])
                magic_cookie, message_type, total_segments_recv, segment_number = header

                if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_PAYLOAD:
                    received_segments.add(segment_number)
                    print(f"[UDP] Received segment {segment_number}/{total_segments_recv}")

            except socket.timeout:
                print(f"[UDP] UDP receive timed out")
                break

        # 6. Calculate performance metrics
        total_time = time.time() - start_time
        bytes_received = len(received_segments) * 1024
        speed = (bytes_received * 8) / total_time if total_time > 0 else 0  # bits per second
        loss = 100 - (len(received_segments) / total_segments * 100) if total_segments > 0 else 0

        # 7. Print final results
        print(
            f"[UDP] Transfer #{transfer_id} finished, "
            f"total time: {total_time:.2f}s, speed: {speed:.2f} bits/sec, "
            f"packet loss: {loss:.2f}%"
        )
    except Exception as e:
        print(f"[UDP] Transfer #{transfer_id} error: {e}")
    finally:
        if udp_socket:
            udp_socket.close()
def main():

    try:
        while True:
            try:
                file_size_input = input(
                    f"Enter file size in bytes (e.g., 1000000 for ~1MB): ")
                if not file_size_input.isdigit():
                    print(f"Invalid file size. Please enter a positive integer.")
                    continue
                file_size = int(file_size_input)

                num_tcp_input = input(f"Enter number of TCP connections: ")
                if not num_tcp_input.isdigit() or int(num_tcp_input) < 1:
                    print(
                        f"Invalid number of TCP connections. Please enter a positive integer.")
                    continue
                num_tcp = int(num_tcp_input)

                num_udp_input = input(f"Enter number of UDP connections: ")
                if not num_udp_input.isdigit() or int(num_udp_input) < 1:
                    print(
                        f"Invalid number of UDP connections. Please enter a positive integer.")
                    continue
                num_udp = int(num_udp_input)
            except Exception as e:
                print(f"[Client] Error reading input: {e}")
                continue

            server_ip = "127.0.0.1"
            udp_port_input = "61672"
            tcp_port_input = "57725"
            print("Client started, listening for offer requests...")

            if not udp_port_input.isdigit() or not tcp_port_input.isdigit():
                print(f"Invalid port numbers. Please enter valid integers.")
                continue
            udp_port = int(udp_port_input)
            tcp_port = int(tcp_port_input)

            print(
                f"Connecting to server at {server_ip} (UDP port {udp_port}, TCP port {tcp_port})")

            threads = []
            count = 1
            for i in range(1, num_tcp + 1):
                t = threading.Thread(target=handle_tcp_transfer, args=(server_ip, tcp_port, file_size, count),daemon=True)
                threads.append(t)
                count += 1
                t.start()

            for i in range(1, num_udp + 1):
                t = threading.Thread(target=handle_udp_transfer, args=(server_ip, udp_port, file_size, count),
                                     daemon=True)
                threads.append(t)
                count += 1
                t.start()

            for t in threads:
                t.join()

            print(f"All transfers complete, ready for new tests...\n")

    except KeyboardInterrupt:
        print(f"\nClient shutting down...")
    except Exception as e:
        print(f"[Client] Unexpected error: {e}")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
