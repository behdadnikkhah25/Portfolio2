import time
from struct import *
from socket import *
import sys

# Header format
header_format = "!IIHH"

handshake_complete = False


def create_packet(seq_num, ack_num, flags, window_size, data):
    """
    Creates a packet from the given parameters

    Args:
        seq_num (int): The sequence number of the packet
        ack_num (int): The acknowledgement number of the packet
        flags (int): An integer representing the packet's flags
        window_size (int): The window size of the packet
        data (bytes): The data to be included in the packet

    Returns:
        bytes: The packet created from the given parameters
    """
    header = pack(header_format, seq_num, ack_num, flags, window_size)
    packet = header + data
    return packet


def parse_header(header):
    """
    Parses the given header bytes and returns the values as a tuple

    Args:
        header (bytes): The header bytes to be parsed

    Returns:
        tuple[int, int, int, int]: A tuple containing the sequence number, acknowledgement number, flags,
        and window size parsed from the header bytes
    """
    header_from_msg = unpack(header_format, header)
    return header_from_msg


def parse_flags(flags):
    """
    Parses the given flags integer and returns a tuple containing the SYN, ACK, and FIN flags

    Args:
        flags (int): An integer representing the flags of the packet

    Returns:
        tuple: A tuple containing the SYN, ACK, and FIN flags
    """
    syn = (flags >> 3) & 1
    ack = (flags >> 2) & 1
    fin = (flags >> 1) & 1

    return syn, ack, fin


def send(sock, data, seq_num, addr):
    """
    Sends a packet with the given data, sequence number, and address using the provided socket

    Args:
        sock (socket): The socket to use for sending the packet
        data (bytes): The data to include as payload in the packet
        seq_num (int): The sequence number of the packet
        addr (tuple): A tuple representing the address to send the packet to

    Returns:
        None
    """
    packet = create_packet(seq_num, 0, 0, 0, data)
    sock.sendto(packet, addr)


def send_ack(sock, ack_num, addr):
    """
    Sends an acknowledgement packet with the given acknowledgement number and address using the provided socket

    Args:
        sock (socket): The socket to use for sending the acknowledgement packet
        ack_num (int): The acknowledgement number to include in the packet
        addr (tuple): A tuple representing the address to send the acknowledgement packet to

    Returns:
        None
    """
    ack_msg = create_packet(0, ack_num, 4, 64, b"")  # flags = 0 1 0 0 = 4 --> ACK flag value
    sock.sendto(ack_msg, addr)


def initiate_handshake(sock, addr):
    """
    Initiate the three-way handshake to establish connection with server/receiver host

    Arguments:
        sock (socket): Client/sender socket to be used for communication with the server/receiver host
        addr (tuple): IP address and port number of the server

    Returns:
        None
    """
    global handshake_complete

    # If handshake has not yet been completed, establish connection
    if not handshake_complete:
        flags = 8  # 1 0 0 0 = SYN flag value
        syn_packet = create_packet(0, 0, flags, 0, b"")  # Create SYN packet
        sock.sendto(syn_packet, addr)  # Send SYN packet to destination address
        print("Sent SYN packet with seq_num", 0)

        while True:
            # Set a timeout of 0.5 seconds for the socket for receiving SYN-ACK message
            sock.settimeout(0.5)
            try:
                synack_msg, addr = sock.recvfrom(1472)  # Receive message from the destination address
                header_from_msg = synack_msg[:12]  # Extract the header from the received message
                seq_num, ack_num, flags, win = parse_header(header_from_msg)  # Parse the header fields
                syn, ack, fin = parse_flags(flags)  # Parse the flags

                # If received SYN-ACK message is valid, send final ACK packet and complete handshake
                if syn and ack and not fin:
                    print("Received SYN-ACK msg with ak_num", ack_num)
                    flags = 4  # 0 1 0 0 = ACK flag value
                    ack_packet = create_packet(0, 0, flags, 0, b'')  # Create final ACK packet
                    sock.sendto(ack_packet, addr)  # Send ACK to destination address
                    print("Sent final ACK packet with ack_num", 0)
                    handshake_complete = True  # Set handshake_complete  to True
                    break

            # If timeout occurs, resend SYN packet
            except timeout:
                print(f"Timeout occurred. Resending SYN packet with seq_num 0")
                flags = 8  # 1 0 0 0 = SYN flag value
                syn_packet = create_packet(0, 0, flags, 0, b"")  # Create new SYN packet
                sock.sendto(syn_packet, addr)  # Send new SYN packet to destination address


