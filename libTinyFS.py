#!/usr/bin/env python3
from libDisk import *
import globalVars
from math import *
import time
import os
import sys


# Tracked by OS
filesystems = {}    # Tracks all created FS's
curr_FS = None      # Currently mounted filesystem
mounted = False     # FS is currently mounted / not

# File system layout:
# Block 0: Superblock
# Blocks 1-2: Extra space for freeblock bitmap
# Blocks 3-7: Space for Inode Table
# Blocks > 7: Data Region

# Limitations
# FS must be at least 2560 bytes (10 blocks, 8 needed for FS metadata, 2 for an inode and 1-block file)
# FS must be at most 1568768 bytes (8 blocks for metadata, then entire freeblock bitmap is full) 
# Files must be at least 256 bytes and at most 15104 bytes (full INode data block list)

# Filesystem object
class FS:
    def __init__(self, nBytes, disk):
        self.mounted = False
        self.nBlocks = int(nBytes / BLOCKSIZE)
        self.disk = disk
        self.files = {}
        self.extra_blocks = 0
        self.free_blocks = self.nBlocks - 8 # First 8 blocks are for tracking FS metadata

        # Number of bits per address / bits per byte = bytes per address
        self.addr_size = int(ceil(ceil(log(self.nBlocks, 2)) / float(8)))


# File Entry object
class Filent:
    def __init__(self, filename):
        self.filename = filename
        self.offset = 0
        self.bNums = []                     # Block Numbers

# File stat entry
class Stat:
    def __init__(self, name, index, perms, itype, size, nBlocks, ctime, atime, mtime):
        self.name = name        # Name of file
        self.index = index      # The index part of "index node"
        self.type = itype       # The type of file inode points to
        self.perms = perms      # Permissions: Only supports Read-Only (RO) and Read/Write (RW)
        self.size = size        # Size of data in file
        self.nBlocks = nBlocks  # Number of data blocks allocated for file
        self.ctime = ctime      # Creation time 
        self.atime = atime      # Time of last access
        self.mtime = mtime      # Time of last modification

    def translate_type(self):
        # Translate inode type constant to correspond string
        if(self.type == MODE_SB):
            return "superblock"
        elif(self.type == MODE_DIR):
            return "directory"
        elif(self.type == MODE_DATA):
            return "data"

    def translate_perms(self):
        # Translate inode perms constant to corresponding string
        if(self.perms == PERMS_RO):
            return "Read-Only (RO)"
        elif(self.perms == PERMS_RW):
            return "Read/Write (RW)"

    def print_info(self):
        # Prints all data held by Stat obj
        print(f"{' -----':<9}{'Printing data for inode {}'.format(self.index)}{'----- ':>9}")
        print(
            " File name: \t\t{}\n".format(self.name),
            "File Type: \t\t{}\n".format(self.translate_type()),
            "Permissions: \t\t{}\n".format(self.translate_perms()),
            "File Size: \t\t{} bytes\n".format(self.size),
            "Blocks allocated: \t{}\n".format(self.nBlocks),
            "Creation Time: \t{}\n".format(convert_time(self.ctime)),
            "Access Time: \t\t{}\n".format(convert_time(self.atime)),
            "Modification Time: \t{}\n\n".format(convert_time(self.mtime))
            )

def tfs_mkfs(filename, nBytes):
    fs_disk = openDisk(filename, nBytes)
    if(fs_disk >= 0):                       # FS creation was successful
        new_fs = FS(nBytes, fs_disk)        # Create new FS
        extra_blocks = create_superblock(new_fs.disk, new_fs.addr_size, new_fs.nBlocks, new_fs.free_blocks)
        new_fs.extra_blocks = extra_blocks
        filesystems[filename] = new_fs
        return SUCCESS
    else:                                   # FS creation failed
        return ERR_FAILED_CREAT

def tfs_mount(filename):
    global mounted
    global curr_FS
    if(mounted == True):
        return ERR_MOUNTED_FS
    
    # Check superblock for magic number
    new_FS = filesystems[filename]
    superblock = bytearray(BLOCKSIZE)
    readBlock(new_FS.disk, 0, superblock)
    if(superblock[0] != MAGIC_NUMBER):
        return ERR_INVALID_FS

    curr_FS = new_FS
    mounted = True 
    return SUCCESS

def tfs_unmount():
    global curr_FS
    global mounted
    if(not mounted):
        return ERR_MOUNTED_NONE
    
    curr_FS = None
    mounted = False
    return SUCCESS

