#!/usr/bin/env python3
from constants import *
import binascii
import time

class Disk():
    def __init__(self, file, size):
        self.disk = file
        self.size = size
        self.open = OPEN
        self.numBlocks = int(size / BLOCKSIZE)

disks = []  # Will hold all the disks as tuples (filename, open)

def openDisk(filename, nBytes):
    if(nBytes < 0):                     # nBytes must be >= 0
        return ERR_DSKSIZE
    elif(nBytes == 0):                  # Open existing disk without overwriting anything
        try:                            # Try opening for reading & writing
            disk = open(filename, 'r+b')
        except:
            return ERR_OPEN
    else:
        try:
            # Create/Truncate new disk and initialize bytes to 0
            disk = open(filename, 'w+b')
            disk.write(b'\x00' * nBytes)   # Initialize all bytes to 0
        except:
            return ERR_CREAT
    disks.append(Disk(disk, nBytes))    # Add new disk to array as (filename=disk, open=1)
    return len(disks)-1                 # Return index of new disk

def readBlock(disk, bNum, block):
    # Assumes block is a bytearray
    # Check that valid disk is selected
    if(disk > (len(disks)-1)):
        return ERR_INVALID_DISK
    if(disks[disk].open == CLOSED):
        return ERR_CLOSED
    if(bNum >= disks[disk].numBlocks):
        return ERR_INVALID_BNUM
    
    # If open/valid, read block from disk
    currDisk = disks[disk].disk
    currDisk.seek(bNum*BLOCKSIZE)
    inBlock = bytearray(currDisk.read(BLOCKSIZE))
    for i in range(BLOCKSIZE):
        block[i] = inBlock[i]
    return SUCCESS

def writeBlock(disk, bNum, block):
    # Assumes block is bytearray
    # Check that valid disk is selected
    if(disk > (len(disks)-1)):
        return ERR_INVALID_DISK
    if(disks[disk].open == CLOSED):
        return ERR_CLOSED
    if(bNum >= disks[disk].numBlocks):
        return ERR_INVALID_BNUM

    # If open/valid, write block to disk
    currDisk = disks[disk].disk
    buffer = bytearray(block)[:BLOCKSIZE]   # Cut to BLOCKSIZE bytes
    currDisk.seek(bNum*BLOCKSIZE)           # Seek to correct logical block
    currDisk.write(bytes(buffer))           # Write bytes to disk

    return 0

def closeDisk(disk):
    # Make sure disk is valid/open
    if(disk > (len(disks)-1)):
        return ERR_INVALID_DISK
    
    currDisk = disks[disk].disk
    disks[disk].open = CLOSED
    currDisk.close()
    

def main():
    block = bytearray(BLOCKSIZE)
    for i in range(BLOCKSIZE):
        block[i] = 0xFF

    testDisk = openDisk("testDisk", 3*BLOCKSIZE)
    disk1 = openDisk("disk1", 10*BLOCKSIZE)
    disk2 = openDisk("disk2", 4*BLOCKSIZE)

    currDisk = "testDisk"
    blockNum = 1
    status = writeBlock(testDisk, blockNum, block)
    if(status < 0):
        print("ERROR CODE: {}".format(status))
        print("FAILED TO READ/WRITE THE FOLLOWING BLOCK to '{}' disk\n{}\n".format(currDisk, binascii.hexlify(block)))
    
    blockNum = 4
    status = writeBlock(testDisk, blockNum, block)
    if(status < 0):
        print("ERROR CODE: {}".format(status))
        print("FAILED TO READ/WRITE THE FOLLOWING BLOCK to '{}' disk\n{}\n".format(currDisk, binascii.hexlify(block)))
    
    buffer = bytearray(BLOCKSIZE)
    print(readBlock(testDisk, 1, buffer))
    print(buffer)

    currDisk = "disk1"
    blockNum = 0
    status = writeBlock(disk1, blockNum, block)
    if(status < 0):
        print("ERROR CODE: {}".format(status))
        print("FAILED TO READ/WRITE THE FOLLOWING BLOCK to '{}' disk\n{}\n".format(currDisk, binascii.hexlify(block)))
    for i in range(0, BLOCKSIZE, 4):
        block[i] = 0xDE
        block[i+1] = 0xAD
        block[i+2] = 0xBE
        block[i+3] = 0xEF

    blockNum = 1
    status = writeBlock(disk1, blockNum, block)
    if(status < 0):
        print("ERROR CODE: {}".format(status))
        print("FAILED TO READ/WRITE THE FOLLOWING BLOCK to '{}' disk\n{}\n".format(currDisk, binascii.hexlify(block)))

    closeDisk(testDisk)
    closeDisk(disk1)
    closeDisk(disk2)



if __name__ == '__main__':
    main()