def handle_handshake(sock):
    """
    Perform the three-way handshake to establish connection with the sender

    Arguments:
        sock (socket): The receivers socket for communication with the sender

    Returns:
        None
    """
    # Import global variable
    global handshake_complete

    # If the handshake is not completed yet
    if not handshake_complete:
        # Keep looping until the handshake is complete
        while True:
            try:
                # Receive SYN packet from sender
                syn_packet, addr = sock.recvfrom(1472)
                header = syn_packet[:12]        # Extract the header from the packet
                syn, ack, fin = parse_flags(parse_header(header)[2])    # Parse the flags from the header

                # If SYN flag is set and no other flags are set
                if syn and not ack and not fin:
                    print("Received SYN msg")
                    # Create a SYN-ACK packet and send back to sender
                    syn_ack_msg = create_packet(0, 0, 12, 64, b"")
                    sock.sendto(syn_ack_msg, addr)

                # If ACK flag is set and no other flags are set
                elif not syn and ack and not fin:
                    print("Received final ACK msg")
                    # Set handshake to True and exit loop
                    handshake_complete = True
                    break

            # If any error occurs, print the error and exit the program
            except Exception as e:
                print("Error:", e)
                sys.exit()


def close_conn(sock, addr, next_seq_num):
    """
    Closes the connection between the client and server

    Arguments:
        sock (socket): Client/sender socket to close the connection
        addr (tuple): IP address and port number of the server
        next_seq_num (int): Current sequence number to continue from

    Returns:
        None
    """
    flags = 2  # 0 0 1 0 = FIN flag value
    # Create packet with current sequence number and to destination address
    fin_msg = create_packet(next_seq_num, 0, flags, 0, b"")
    sock.sendto(fin_msg, addr)

    fin_ack_received = False

    while not fin_ack_received:
        # Set timeout of 0.5 seconds for the socket
        sock.settimeout(0.5)

        try:
            # Receive message from the destination address
            fin_ack_msg, addr = sock.recvfrom(1472)
            header_from_msg = fin_ack_msg[:12]      # Extract the header from the message
            seq_num, ack_num, flags, win = parse_header(header_from_msg)    # Parse the header
            syn, ack, fin = parse_flags(flags)      # Parse the flags

            # If only ACK flag is set with the correct ack_num
            if ack and not syn and not fin and ack_num == next_seq_num:
                print("Received ACK msg for FIN msg with ack_num", ack_num)
                # Increment sequence number, close the socket and exit loop
                next_seq_num += 1
                sock.close()
                fin_ack_received = True
                return

            # If ACK flag is not set and with lower ack_num
            elif not ack and ack_num < next_seq_num:
                print("Received duplicate ACK msg with ack_num", ack_num)
                flags = 2  # Set the flag value to FIN
                # Create a new packet and resend to the destination address
                fin_msg = create_packet(next_seq_num, 0, flags, 0, b"")
                sock.sendto(fin_msg, addr)

        # If a timeout occurs, resend the FIN packet
        except timeout:
            print(f"Timeout occurred. Resending FIN msg")
            sock.sendto(fin_msg, addr)