def tfs_open(name):
    global curr_FS
    # Make sure FS is actually mounted
    if(not mounted):
        return ERR_MOUNTED_NONE

    # Create new inode, and inode-name pair in root dir
    # Find free inode block
    for inode_bNum in range(INODE_TABLE_SIZE):
        inode_entry_block = bytearray(BLOCKSIZE)
        readBlock(curr_FS.disk, 1+BITMAP_BLOCKS+inode_bNum, inode_entry_block)
        inode_ind = find_free_inode(inode_entry_block)
        if(inode_ind >= 0):
            # Found free inode, now create inode
            # Find free block on disk to put inode on
            inode_blk_ind = find_freeblock(curr_FS.disk, curr_FS.extra_blocks)
            new_inode = create_inode(MODE_DATA, 0, [])
            # Set creation time to be now
            inode_set_data(new_inode, INODE_CTIME, INODE_SIZE_TIME, int(time.time()))
            writeBlock(curr_FS.disk, inode_blk_ind, new_inode)
            remove_freeblock(curr_FS.disk, inode_blk_ind, curr_FS.extra_blocks)
            curr_FS.free_blocks -= 1

            inode_entry = bytearray(INODE_ENTRY_SIZE)
            # Start with name
            name_bytes = bytearray(name, 'ascii')
            for i in range(len(name)):
                inode_entry[i] = name_bytes[i]
            # Now add index (block number on disk)
            for i in range(ADDR_SIZE):
                inode_entry[NAME_SIZE+ADDR_SIZE-(1+i)] = (inode_blk_ind & (0xFF << (8*i))) >> (8*i)
    
            # inode has been created and written on disk, update inode table
            for i in range(INODE_ENTRY_SIZE):
                inode_entry_block[(inode_ind*INODE_ENTRY_SIZE)+i] = inode_entry[i]
            writeBlock(curr_FS.disk, 1+BITMAP_BLOCKS+inode_bNum, inode_entry_block)
            FD = ((int(BLOCKSIZE / INODE_ENTRY_SIZE)) * inode_bNum) + inode_ind

            # Create new file entry and add to FS's list of files
            new_filent = Filent(name)
            curr_FS.files[FD] = new_filent

            return FD
    return ERR_NO_FREEBLOCKS

def inode_parse_entry(inode_entry):
    # Parses inode entry and returns tuple of (name, index)
    name_bytes = bytearray(NAME_SIZE)
    for i in range(NAME_SIZE):
        name_bytes[i] = inode_entry[i]
    name = bytes(name_bytes).decode()
    index = 0
    for i in range(ADDR_SIZE):
        index |= (inode_entry[NAME_SIZE+i] << (8*(ADDR_SIZE-(i+1))))
    return (name, index)

def find_free_inode(inode_block):
    # Searches inode_block for free inode pair opening and returns index if successful
    # Index = index in inode_block list not index on disk array of bytes
    for i in range(int(BLOCKSIZE / INODE_ENTRY_SIZE)):
        inode_entry = inode_block[(i*INODE_ENTRY_SIZE):((i*INODE_ENTRY_SIZE)+INODE_ENTRY_SIZE)]
        found = True
        for j in range(INODE_ENTRY_SIZE):
            if((inode_entry[j] & 0xFF) != 0):
                found = False
        if(found):
            return i
    return -1

def inode_get_entry(FD):
    # Given FD, return inode entry
    global curr_FS
    inode_bNum = int(FD / (BLOCKSIZE / INODE_ENTRY_SIZE))
    inode_offset = FD - (inode_bNum * INODE_ENTRY_SIZE)
    inode_block = bytearray(BLOCKSIZE)
    readBlock(curr_FS.disk, 1+BITMAP_BLOCKS+inode_bNum, inode_block)
    return inode_block[(inode_offset*INODE_ENTRY_SIZE):((inode_offset*INODE_ENTRY_SIZE)+INODE_ENTRY_SIZE)]

def inode_remove_entry(FD):
    global curr_FS
    inode_bNum = int(FD / (BLOCKSIZE / INODE_ENTRY_SIZE))
    inode_offset = FD - (inode_bNum * INODE_ENTRY_SIZE)
    inode_block = bytearray(BLOCKSIZE)
    readBlock(curr_FS.disk, 1+BITMAP_BLOCKS+inode_bNum, inode_block)
    for i in range(INODE_ENTRY_SIZE):
        inode_block[(inode_offset*INODE_ENTRY_SIZE)+i] = 0x00
    writeBlock(curr_FS.disk, 1+BITMAP_BLOCKS+inode_bNum, inode_block) 

