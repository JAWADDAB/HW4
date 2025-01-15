import socket
import struct
import threading
import time
import sys


MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE_REQUEST = 0x3
MESSAGE_TYPE_PAYLOAD = 0x4



def handle_tcp_transfer(server_ip: str, tcp_port: int, file_size: int, transfer_id: int):

    try:

        print(f"[TCP] Transfer #{transfer_id} started.")
        start_time = time.time()

        tcp_socket = None
        try:
            tcp_socket = socket.create_connection((server_ip, tcp_port), timeout=10)

            size_bytes = b"f" * file_size + b"\n"

            tcp_socket.sendall(size_bytes.decode("latin-1").encode())


            received = 0
            while received < file_size:
                data = tcp_socket.recv(4096)
                if not data:
                    break
                received += len(data)

        finally:

            if tcp_socket:
                tcp_socket.close()

        duration = time.time() - start_time
        speed = (file_size * 8) / duration  # bits per second
        print(
            f"[TCP] Transfer #{transfer_id} finished, total time: {duration:.2f}s, speed: {speed:.2f} bits/sec"
        )

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

        total_time = time.time() - start_time
        bytes_received = len(received_segments) * 1024
        speed = (bytes_received * 8) / total_time if total_time > 0 else 0  # bits per second
        loss = 100 - (len(received_segments) / total_segments * 100) if total_segments > 0 else 0

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


def main() :

    try:
        while True:

            file_size, num_tcp, num_udp = None, None, None
            try:
                # File Size
                file_size_input: str = input("Enter file size in bytes (e.g., 1000000 for ~1MB): ")
                if not file_size_input.isdigit():
                    print("Invalid file size. Please enter a positive integer.")
                else:
                    file_size = int(file_size_input)

                # Number of TCP Connections
                num_tcp_input: str = input("Enter number of TCP connections: ")
                if (num_tcp_input.isdigit() and int(num_tcp_input) >= 1):
                    num_tcp = int(num_tcp_input)
                else:
                    print("Invalid number of TCP connections. Please enter a positive integer.")
                    file_size = None

                # Number of UDP Connections
                num_udp_input: str = input("Enter number of UDP connections: ")
                if (num_udp_input.isdigit() and int(num_udp_input) >= 1):
                    num_udp = int(num_udp_input)
                else:
                    print("Invalid number of UDP connections. Please enter a positive integer.")
                    file_size = None

            except Exception as e:
                print(f"[Client] Error reading input: {e}")

            # If any input was invalid, loop around to ask again
            if file_size is None or num_tcp is None or num_udp is None:
                continue


            server_ip: str = "127.0.0.1"
            udp_port_input: str = "4444"
            tcp_port_input: str = "3333"
            print("Client started, listening for offer requests...")

            # Validate port inputs
            if not udp_port_input.isdigit() or not tcp_port_input.isdigit():
                print("Invalid port numbers. Please enter valid integers.")
                continue

            udp_port: int = int(udp_port_input)
            tcp_port: int = int(tcp_port_input)

            # Notify user about the target server/ports
            print(f"Connecting to server at {server_ip} (UDP port {udp_port}, TCP port {tcp_port})")


            import threading

            threads = []
            count: int = 1

            # Launch TCP threads
            for _ in range(num_tcp):
                t = threading.Thread(
                    target=handle_tcp_transfer,
                    args=(server_ip, tcp_port, file_size, count),
                    daemon=True
                )
                threads.append(t)
                t.start()
                count += 1

            for _ in range(num_udp):
                t = threading.Thread(
                    target=handle_udp_transfer,
                    args=(server_ip, udp_port, file_size, count),
                    daemon=True
                )
                threads.append(t)
                t.start()
                count += 1

            for t in threads:
                t.join()

            print("All transfers complete, ready for new tests...\n")

    except KeyboardInterrupt:
        print("\nClient shutting down...")
    except Exception as e:
        print(f"[Client] Unexpected error: {e}")
    finally:
        import sys
        sys.exit(0)

if __name__ == "__main__":
    main()
