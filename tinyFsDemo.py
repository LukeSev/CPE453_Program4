#!/usr/bin/env python3
from libTinyFS import *

def test_FS():
    # Print some formatting/intro stuff
    print("-----------------------------------------------")
    print("#####       Basic FS Demo Description     #####")
    print("-----------------------------------------------")
    print("\nIn this demo, a File System will be created and mounted, and then two different files will be opened/written into the file systems.")
    print("Some general notes about the demo before we begin:")
    print("   -  At various times errors will deliberately be caused to demonstrate proper error handling.")
    print("      -  When this occurs, error codes will generally be printed to reflect this behavior.")
    print("      -  The error will then often be corrected, and a successful return code will be printed to reflect this.")
    print("   -  The demo will be broken up into sections that I've tried my best to separate with headings/comments. There are two main over-arching sections with some subsections within each")
    print("       -  The first over-arching section runs through the basic functionality that was described/required for the assignment, such as:")
    print("           -  making and mounting the file system")
    print("           -  opening and writing files")
    print("           -  closing and deleting files")
    print("           -  reading from files")
    print("       -  The second over-arching section covers the two bonus areas of functionality that I added, which specifically were:")
    print("           -  timestamps/stat support (collect and/or print all relevant tracked data for a file)")
    print("           -  Read-only and writeByte support")
    print("   -  Print statements will accompany just about every operation that occurs throughout the demo.")
    print("       -  While I will be writing about my various design choices and added functionality in the README, I obviously still wanted to make the results of the demo easily readable/verifiable")
    print("       -  I start to get a little verbose towards the end when covering my added functionality, but I feel that was appropriate due to it being a little more open-ended (although the entire project is somewhat open-ended)")

    print("\n\n####################################")
    print("##      B E G I N   D E M O       ##")
    print("####################################")


    file1 = "hello"
    file2 = "goodbye"
    print("\nThe program will begin by mounting a filesystem and opening/writing two files, which will be referred to as (in the order that they appear):")
    print("\t{}\n\t{}".format(file1, file2))
    print("The filesystem will be called 'testFS'")

    print("The files were already written prior to the running of this demo using libDisk to avoid using anything but tfs functions in the demo itself.")
    print("The format of the files are outlined below as they are opened/written into the FS, but they notably",
    "contain patterns that change from block to block to make reading from/writing to different blocks easily differentiatable")


    print("\n\n------------------------------")
    print("-----  BEGIN BASIC TEST  -----")
    print("------------------------------")

    # Create FS for testing, make it magnitudes larger than default
    fs_name = "testFS"
    tfs_mkfs(fs_name, 10*DEFAULT_DISK_SIZE)
    results = tfs_mount(fs_name)
    if(results == SUCCESS):
        print("\nSuccessfully created and mounted FS: '{}'\n".format(fs_name))

    # Open the first file and read some bytes
    fd_hello = tfs_open(file1)
    f1 = open("disk1", 'r+b')
    buffer = f1.read()
    tfs_write(fd_hello, buffer, len(buffer))
    print("")

    tfs_seek(fd_hello, BLOCKSIZE)           # Should point to 0xde, the first byte of the second block
    buff = [0]
    print("Attempting to print 4 bytes from file '{}' starting at second block".format(file1))
    print("--- Expected results --- \n",
        "Second block is full of 'deadbeef' in hex repeated throughout\n",
        "Since we're starting at the second block, the first 4 bytes should simply be 'deadbeef'")
    for i in range(4):                      # Should print out "deadbeef", the first four bytes of second block
        tfs_readByte(fd_hello, buff)    
        print(format(buff[0], '#x'))

    # Open another file and read some bytes
    fd_goodbye = tfs_open(file2)
    f2 = open("testDisk", 'r+b')
    buffer = f2.read()
    tfs_write(fd_goodbye, buffer, len(buffer))
    tfs_seek(fd_goodbye, BLOCKSIZE-2)       # This one crosses block lines, starting 2 bytes before start of second block
    print("\nAttempting to print 4 bytes from file '{}' starting 2 bytes before the second block".format(file2))
    print("--- Expected results --- \n",
        "First block is all 0x00, second block is all 0xFF\n",
        "Since we're starting 2 bytes before the second block, the 4 printed bytes should be 0000FFFF")
    for i in range(4):                      # Should print out "0000FFFF", since first block is all 0x00's, second all 0xFF's
        tfs_readByte(fd_goodbye, buff)      
        print(format(buff[0], '#x'))

    # Unmount FS and make sure it doesn't let you do anything
    results = tfs_unmount()
    if(results == SUCCESS):
        print("\n\nSuccessfully unmounted FS: '{}'\n".format(fs_name))
    print("\nCurrently Mounted FS: {}".format(curr_FS))           # Should be none
    print("Value for 'mounted' boolean: {}".format(mounted))    # Should be false

    print("\nAn attempt will now be made to open a file while the FS isn't mounted. This should fail.")
    print("\n --- Return value from trying to open file with no mounted FS --- \n", 
        "Return Values: 0 for Success, -9 for expected Error (ERR_MOUNTED_NONE)\n",
        "Results: {}\n".format(tfs_open("hey_hey")))

    input("Before re-mounting the FS and continuing, you can stop and inspect the FS if desired. Just press enter to continue.")

    # Re-mount FS
    tfs_mount("testFS")
    
    print("FS Re-mounted, read some more bytes from '{}'".format(file1))

    # Read some more bytes from the first open file
    for i in range(4):                      # Should print out "deadbeef" again
        tfs_readByte(fd_hello, buff)    
        print(format(buff[0], '#x'))

    print("Now delete '{}' and try to read from it again".format(file1))
    # Now delete file and try to read again
    tfs_delete(fd_hello)
    results = tfs_readByte(fd_hello, buff)
    print("\n --- Results of trying to read from deleted file ---\n",
        "Return Values: 0 for Success, -15 for expected Error (ERR_INVALID_READ)\n",
        "Results: {}\n".format(results))


    print("\n------------------------------")
    print("-----  BEGIN STAT TEST   -----")
    print("------------------------------\n")

    print("One of the added functionalities will now be tested: Timestamps and the tfs_stat call")
    print("To do this, first the file that was just deleted will be recreated ({})".format(file1))
    print("An artificial delay of {}s will be added before each operation since the time precision only goes down to the second, and no delay would lead to equal creation/access/modification times.".format(T_DELAY))
    print("4 bytes will then be read from the file (and printed to the screen), with a {}s delay between each read.".format(T_DELAY))
    print("This should lead to a difference of {}s between creation and modification time, and a difference of {}/{} between access time and creation/modification times, respectively".format(T_DELAY, 5*T_DELAY, 4*T_DELAY))
    print("This will further be compared to the timestamps of the second file, which was never deleted and which was created/opened/written without any delays")
    print("To print the relevant info, a Stat() struct will be created with the tfs_stat() call and then printed with Stat.print_info()")
    print("On a side note, this will incidentally demonstrate that opening the file initialized the offset to 0, since in both other cases seek was used before any reads occurred")
    delay()
    fd_hello = tfs_open(file1)
    print("FILE OPENED AT DATE/TIME {}".format(convert_time(int(time.time()))))
    # Note: We still have to seek in the actual/original file since that isn't affected by the simulated FS
    f1.seek(0)
    buffer = f1.read()
    delay()
    tfs_write(fd_hello, buffer, len(buffer))
    print("FILE WRITTEN AT DATE/TIME {}".format(convert_time(int(time.time()))))
    for i in range(4):
        delay()
        tfs_readByte(fd_hello, buff)
        print("Read byte 0x{:x} at offset {}".format(buff[0], get_offset(fd_hello)-1))

    print("\nAll modifications are complete! Time to print the actual stat data, starting with the newly re-created file: {}".format(file1))
    file1_stat = tfs_stat(fd_hello)
    file1_stat.print_info()
    print("\nNow for the other file (as mentioned above), to be used as a control:")
    file2_stat = tfs_stat(fd_goodbye)
    file2_stat.print_info()


    print("\n------------------------------")
    print("-----  BEGIN WRITE TEST  -----")
    print("------------------------------\n")

    print("The second added functionality will now be tested: Read-only and writeByte support")
    print("To do this, some operations will be performed on the second file ({}):")
    print("   -  First, 4 bytes will be written at four different offsets (one byte at each offset)")
    print("      (As a reminder, the second file consists of datablock 0 being all 0x00's and datablock 1 being all 0xFF's)")
    print("      -  '0xba' will be written at the midpoint of the first block (offset = BLOCKSIZE / 2)")
    print("      -  '0xdd' will be written at the end of the first block (offset = BLOCKSIZE - 1)")
    print("      -  '0xc0' will be written at the beginning of the second block (offset = BLOCKSIZE)")
    print("      -  '0xde' will be written at the midpoint of the second block (offset = BLOCKSIZE+(BLOCKSIZE / 2))")
    print("   -  To confirm these writes, 3 consecutive reads will occur around each write (the written byte and two surrounding bytes)")
    print("      - Further, a delay will be added between each write and a call to stat/print_info will occur to show the change in modification/access times")
    print("   -  Once this has been confirmed, the file will be made Read-Only (RO)")
    print("   -  An attempt will then be made to write-over the first byte that was written")
    print("      - Specifically, an attempt will be made to write '0xff' at offset = BLOCKSIZE / 2")
    print("   -  To confirm that the write was unsuccessful, the return code from the write function will be printed")
    print("      - To further confirm the outcome of the write, 3 consecutive reads will be made around the byte in question, as was done previously")
    print("   -  The file will then be made Read/Write (RW) and the attempt to perform the write will be repeated")
    print("   -  The results will be printed in the same format as they were previously")
    delay()
    print("Writing 0xba...")
    tfs_writeByte(fd_goodbye, int(BLOCKSIZE / 2), 0xba)
    delay()
    print("Write complete! Performing stat call:")
    file2_stat = tfs_stat(fd_goodbye)
    file2_stat.print_info()
    delay()
    print("Writing 0xdd...")
    tfs_writeByte(fd_goodbye, BLOCKSIZE - 1, 0xdd)
    delay()
    print("Write complete! Performing stat call:")
    file2_stat = tfs_stat(fd_goodbye)
    file2_stat.print_info()
    delay()
    print("Writing 0xc0...")
    tfs_writeByte(fd_goodbye, BLOCKSIZE, 0xc0)
    delay()
    print("Write complete! Performing stat call:")
    file2_stat = tfs_stat(fd_goodbye)
    file2_stat.print_info()
    delay()
    print("Writing 0xde...")
    tfs_writeByte(fd_goodbye, BLOCKSIZE + int(BLOCKSIZE / 2), 0xde)
    delay()
    print("Write complete! Performing stat call:")
    file2_stat = tfs_stat(fd_goodbye)
    file2_stat.print_info()
    delay()
 
    print("\nAll the writes have been completed, now to confirm them with consecutive reads:\n")
    delay()
    read_tests = [
        ("the midpoint of the first block:", int(BLOCKSIZE / 2) - 1),
        ("the last byte of the first block", BLOCKSIZE - 2),
        ("the first byte of the second block", BLOCKSIZE - 1),
        ("the midpoint of the second block", BLOCKSIZE + int(BLOCKSIZE / 2) - 1)
    ]
    for i in range(4):
        print("Making three consecutive reads starting before {}".format(read_tests[i][0]))
        tfs_seek(fd_goodbye, read_tests[i][1])
        delay()
        for j in range(3):
            tfs_readByte(fd_goodbye, buff)
            print("0x{:x}".format(buff[0]))
        print()
        delay()

    print("\nAll the reads have been completed, the file will now be made Read-Only and stat() will be called to confirm as such")
    tfs_makeRO(file2)
    delay()
    file2_stat = tfs_stat(fd_goodbye)
    file2_stat.print_info()
    delay()

    print("An attempt will now be made to overwrite the first written byte with '0xff' (replacing '0xba' at offset = BLOCKSIZE / 2)")
    results = tfs_writeByte(fd_goodbye, int(BLOCKSIZE / 2), 0xff)
    print("The return value will now be printed. A return value of 0 indicates success, < 0 indicates error (specifically, -19 corresponds to ERR_INVALID_PERMS):")
    delay()
    print("Return Value: {}".format(results))
    delay()
    print("To further confirm that the write failed, the 3 consecutive reads will be performed as before, starting at offset = (BLOCKSIZE / 2) - 1")
    delay()
    tfs_seek(fd_goodbye, int(BLOCKSIZE / 2) - 1)
    for j in range(3):
        tfs_readByte(fd_goodbye, buff)
        print("0x{:x}".format(buff[0]))

    print("\nThe file will now be made Read/Write and stat() will be called to confirm as such")
    tfs_makeRW(file2)
    delay()
    file2_stat = tfs_stat(fd_goodbye)
    file2_stat.print_info()
    delay()
    print("An attempt will now be made to perform the write that previously failed.")
    print("An attempt will then be made to confirm this write with 3 consecutive reads, as done previously.")
    results = tfs_writeByte(fd_goodbye, int(BLOCKSIZE / 2), 0xff)
    print("The return value will once again be printed:")
    delay()
    print("Return Value: {}".format(results))
    delay()

    print("\nAn attempt will now be made to repeat the first series of 3 consecutive reads, starting at offset = (BLOCKSIZE / 2) - 1")
    delay()
    tfs_seek(fd_goodbye, int(BLOCKSIZE / 2) - 1)
    for j in range(3):
        tfs_readByte(fd_goodbye, buff)
        print("0x{:x}".format(buff[0]))
    delay()



    print("\n####################################")
    print("##        E N D   D E M O        ##")
    print("####################################")

# Adds a 1 second delay. 
# Mostly used to create multi-second differences in file timestamps, 
#   but also added throughout to give the user a sense of timely progression
# Clarification: Scratch that, timed delays will only begin once stat begins being used to look at timestamps
#   Adding artificial delays to make the demo more readable in real-time might be nice from a viewing perspective,
#   but it detracts from the viewer's ability to assess how quickly the program runs/performs.
def delay():
    time.sleep(1)

def big_delay(seconds):
    for i in range(seconds):
        delay()

def main():
    test_FS()
    return

if __name__ == '__main__':
    main()