def inode_update_blocks(inode_block, blocks):
    # Updates inode with new data blocks
    blk_index = INODE_METADATA
    for block in blocks:
        for i in range(ADDR_SIZE):
            inode_block[blk_index+ADDR_SIZE-(i+1)] = (block & (0xFF << (8*i))) >> (8*i)
        blk_index += ADDR_SIZE

def inode_update_size(inode_block, size):
    # Updates the 'size' field in the inode block
    inode_block[2] = (size & (0xFF << 8)) >> 8
    inode_block[3] = size & (0xFF)

def inode_get_blocks(inode_block):
    # Gets blocks from inode block
    blocks = []
    blk_index = INODE_METADATA
    more_blocks = True
    next_blk = bytearray()
    while(more_blocks and (blk_index < BLOCKSIZE)):
        next_blk = inode_block[blk_index:blk_index+ADDR_SIZE]
        more_blocks = False
        for i in range(ADDR_SIZE):
            if(next_blk[i] != 0x00):
                more_blocks = True
        if(more_blocks):
            blocks.append(int.from_bytes(next_blk, 'big'))
        blk_index += ADDR_SIZE
    return blocks
        
def inode_get_data(inode_block, start, size):
    # Gets data from inode, starting at a given index
    # Translates multiple bytes of data into one number
    t = 0
    for i in range(size):
        t |= (inode_block[start+i] << (8*(size-(1+i))))
    return t

def inode_set_data(inode_block, start, size, data):
    # Sets data field of an inode
    # Translates 'data' into multiple bytes as determined by 'size'
    for i in range(size):
        inode_block[start+i] = (data & (0xFF << (8*(size-(1+i))))) >> (8*(size-(1+i)))

def tfs_stat(FD):
    # All metadata stored in inode
    inode_block = inode_get_block(FD)
    inode_entry = inode_parse_entry(inode_get_entry(FD))
    itype = inode_get_data(inode_block, INODE_TYPE, INODE_SIZE_TYPE)
    perms = inode_get_data(inode_block, INODE_PERMS, INODE_SIZE_PERMS)
    isize = inode_get_data(inode_block, INODE_FILESIZE, INODE_SIZE_FILESIZE)
    nBlocks = inode_get_data(inode_block, INODE_NBLOCKS, INODE_SIZE_NBLOCKS)
    ctime = inode_get_data(inode_block, INODE_CTIME, INODE_SIZE_TIME)
    atime = inode_get_data(inode_block, INODE_ATIME, INODE_SIZE_TIME)
    mtime = inode_get_data(inode_block, INODE_MTIME, INODE_SIZE_TIME)
    return Stat(inode_entry[INODE_ENTRY_NAME], FD, perms, itype, isize, nBlocks, ctime, atime, mtime)

def get_FD(name):
    # Gets FD for a file from its name
    global curr_FS
    for FD in curr_FS.files:
        if(curr_FS.files[FD].filename == name):
            return FD
    return ERR_NO_FD

def tfs_makeRO(name):
    global curr_FS
    # Make sure file exists and grab its file descriptor
    FD = get_FD(name)
    if(FD == ERR_NO_FD):
        return ERR_FILE_NOT_FOUND

    # Get and change inode to make it read-only
    inode_block = inode_get_block(FD)
    inode_set_data(inode_block, INODE_PERMS, INODE_SIZE_PERMS, PERMS_RO)

    # Update inode's modify/access times to reflect change
    atime_mtime = int(time.time())
    inode_set_data(inode_block, INODE_ATIME, INODE_SIZE_TIME, atime_mtime)
    inode_set_data(inode_block, INODE_MTIME, INODE_SIZE_TIME, atime_mtime)

    inode_bNum = inode_parse_entry(inode_get_entry(FD))[INODE_ENTRY_INDEX]

    # Write updated inode back to disk
    writeBlock(curr_FS.disk, inode_bNum, inode_block)
    return SUCCESS

