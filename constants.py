# Disk-specific constants
BLOCKSIZE           =   256     # Block size statically defined as 256 bytes
DEFAULT_DISK_SIZE   =   10240   # Default size of a disk if no other size specified

# tinyFS-specific constants
DEFAULT_DISK_NAME   =   "tinyFSDisk"
MAGIC_NUMBER        =   0x5A
NAME_SIZE           =   8       # Name is 8 chars/bytes in length
ADDR_SIZE           =   4
ROOT_DIR_BLOCK      =   3       # See tinyFS.py for details on FS block layout
HEADER_BYTES        =   3       # ^^^ Number of header bytes in superblock
BITMAP_BLOCKS       =   2       # ^^^ Number of extra blocks for freeblock bitmap
INODE_TABLE_SIZE    =   5       # ^^^ Number of blocks for Inode Table size
DATA_REGION_START   =   8       # ^^^
MAX_DBLOCKS         =   59      # Max number of data blocks for a file, dictated by INode's space for data block list
INODE_METADATA      =   20      # Number of bytes needed for file metadata, before block location list
                                #   2 bytes for file type, 
                                #   4 for size, 
                                #   2 for blocks allocated
                                #   12 (4 each) for access, creation, and modification times,
MAX_FILESIZE        =   59 * BLOCKSIZE
INODE_ENTRY_SIZE    =   12      # 4 bytes for block number, 8 for name
INODE_SIZE_TIME     =   4       # Number of bytes used to store time
INODE_SIZE_TYPE     =   1
INODE_SIZE_PERMS    =   1
INODE_SIZE_FILESIZE =   2
INODE_SIZE_NBLOCKS  =   4

# File types/modes
MODE_SB     =   0
MODE_DIR    =   1
MODE_DATA   =   2

# File perms
PERMS_RW    =   0
PERMS_RO    =   1

# Error Codes
SUCCESS             =   0
ERR_DSKSIZE         =   -1
ERR_OPEN            =   -2
ERR_CREAT           =   -3
ERR_CLOSED          =   -4
ERR_INVALID_DISK    =   -5
ERR_INVALID_BNUM    =   -6
ERR_FAILED_CREAT    =   -7
ERR_MOUNTED_FS      =   -8
ERR_MOUNTED_NONE    =   -9
ERR_INVALID_FD      =   -10
ERR_NO_FREEBLOCKS   =   -11
ERR_FILE_SIZE       =   -12
ERR_INVALID_FS      =   -13
ERR_INVALID_SEEK    =   -14
ERR_INVALID_OFFSET  =   -15
ERR_FILE_TOO_LARGE  =   -16
ERR_NO_FD           =   -17
ERR_FILE_NOT_FOUND  =   -18
ERR_INVALID_PERMS   =   -19

# Indexing into inode block (array of bytes)
INODE_PERMS         =   0
INODE_TYPE          =   1
INODE_FILESIZE      =   2
INODE_NBLOCKS       =   4
INODE_CTIME         =   8
INODE_ATIME         =   12
INODE_MTIME         =   16

# Indexing into inode_entry (name, index)
INODE_ENTRY_NAME    =   0
INODE_ENTRY_INDEX   =   1

# Other constants
CLOSED      =   0
OPEN        =   1
T_DELAY     =   1