def RECV_SAW(sock, skip_ack):
    """
    Receives data packets sent by the sender and sends ACK packets to confirm receipt of each packet

    Arguments:
        sock (socket): Receiver socket for receiving packets from server
        skip_ack (bool): Whether to skip the first ACK message (for test case)

    Returns:
        bytes: Concatenated data from the received packets
    """
    # Perform handshake with sender
    handle_handshake(sock)

    # Initialize variables
    expected_seq_num = 1
    received_data = b""     # Concatenated data of all received packets

    while True:
        # Receive packet from sender
        msg, addr = sock.recvfrom(1472)
        header_from_msg = msg[:12]              # Extract the header from the received message 
        seq_num, ack_num, flags, win = parse_header(header_from_msg)    # Parse the header fields
        syn, ack, fin = parse_flags(flags)      # Parse the flags

        # If flag is True, skip the first ACK message
        if skip_ack:
            print("Skipping first ACK msg")
            skip_ack = False
            continue

        # If received packet has correct sequence number
        if not fin and not syn and not ack and seq_num == expected_seq_num:
            print("Received in-order with seq_num =", seq_num)
            # Extract payload from the packet
            app_data = msg[12:]
            # Send an ACK message with received seq_num
            send_ack(sock, expected_seq_num, addr)
            # Increment the expected sequence number
            expected_seq_num += 1
            received_data += app_data

        # If received packet does not have correct sequence number
        elif not fin and not syn and not ack and seq_num != expected_seq_num:
            # Send a duplicate ACK message to the sender, if received a duplicate packet
            if seq_num == expected_seq_num - 1:
                print("Received duplicate packet with seq_num =", seq_num)
                send_ack(sock, expected_seq_num - 1, addr)

            # Else ignore received packet
            else:
                print("Received out-of-order packet. Ignoring")

        # If FIN flag is set, send back an ACK message, close the socket, and return received data
        elif fin and not ack and not syn and seq_num == expected_seq_num:
            print("Received FIN msg with seq_num", seq_num)
            send_ack(sock, expected_seq_num, addr)
            sock.close()
            return received_data


def SEND_SAW(sock, addr, data):
    """
    Sends data using the Selective Acknowledgment Protocol

    Arguments:
        sock (socket): Socket object to use for sending and receiving data
        addr (tuple): IP address and port number of the server/receiver
        data (bytes): File data to be sent in bytes

    Returns:
        Void
    """
    # Initiate three-way handshake with the receiver
    initiate_handshake(sock, addr)

    # Initialize variables
    sequence_num = 1
    last_sent_packet = {}

    # Loop until there is no data to send
    while True:
        # Initialize the estimated RTT 
        est_rtt = 0.5

        # If no more data, close the connection and exit loop
        if not data:
            close_conn(sock, addr, sequence_num)
            break

        # Send the next packet of data (upt to 1460bytes) with the current sequence number
        send(sock, data[:1460], sequence_num, addr)
        last_sent_packet[sequence_num] = data[:1460]
        # Remove the sent data from the buffer
        data = data[1460:]

        # Record the time the packet was sent
        send_time = time.monotonic()

        # Wait for ACK message from the receiver
        received_ack = False

        while not received_ack:
            # Set the timeout to the estimated RTT times 4
            sock.settimeout(est_rtt)

            try:
                # Receive message from destination address
                ack_msg, addr = sock.recvfrom(1472)     
                header_from_msg = ack_msg[:12]          # Extract the header from the received message
                seq_num, ack_num, flags, win = parse_header(header_from_msg)  # Parse the header fields
                syn, ack, fin = parse_flags(flags)      # Parse the flags

                # If received ACK message is valid, update sequence number, empty sent packet list and set received_ack to True
                if ack and ack_num == sequence_num:
                    print("ACK msg: ack_num =", ack_num)

                    # Calculate the roundtrip time and update the estimated RTT to 4RTT
                    rtt = time.monotonic() - send_time
                    est_rtt = 4 * rtt

                    sequence_num += 1
                    received_ack = True
                    last_sent_packet = {}

                # If the acknowledgement message is a duplicate, resend the previous packet with the previous sequence number
                elif ack and ack_num == sequence_num - 1:
                    print("Received duplicate ACK msg with ack_num", ack_num)
                    send(sock, data[:1460], sequence_num - 1, addr)

            # If timeout occurs while waiting for ACK message, resend the pakcet with the current sequence number
            except timeout:
                print("Timeout occurred. Resending packet with seq_num =", sequence_num)
                send(sock, last_sent_packet[sequence_num], sequence_num, addr)