def tfs_makeRW(name):
    global curr_FS
    # Make sure file exists and grab its file descriptor
    FD = get_FD(name)
    if(FD == ERR_NO_FD):
        return ERR_FILE_NOT_FOUND

    # Get and change inode to make it read-only
    inode_block = inode_get_block(FD)
    inode_set_data(inode_block, INODE_PERMS, INODE_SIZE_PERMS, PERMS_RW)

    # Update inode's modify/access times to reflect change
    atime_mtime = int(time.time())
    inode_set_data(inode_block, INODE_ATIME, INODE_SIZE_TIME, atime_mtime)
    inode_set_data(inode_block, INODE_MTIME, INODE_SIZE_TIME, atime_mtime)

    inode_bNum = inode_parse_entry(inode_get_entry(FD))[INODE_ENTRY_INDEX]

    # Write updated inode back to disk
    writeBlock(curr_FS.disk, inode_bNum, inode_block)
    return SUCCESS

def tfs_writeByte(FD, offset, data):
    # NOTE: Assumes data is given as a bytes object
    global curr_FS
    # Make sure FS is actually mounted
    if(not mounted):
        return ERR_MOUNTED_NONE

    if(FD not in curr_FS.files):        # Make sure file is open
        return ERR_INVALID_FD
    
    # Get inode entry to find where inode is, so it can be updated later
    inode_entry = inode_get_entry(FD)
    inode_bNum = inode_parse_entry(inode_get_entry(FD))[INODE_ENTRY_INDEX]
    inode_block = bytearray(BLOCKSIZE)
    readBlock(curr_FS.disk, inode_bNum, inode_block)

    # Check to make sure file is NOT read-only (RO)
    perms = inode_get_data(inode_block, INODE_PERMS, INODE_SIZE_PERMS)
    if(perms == PERMS_RO):
        return ERR_INVALID_PERMS

    # Make sure offset isn't outside file's boundaries
    size = inode_get_data(inode_block, INODE_FILESIZE, INODE_SIZE_FILESIZE)
    f = curr_FS.files[FD]
    if(f.offset >= size):
        return ERR_INVALID_OFFSET

    # Offset is valid, find which data block byte is in
    dbNums = inode_get_blocks(inode_block)
    dbNum = dbNums[int(offset / BLOCKSIZE)]
    dbOffset = int(offset % BLOCKSIZE)

    data_block = bytearray(BLOCKSIZE)
    readBlock(curr_FS.disk, dbNum, data_block)

    # Once you have data block, insert data at offset
    data_block[dbOffset] = data

    # Write updated datablock back onto disk
    writeBlock(curr_FS.disk, dbNum, data_block)

    # Update inode block with new access/modification time
    atime_mtime = int(time.time())
    inode_set_data(inode_block, INODE_ATIME, INODE_SIZE_TIME, atime_mtime)
    inode_set_data(inode_block, INODE_MTIME, INODE_SIZE_TIME, atime_mtime)
    writeBlock(curr_FS.disk, inode_bNum, inode_block)
    return SUCCESS


# Closes the file and removes dynamic resource table entry
def tfs_close(FD):
    global curr_FS
    # Make sure FS is actually mounted
    if(not mounted):
        return ERR_MOUNTED_NONE
    if(FD >= len(curr_FS.files)):       # Make sure file is open for closing
        return ERR_INVALID_FD  

    curr_FS.files[FD] = None            # Remove Filent (set to None)     
    return SUCCESS

def tfs_write(FD, buffer, size):
    global curr_FS
    # Make sure FS is actually mounted
    if(not mounted):
        return ERR_MOUNTED_NONE

    if(FD not in curr_FS.files):        # Make sure file is open
        return ERR_INVALID_FD
    
    # Get inode entry to find where inode is, so it can be updated later
    inode_entry = inode_get_entry(FD)
    inode_bNum = int.from_bytes(bytes(inode_entry[NAME_SIZE:NAME_SIZE+ADDR_SIZE]), 'big')
    inode_block = bytearray(BLOCKSIZE)
    readBlock(curr_FS.disk, inode_bNum, inode_block)

    # Check to make sure file is NOT read-only (RO)
    perms = inode_get_data(inode_block, INODE_PERMS, INODE_SIZE_PERMS)
    if(perms == PERMS_RO):
        return ERR_INVALID_PERMS

    # Make sure there are enough free blocks
    fBlocks = int(size / BLOCKSIZE)
    if(fBlocks > curr_FS.free_blocks):
        return ERR_NO_FREEBLOCKS

    # Find all the free blocks you can use for file
    bNums = []
    for i in range(fBlocks):
        # Find freeblock and mark as no longer free on bitmap
        bNum = find_freeblock(curr_FS.disk, curr_FS.extra_blocks)
        remove_freeblock(curr_FS.disk, bNum, curr_FS.extra_blocks)
        bNums.append(bNum)

    # Update inode block with data blocks and new size/nBlocks/atime/mtime
    inode_update_blocks(inode_block, bNums)
    inode_set_data(inode_block, INODE_FILESIZE, INODE_SIZE_FILESIZE, size)
    inode_set_data(inode_block, INODE_NBLOCKS, INODE_SIZE_NBLOCKS, len(bNums))
    atime_mtime = int(time.time())
    inode_set_data(inode_block, INODE_ATIME, INODE_SIZE_TIME, atime_mtime)
    inode_set_data(inode_block, INODE_MTIME, INODE_SIZE_TIME, atime_mtime)

    writeBlock(curr_FS.disk, inode_bNum, inode_block)

    # Now write the data blocks
    for i in range(len(bNums)):
        data_block = buffer[(i*BLOCKSIZE):(i*BLOCKSIZE)+BLOCKSIZE]
        writeBlock(curr_FS.disk, bNums[i], data_block)
    
    return SUCCESS
    
