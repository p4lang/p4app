#!/usr/bin/env python

import sys
import struct
import argparse

mold_hdr_struct = struct.Struct("!10s Q H")

add_order_struct = struct.Struct("!c H H 6s Q c L 8s L")
uint64_struct = struct.Struct("!Q")
uint16_struct = struct.Struct("!H")


message_sizes = dict(S=12, R=39, H=25, Y=20, L=26, V=35, W=12, K=28, A=36,
                     F=40, E=31, C=36, X=23, D=19, U=35, P=44, Q=40, B=19,
                     I=50, N=20)

def fmtStock(stock):
    assert len(stock) <= 8
    return "%-8s" % stock

# I assume that this host is little-endian
def hton48(i):
    return uint64_struct.pack(i)[:6]

def AddOrderMessage(
	MessageType='A',
        StockLocate=0,
        TrackingNumber=0,
	Timestamp=0,
	OrderReferenceNumber=0,
	BuySellIndicator='S',
	Shares=0,
	Stock='EMPTY   ',
	Price=0
        ):

    StockLocate, TrackingNumber, Timestamp = int(StockLocate), int(TrackingNumber), int(Timestamp)
    OrderReferenceNumber, Shares, Price = int(OrderReferenceNumber), int(Shares), int(Price)

    data = add_order_struct.pack(MessageType, StockLocate, TrackingNumber,
            hton48(Timestamp), OrderReferenceNumber, BuySellIndicator,
            Shares, fmtStock(Stock), Price)

    assert len(data) == 36

    return data

def makeDummyMessageConstructor(MessageType, size):
    assert len(MessageType) == 1, "MessageType should be a single char"
    def DummyMessage(**kwargs):
        data = MessageType + "\0" * (size - 1)
        return data
    return DummyMessage

def MessageForType(MessageType):
    if MessageType == 'A':
        return AddOrderMessage
    elif MessageType in message_sizes:
        return makeDummyMessageConstructor(MessageType, message_sizes[MessageType])
    else:
        raise Exception("Unknown message type '%s'" % MessageType)


def MoldMessage(payload):
    size_header = uint16_struct.pack(len(payload))
    return size_header + payload

def MoldPacket(
        Session=0,
        SequenceNumber=0,
        MessageCount=None,
        MessagePayloads=[]
        ):

    packed_session = uint64_struct.pack(Session) + "\0\0"
    if MessageCount is None: MessageCount = len(MessagePayloads)
    data = mold_hdr_struct.pack(packed_session, SequenceNumber, MessageCount)
    for payload in MessagePayloads:
        data += MoldMessage(payload)

    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a dump of ITCH messages')
    parser.add_argument('filename', nargs='?', help='Path to output file, or "-" for STDOUT',
            type=str, default='-')
    parser.add_argument('--message-type', '-t', help='1 char ID of MessageType to generate',
            type=str, choices=message_sizes.keys(), default='A')
    parser.add_argument('--fields', '-f', help='Field values. E.g. StockLocate=1,Price=33',
            type=lambda s: dict(f.split('=') for f in s.split(',')), default=dict())
    args = parser.parse_args()

    with (sys.stdout if args.filename == '-' else open(args.filename, 'wb')) as fd:
        Message = MessageForType(args.message_type)
        fd.write(MoldMessage(Message(**args.fields)))