def RECV_GBN(sock, skip_ack):
    """
    Receive data using Go back N protocol

    Arguments:
        sock (socket): Socket object to receive data with
        skip_ack (bool): Whether to skip sending ACK message or not for test case

    Returns:
        Concatenated received data in bytes
    """
    # Perform three-way handshake
    handle_handshake(sock)

    # Initialize variables
    expected_seq_num = 1
    received_data = b""

    # Continuously receive packets and send back ACK messages if received packets are in-order
    while True:
        message, addr = sock.recvfrom(1472)
        seq_num, ack_num, flags, win = parse_header(message[:12])
        syn, ack, fin = parse_flags(flags)

        # Runs skip_ack test case
        if skip_ack:
            skip_ack = False
            print("Skipping first ACK msg")
            continue

        # If a new SYN message received, redo three-way handshake
        if syn:
            handle_handshake(sock)

        # If received packet has correct sequence number
        elif not ack and seq_num >= expected_seq_num:
            if not fin and seq_num == expected_seq_num:
                print("Received in-order with seq_num =", seq_num)
                received_data += message[12:]
                expected_seq_num += 1
                send_ack(sock, seq_num, addr)

            elif fin and not ack and seq_num == expected_seq_num:
                print("Received FIN msg with seq_num", seq_num)
                send_ack(sock, seq_num, addr)
                sock.close()
                return received_data
            
            else:
                print("Received out-of-order with seq_num =", seq_num)
                # Discarding out-of-order packets
                pass


def SEND_GBN(send_sock, addr, data, window_size, skip_seq_num):
    """
    Sends data using the Go-Back-N protocol

    Arguments:
        sock (socket): Socket object to use for sending and receiving data
        addr (tuple): IP address and port number of the server/receiver
        data (bytes): File data to be sent in bytes
        window_size (int): The size of the sliding window/the number of packets in flight
        skip_seq_num (bool): Whether to skip a sequence number or not for test cases

    Returns:
        Void
    """
    # Initiate three-way handshake
    initiate_handshake(send_sock, addr)

    # Initialize variables
    next_seq_num = 1
    base_seq_num = 1
    unacked_packets = {}
    data_offset = 0
    fin_sent = False
    
    # Loop until FIN message is sent
    while not fin_sent:
        # Initialize the estimated RTT 
        est_rtt = 0.5

        # Send packets while the number of unacknowledged packets is less than the window size
        while next_seq_num < base_seq_num + window_size:
            # Calculate the size of the next chunk of data to send
            chunk_size = min(1460, len(data) - data_offset)
            # If no more data and no more unacknowledged packets, send FIN message
            if chunk_size == 0:
                if not unacked_packets:
                    # All sent packets have been acknowledged, send FIN message
                    fin_packet = create_packet(next_seq_num, 0, 2, 0, b"")
                    send_sock.sendto(fin_packet, addr)
                    print("FIN msg sent. Waiting for ACK...")
                    fin_sent = True
                    break
                
                #  If there are unacknowledged packets, break out of the inner loop to wait for acknowledgements
                else:
                    break

            # Slices the next chunk of data to be sent from data
            chunk_data = data[data_offset : data_offset + chunk_size]

            # Skip sending packet with sequence number 5 if skip_seq_num is True.
            if skip_seq_num and next_seq_num == 5:
                skip_seq_num = False
                print("Skipping seq_num =", next_seq_num)
                unacked_packets[next_seq_num] = chunk_data
                next_seq_num += 1
                data_offset += chunk_size
                continue
            
            # Record packet send time
            send_time = time.monotonic() 

            # Send the packet, add its data to unacked_packets and increment sequence number and data_offset
            send(send_sock, chunk_data, next_seq_num, addr)
            unacked_packets[next_seq_num] = chunk_data
            next_seq_num += 1
            data_offset += chunk_size

        # If FIN message not sent, wait for acknowledgement for sent packet
        if not fin_sent:
            # Set timeout for receiving ACK message
            send_sock.settimeout(est_rtt)
            try:
                # Receive ACK message, parse header and flags
                ack_msg, addr = send_sock.recvfrom(1472)
                seq_num, ack_num, flags, win = parse_header(ack_msg[:12])
                syn, ack, fin = parse_flags(flags)

                # If ACK is received and within current window, update base_seq_num and remove acked packets from unacked packets
                if ack and ack_num >= base_seq_num:
                    print("ACK msg: ack_num =", ack_num)

                    # Calculate the roundtrip time and update the estimated RTT to 4RTT
                    rtt = time.monotonic() - send_time
                    est_rtt = 4 * rtt
                    
                    # Update base_seq_num
                    base_seq_num = ack_num + 1

                    # Update unacked packets list
                    new_unacked_packets = {}
                    for seq_num, packet_data in unacked_packets.items():
                        if seq_num >= base_seq_num:
                            new_unacked_packets[seq_num] = packet_data

                    unacked_packets = new_unacked_packets

            # Resend all unacked packets with original payload that timed out
            except timeout:
                print("Timeout occurred. Resending packets")
                for seq_num, packet_data in unacked_packets.items():
                    new_packet = create_packet(seq_num, 0, 0, 0, packet_data)
                    send_sock.sendto(new_packet, addr)
                
    # Wait for ACK for the FIN message
    while True:
        send_sock.settimeout(est_rtt)

        try:
            # Receive ACK message, parse header and flags
            ack_msg, addr = send_sock.recvfrom(1472)
            seq_num, ack_num, flags, win = parse_header(ack_msg[:12])
            syn, ack, fin = parse_flags(flags)

            # Exits if ack for FIN is received
            if ack and ack_num == next_seq_num:
                print("ACK for FIN msg received. Exiting...")
                break

        except timeout:   # Exits due to timeout
            print("Timeout occurred while waiting for ACK for FIN msg. Exiting...")
            break