def inode_get_block(FD):
    # Gets inode block given FD
    inode_entry = inode_get_entry(FD)
    inode_bNum = int.from_bytes(bytes(inode_entry[NAME_SIZE:NAME_SIZE+ADDR_SIZE]), 'big')
    inode_block = bytearray(BLOCKSIZE)
    readBlock(curr_FS.disk, inode_bNum, inode_block)
    return inode_block

# deletes a file and marks its blocks as free on disk.
def tfs_delete(FD):
    global curr_FS
    # Make sure FS is actually mounted
    if(not mounted):
        return ERR_MOUNTED_NONE

    # Get File Entry for file to be deleted
    if(FD not in curr_FS.files):
        return ERR_INVALID_FD
    filent = curr_FS.files[FD]

    # Find inode and its associated datablocks, to be removed later
    inode_entry = inode_get_entry(FD)
    inode_bNum = int.from_bytes(bytes(inode_entry[NAME_SIZE:NAME_SIZE+ADDR_SIZE]), 'big')
    inode_block = bytearray(BLOCKSIZE)
    readBlock(curr_FS.disk, inode_bNum, inode_block)
    
    # Check to make sure file is NOT read-only (RO)
    perms = inode_get_data(inode_block, INODE_PERMS, INODE_SIZE_PERMS)
    if(perms == PERMS_RO):
        return ERR_INVALID_PERMS

    bNums = inode_get_blocks(inode_block)
    bNums.append(inode_bNum)

    # Add inode and data blocks back to freeblock bitmap
    for bNum in bNums:
        add_freeblock(curr_FS.disk, bNum, curr_FS.extra_blocks)
    # Remove inode entry
    inode_remove_entry(FD)
    return SUCCESS

def tfs_readByte(FD, buffer):
    # NOTE: Assumes buffer is passed as a char array of size 1
    # Make sure FS is actually mounted
    if(not mounted):
        return ERR_MOUNTED_NONE

    f = curr_FS.files[FD]
    # Grab inode
    inode_block = inode_get_block(FD)

    # Get size of file from inode
    size_bytes = inode_block[2:4]
    size = (size_bytes[0] << 8) | (size_bytes[1])

    if(f.offset >= size):
        return ERR_INVALID_OFFSET

    # Offset is valid, find which data block byte is in
    dbNums = inode_get_blocks(inode_block)
    dbNum = dbNums[int(f.offset / BLOCKSIZE)]
    dbOffset = int(f.offset % BLOCKSIZE)

    data_block = bytearray(BLOCKSIZE)
    readBlock(curr_FS.disk, dbNum, data_block)

    # Once you have data block, put byte into buffer & increment offset
    buffer[0] = data_block[dbOffset]
    f.offset += 1

    # Update inode block with new access time
    inode_bNum = inode_parse_entry(inode_get_entry(FD))[INODE_ENTRY_INDEX]
    inode_set_data(inode_block, INODE_ATIME, INODE_SIZE_TIME, int(time.time()))
    writeBlock(curr_FS.disk, inode_bNum, inode_block)

