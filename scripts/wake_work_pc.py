import socket
import struct

def send_magic_packet(mac_address):
    # Remove separators and convert to bytes
    mac_address = mac_address.replace(':', '').replace('-', '')
    data = bytes.fromhex('FF' * 6 + mac_address * 16)
    
    # Send packet to broadcast address
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(data, ('192.168.0.255', 9))
    print(f"Magic packet sent to {mac_address}")

if __name__ == "__main__":
    send_magic_packet("f0:2f:74:ac:e3:1d")