def RECV_SR(sock, skip_ack, window_size):
    """
    Receives data from the sender using Selective Repeat protocol

    Arguments:
        sock (socket): Socket object to receive data with
        skip_ack (bool): Whether to skip sending ACK message or not for test case
        window_size (int): The size of the sliding window/the number of packets in flight

    Returns:
        A table of all of the received data in bytes, it is used application.py to transfer all the data to a file
    """
    # Perform three-way handshake
    handle_handshake(sock)

    # Initialize variables
    expected_seq_num = 1  # expected sequence number of the next in-order packet
    received_data = b""
    unacked_packets = {}  # dictionary of unacknowledged packets, the keys are the sequence no. of the packets

    while True:
        message, addr = sock.recvfrom(1472)  # Receives a packet
        seq_num, ack_num, flags, win = parse_header(message[:12])  # Parses header of packet
        syn, ack, fin = parse_flags(flags)  # Parse flags from the header

        if skip_ack:  # Runs skip_ack test case
            skip_ack = False
            print("Skipping first ACK msg")
            continue

        if syn:  # Perfoms handshake again if syn flag is used
            handle_handshake(sock)

        # Process packet if received packet is not an ACK and its sequence number is greater/equal to the expected sequence no.
        # and the no. of unacknowledged packets is less than the window size
        elif not ack and seq_num >= expected_seq_num and len(unacked_packets) < window_size:
            if not fin and seq_num == expected_seq_num:
                print("Received in-order with seq_num =", seq_num)
                received_data += message[12:]  # Add packet data to received data
                expected_seq_num += 1  # Update expected seq num to next in order packet

                send_ack(sock, seq_num, addr)  # Acknowledge the last received packet

                # Send acks for any other received but unacked packets
                while expected_seq_num in unacked_packets:
                    received_data += unacked_packets[expected_seq_num]  # Add unacked packet to received data
                    expected_seq_num += 1
                    del unacked_packets[expected_seq_num - 1]  # Remove acked packet from unacked packets list
                    send_ack(sock, expected_seq_num - 1, addr)

            # Close connection if packet is a FIN and sequence no. and expected sequence no. is equal
            elif fin and not ack and seq_num == expected_seq_num:
                print("Received FIN msg with seq_num", seq_num)
                send_ack(sock, seq_num, addr)
                sock.close()
                return received_data
            
            else:  # Packet is out of order and is added to unacked_packets
                print("Received out-of-order with seq_num =", seq_num)
                # Send an acknowledgment for the last received in-order packet
                send_ack(sock, expected_seq_num - 1, addr)
                # Add the out-of-order packet to the unacknowledged list
                unacked_packets[seq_num] = message[12:]

                # Send acks for any other received but unacknowledged packets in order
                while expected_seq_num in unacked_packets:
                    received_data += unacked_packets[expected_seq_num]
                    expected_seq_num += 1
                    del unacked_packets[expected_seq_num - 1]
                    send_ack(sock, expected_seq_num - 1, addr)