# change the file pointer location to offset (absolute). Returns success/error codes.
def tfs_seek(FD, offset):
    # Make sure FS is actually mounted
    if(not mounted):
        return ERR_MOUNTED_NONE
    f = curr_FS.files[FD]

    # Get size of file from inode
    inode_block = inode_get_block(FD)
    size_bytes = inode_block[2:4]
    size = (size_bytes[0] << 8) | (size_bytes[1])

    # Make sure you're not trying to seek past EOF
    if(offset >= size):
        return ERR_INVALID_SEEK

    f.offset = offset
    return SUCCESS

def create_superblock(disk, addr_size, nBlocks, freeBlocks):
    # Creates superblock and free blocks bitmap, and write them to memory
    # 0 byte = Magic Number, 1 byte = how many blocks needed for free block bitmap, next 4 bytes = root inode addr
    # Returns the number of extra blocks needed to create the free block bitmap
    superblock = [0x00] * BLOCKSIZE
    superblock[0] = MAGIC_NUMBER            # Add magic number at first byte

    # Add block number for root directory inode
    superblock[1] = ROOT_DIR_BLOCK

    # Create bitmap for free blocks
    bitmap_len = freeBlocks                 # How many freeblocks (bits) needed for bitmap
    bits_left = 8*(BLOCKSIZE-(2+addr_size)) # Bits left in superblock for bitmap    
    if(bitmap_len > bits_left):             # Check if more blocks needed for bitmap
        extra_blocks = int(ceil((bitmap_len-bits_left)/float(8*BLOCKSIZE)))
    else:
        extra_blocks = 0
    superblock[2] = extra_blocks            # Write number of extra blocks needed

    # Now write bitmap contiguously
    full_bytes = int(floor(bitmap_len / 8))
    leftover_bits = (bitmap_len % 8)
    leftover_byte = 0
    if(leftover_bits != 0):
        for i in range(leftover_bits):
            leftover_byte |= 1 << (7-i)

    if(extra_blocks == 0):                  # Simple solution
        for i in range(full_bytes):
            superblock[HEADER_BYTES+i] = 0xFF
        if(leftover_byte != 0):
            superblock[HEADER_BYTES+full_bytes] = leftover_byte
        writeBlock(disk, 0, superblock)     # Write superblock
    else:                                   # We're gonna need more blocks
        # Finish up superblock first
        ind = HEADER_BYTES
        while((full_bytes > 0) and (ind < BLOCKSIZE)):
            superblock[ind] = 0xFF
            full_bytes -= 1
            ind += 1
        writeBlock(disk, 0, superblock)

        # Write extra block(s) as necessary
        for i in range(extra_blocks):
            extra_block = [0x00] * BLOCKSIZE
            # Fill extra block
            ind = 0
            while((full_bytes > 0) and (ind < BLOCKSIZE)):
                extra_block[ind] = 0xFF
                full_bytes -= 1
                ind += 1
            if(ind < BLOCKSIZE):
                extra_block[ind] = leftover_byte
            # Write extra block
            writeBlock(disk, 1+i, extra_block)
    return extra_blocks
    
def fill_bytes(block, byts, numByts, offset):
    # Fills given block with numByts bytes starting at given offset
    for i in range(numByts):
        block[offset+i] = byts[i]

def find_freeblock(disk, extra_blocks):
    # Finds a freeblock in the bitmap and returns its logical block number
    # See if the bitmap has any available bits in superblock (bitmap != 0)
    block = bytearray(BLOCKSIZE)
    readBlock(disk, 0, block)
    superblock_bitmap = block[HEADER_BYTES:]

    found = -1
    for i in range(len(superblock_bitmap)):
        if(superblock_bitmap[i] > 0):           # Freeblock occurs in this byte
            found_byte = superblock_bitmap[i]
            found = i
            foundBlock = 0
            break
    
    # Check if freeblock was found
    if(found < 0):
        if(extra_blocks < 1):
            return ERR_NO_FREEBLOCKS
        
        # Check other bitmap block(s)
        for i in range(extra_blocks):
            readBlock(disk, 1+i, block)
            bitmap_block = bytearray(block)
            for j in range(len(bitmap_block)):
                if(bitmap_block[j] > 0):
                    found_byte = bitmap_block[j]
                    found = j
                    foundBlock = i
                    break
        
    if(found < 0):
        return ERR_NO_FREEBLOCKS
        
    # Find bit in byte for freeblock
    bitNum = -1
    for i in range(8):
        if((found_byte & (1 << (7-i))) > 0):
            bitNum = i
            break
    if(bitNum < 0):
        return ERR_NO_FREEBLOCKS

    # Freeblock found, find corresponding bNum
    if(foundBlock != 0):
        # Adjust first block to be first block of block with bitmap
        first_block = DATA_REGION_START + ((BLOCKSIZE - HEADER_BYTES)*8) + (BLOCKSIZE*8*foundBlock)
    else:
        first_block = DATA_REGION_START

    return first_block + (found*8) + bitNum

