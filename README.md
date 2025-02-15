# Portfolio-2
There are two programs in this Portfolio. The first program, `DRTP.py`, is a custom reliable transfer protocol that is built on UDP. This protocol ensures all packets are delivered in-order, without loss and duplicates. The second program, `application.py` is a client/server program that uses the custom reliable transfer protocol, DRTP, to send a file between two end hosts. Both programs are built with python3.

There are three reliability functions:
1. `SAW`, *Stop-And-Wait protocol*: 
    - The sender sends a packet and waits for an ACK. If an ACK is received, it sends a new packet. If not, it waits for a timeout and then resends the packet. If the sender receives a duplicate ACK, it resends the packet.
2. `GBN`, *Go-Back-N protocol*:
    - The sender uses a fixed window size of 5 packets to transfer data, where the sequence numbers represent the packets (packet 1 = 1, packet 2 = 2, etc.). If no ACK packet is received before timeout, all unacknowledged packets are assumed to be lost and are retransmitted. The receiver processes incoming packets in order, and any out-of-order packets indicate packet loss or reordering in the network. In such cases, the DRTP receiver does not acknowledge or process the packets and may discard them.
3. `SR`, *Selective-Repeat protocol*:
    - Based of Go-Back-N protocol, but it differs in that it buffers out-of-order packets instead of discarding them as GBN does. 

# How to run the program
To use the file transfer application (`application.py`):
1. You need to have Python3 installed in your system.
2. In two terminals, navigate to the directory where the code `application.py` and `DRTP.py` are located.
3. Start the program in server mode on one terminal, and then client mode on the other terminal.

## Server mode
To run `application.py` in server/receiver mode with the default options, it can be invoked as:

    python3 application.py -s

* `-s, --server`: run in server mode; receives a file over DRTP/UDP from sender and writes it to the file system

To run the server/receiver mode with the all the available options, it can be invoked as:

    python3 application.py -s -i <ip_address> -p <port_number> -r <reliable_method> -t <test_case>

* `-i, --ip_address`: the IP address to bind the server to (default: `127.0.0.1`)
* `-p, --port`: the port number to listen for incoming connections (default: `12000`)
* `-r, --reliability`: the reliability function, the available options are `SAW`, `GBN` and `SR`,  (default: `SAW`)
* `-t, --test`: test protocol to skip an ack to trigger retransmission at the client/sender-side (e.g. `skip_ack`)

## Client mode
To operate `application.py` in client/sender mode with the default options, it can be invoked as follows:

    python3 application.py -c

* `-c, --client`: run in client mode; reads file from computer and sends it to receiver over DRTP/UDP

To run the client/sender mode with the all the available options, it can be invoked as:

    python3 application.py -c -i <ip_address> -p <port_number> -f <file_to_transfer.jpg> -r <reliable_method> -w <window_size> -t <test_case>

* `-i, --ip_address`: the IP address to bind the server to (default: `127.0.0.1`)
* `-p, --port`: the port number to listen for incoming connections (default: `12000`)
* `-f, --file_name`: the name of the file to send over (default: `./testFile.jpg`)
* `-r, --reliability`: the reliability function, the available options are `SAW`, `GBN` and `SR`,  (default: `SAW`)
* `-t, --test`: test protocol to test packet loss scenario (e.g. `loss`)
* `-w, --window`: the window size for the `GBN` and `SR` protocols (default: `5`)

> **NOTE** The server and client ***MUST*** use the same `<ip_address>`, `<port>` and `<reliable_method>` arguments to connect

# How to generate data
The easiest way to test the program is to run it on any terminal as explained above. 

This project aims to test the code in a virtual network using mininet in different test scenarios. The tests are conducted on the topology provided in the `simple-topo.py` file. To run the same tests, on a recent release of Ubuntu or Debian, install mininet, xterm and iperf if it has not been installed already. Once installed, you can run the following test cases.

## Test case 1
Run the file transfer application with the three reliable protocols (`GBN` and `SR` with window sizes 5, 10, 15) using RTTs 25, 50 and 100ms. To change the RTT values go to the `simple-topo.py` file and edit the delay values in line 28 and 29 to get the desired RTT. Run a simple ping test to confirm, e.g.

    ping 10.0.1.2 from h1

First, run server with respective reliable method, e.g.

    python3 application.py -s -i 10.0.1.2 -r SAW

The client for the different scenarios with respective reliable method 

1. Run `SAW` with three RTT values: 25, 50, and 100ms, e.g.

        python3 application.py -c -i 10.0.1.2 -f <file_to_transfer.jpg> -r SAW

2. Run `GBN` with window size 5 for three different RTT values. Repeat the same for window sizes 10 and 15, e.g.

        python3 application.py -c -i 10.0.1.2 -f <file_to_transfer.jpg> -r GBN -w 5

3. Run `SR` with window size 5 for three different RTT values. Repeat the same for window sizes 10 and 15, e.g.

        python3 application.py -c -i 10.0.1.2 -f <file_to_transfer.jpg> -r SR -w 5


## Test case 2
Skip an acknowledgment message at the receiver side to trigger retransmission with the three reliable protocols. 

Run server with respective reliable method, e.g.

    python3 application.py -s -i 10.0.1.2 -r SAW -t SKIP_ACK

Run client with respective reliable method, e.g.

    python3 application.py -c -i 10.0.1.2 -f <file_to_transfer.jpg> -r SAW

## Test case 3
Skip a sequence number at the sender side to show the out-of-order delivery effect, and trigger retransmission with the `GBN` and `SR` reliable protocols.

Run server with respective reliable method, e.g.

    python3 application.py -s -i 10.0.1.2 -r GBN

Run client with respective reliable method, e.g.

    python3 application.py -c -i 10.0.1.2 -r GBN -t LOSS

## Test case 4
Test case 4 consists of fact analyzing, discussing and summarizing the results found in Tests 2 and 3, which is what we have in the PDF file.