def SEND_SR(send_sock, addr, data, window_size, skip_seq_num):
    """
    Sends data to the receiver using the Selective Repeat protocol

    Arguments:
        send_sock (socket): Socket object to use for sending and receiving data
        addr (tuple): IP address and port number of the server/receiver
        data (bytes): File data to be sent in bytes
        window_size (int): The size of the sliding window/the number of packets in flight
        skip_seq_num (bool): Whether to skip a sequence number or not for test cases

    Returns:
        Void
    """
    # Initiate three-way handshake
    initiate_handshake(send_sock, addr)

    # Initialize variables
    next_seq_num = 1
    base_seq_num = 1
    unacked_packets = {}
    data_offset = 0
    fin_sent = False
    
    # Loop until FIN message is sent
    while not fin_sent:
        # Initialize the estimated RTT
        est_rtt = 0.5

        # Send packets while the number of unacknowledged packets is less than the window size
        while next_seq_num < base_seq_num + window_size:
            # Calculate the size of the next chunk of data to send
            chunk_size = min(1460, len(data) - data_offset)
            # If no more data and no more unacknowledged packets, send FIN message
            if chunk_size == 0:  
                if not unacked_packets:
                    # All data has been sent and acknowledged, send FIN message
                    fin_packet = create_packet(next_seq_num, 0, 2, 0, b"")
                    send_sock.sendto(fin_packet, addr)
                    print("FIN msg sent. Waiting for ACK...")
                    fin_sent = True
                    break

                #  If there are unacknowledged packets, break out of the inner loop to wait for acknowledgements
                else:
                    break

            # Slices the next chunk of data to be sent from data
            chunk_data = data[data_offset : data_offset + chunk_size]

            # Skip sending packet with sequence number 5 if skip_seq_num is True.
            if skip_seq_num and next_seq_num == 5:
                skip_seq_num = False
                print("Skipping seq_num =", next_seq_num)
                unacked_packets[next_seq_num] = chunk_data
                next_seq_num += 1
                data_offset += chunk_size
                continue
            
            # Record packet send time
            send_time = time.monotonic()    

            # Send the packet, add it to unacked packets and update next seq num and data offset
            send(send_sock, chunk_data, next_seq_num, addr)
            unacked_packets[next_seq_num] = chunk_data
            next_seq_num += 1
            data_offset += chunk_size

        # If FIN message not sent, wait for acknowledgement for sent packet
        if not fin_sent:
            # Set timeout for receiving ACK message
            send_sock.settimeout(est_rtt)
            try:
                # Receive ACK message, parse header and flags
                ack_msg, addr = send_sock.recvfrom(1472)
                seq_num, ack_num, flags, win = parse_header(ack_msg[:12])
                syn, ack, fin = parse_flags(flags)

                # If ACK is received and within current window, update base_seq_num and remove acked packets from unacked packets
                if ack and ack_num >= base_seq_num:
                    print("ACK msg: ack_num =", ack_num)

                    # Calculate the roundtrip time and update the estimated RTT to 4RTT
                    rtt = time.monotonic() - send_time
                    est_rtt = 4 * rtt

                    # Remove acknowledged packets from unacked_packets and update base_seq_num 
                    if ack_num in unacked_packets:
                        del unacked_packets[ack_num]
                        base_seq_num = ack_num + 1

            # Resend unacked packets that timed out
            except timeout:
                print("Timeout occurred. Resending packets")
                for seq_num, packet_data in unacked_packets.items():
                    new_packet = create_packet(seq_num, 0, 0, 0, packet_data)
                    send_sock.sendto(new_packet, addr)

    # Wait for ACK for the FIN message
    while True:
        send_sock.settimeout(est_rtt)

        try:
            ack_msg, addr = send_sock.recvfrom(1472)
            seq_num, ack_num, flags, win = parse_header(ack_msg[:12])
            syn, ack, fin = parse_flags(flags)

            # Exits if ack for FIN is received
            if ack and ack_num == next_seq_num:
                print("ACK for FIN msg received. Exiting...")
                break

        except timeout:  # Exits due to timeout
            print("Timeout occurred while waiting for ACK for FIN msg. Exiting...")
            break