def remove_freeblock(disk, bNum, extra_blocks):
    # Given the block number, set corresponding bit in bitmap to 0
    bNum_adjusted = bNum - DATA_REGION_START     # First bit in bitmap = first FREE block
    byteNum = int(floor(bNum_adjusted / 8))
    bitNum = bNum_adjusted % 8

    # Find which bitmap block our old freeblock was on
    leftover_bytes = BLOCKSIZE-HEADER_BYTES     # How many bytes are left for bitmap in superblock
    if(byteNum >= leftover_bytes):              # freeblock is on one of the extra blocks
        bitmap_block = 1+int(floor((byteNum-leftover_bytes) / BLOCKSIZE))
    else:
        bitmap_block = 0
    
    # Read in block from disk
    diskBlock = bytearray(BLOCKSIZE)
    readBlock(disk, bitmap_block, diskBlock)

    # Alter block by setting bit from bitmap to 0
    diskBlock[HEADER_BYTES+byteNum] = diskBlock[HEADER_BYTES+byteNum] & ~(1 << (7-bitNum))

    # Write altered block back onto disk
    writeBlock(disk, bitmap_block, diskBlock)


def add_freeblock(disk, bNum, extra_blocks):
    # Given the block number, set corresponding bit in bitmap to 1
    bNum_adjusted = bNum - DATA_REGION_START     # First bit in bitmap = first FREE block
    byteNum = int(floor(bNum_adjusted / 8))
    bitNum = bNum_adjusted % 8

    # Find which bitmap block our old freeblock was on
    leftover_bytes = BLOCKSIZE-HEADER_BYTES     # How many bytes are left for bitmap in superblock
    if(byteNum >= leftover_bytes):              # freeblock is on one of the extra blocks
        bitmap_block = 1+int(floor((byteNum-leftover_bytes) / BLOCKSIZE))
    else:
        bitmap_block = 0
    
    # Read in block from disk
    diskBlock = bytearray(BLOCKSIZE)
    readBlock(disk, bitmap_block, diskBlock)

    # Alter block by setting bit from bitmap to 1
    diskBlock[HEADER_BYTES+byteNum] = diskBlock[HEADER_BYTES+byteNum] | (1 << (7-bitNum))

    # Write altered block back onto disk
    writeBlock(disk, bitmap_block, diskBlock)

def create_inode(mode, size, bNums):
    # Creates an inode block, containing:
    #   File type (mode), size (in bytes), blocks (allocated in memory), last access time, creation time
    #   Note: bNums is an array of 4-byte logical block numbers for the file's data blocks
    if(len(bNums) > MAX_DBLOCKS):
        return ERR_FILE_TOO_LARGE

    inode = bytearray(BLOCKSIZE)
    # Start with file type
    for i in range(2):
        inode[1-i] = (mode & (0xFF << (8*i))) >> (8*i)
    # Then size
    for i in range(2):
        inode[(1+2)-i] = (size & (0xFF << (8*i))) >> (8*i)
    # Number of blocks allocated
    for i in range(2):
        inode[(1+4+2)-i] = (len(bNums) & (0xFF << (8*i))) >> (8*i)
    # Now creation, access, and modify times, which will start out all the same
    times = int(time.time())
    for i in range(3):
        for j in range(4):
            inode[(1+4+2+4+(4*i))-j] = (times & (0xFF << (8*j))) >> (8*j)
    
    # That takes up all the metadata, now for the data block locations
    # In the form of a list of blocks
    for i in range(len(bNums)):
        for j in range(4):
            inode[INODE_METADATA+(i*4)+3-j] = (bNums[i] & (0xFF << (8*j))) >> (8*j)
    return inode

def convert_time(epoch_time):
    # Converts time since epoch to calendar data + clock time
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch_time))

def get_offset(FD):
    # Helper function for tinyFSDemo
    global curr_FS
    return curr_FS.files[FD].offset



def main():
    print("Wrong place! Run Demo using './tinyFsDemo.py'")

if __name__ == '__main__':
    main()