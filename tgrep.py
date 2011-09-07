#!/usr/bin/python

 
# http://www.reddit.com/r/blog/comments/fjgit
#
# Attack: Use bisection to narrow down the start and stop dates.
# Time is stored in a simple array for easy comparison.
#
# Addendum: Fairly fast, 72GB file would only take log2(72G) == ~36.17
# attempts to find any particular line.

import sys
import time
import os


days = {}           # Eg {'Feb  9':0, 'Feb 10':1}


def find_last_line(infile, sizef, search_time):
    # Return the location of the last line with a time <= search_time.

    # Bisect the file until we find the last line just before a line
    # with a time > search_time.
    lower, upper = 0, sizef
    line_a, line_b = 0, 0
    
    found = False
    while not found and lower < sizef and upper > 0:
        last_line_a, last_line_b = line_a, line_b
        midpoint = (upper-lower)/2 + lower
        infile.seek(midpoint)
        (line_a, line_b), line = read_current_line(infile)
        if (line_a, line_b) == (last_line_a, last_line_b):
            found = True
            break
        t = parsetime(line)
        if search_time < t:
            upper = line_a - 1
        else:
            lower = line_b + 1
    return line_a


def find_first_line(infile, sizef, search_time):
    # Return the location of the first line with a time >= search_time.

    # Search by looking for the last line just earlier
    # than the one we are interested in.
    just_before = search_time[:]
    just_before[-1] -= 1            # make just_before < search_time == true
    k = find_last_line(infile, sizef, just_before)
    if k == 0:
        infile.seek(0)
        if parsetime(infile.readline()) > search_time:
            return 0  # search_time is earlier than the 
                      # earliest time in the file ==> return start of file
    infile.seek(k)
    infile.readline()
    return infile.tell()


def readline_prev(infile):
    # Like file.readline() but in reverse. Read from the current file position
    # backwards until we get to the previous newline.
    x,k = '',''
    while x.rfind('\n', 0, -1) == -1 and infile.tell() != 0:
        rd = min(infile.tell(), 1024)
        infile.seek(-rd, 1)
        x = infile.read(rd)
        k = x[x.rfind('\n', 0, -1)+1:] + k
        infile.seek(-len(x)+x.rfind('\n', 0, -1)+1, 1)
    return k


def read_current_line(infile):
    # Return the ((start, end), string) of the current line of 'infile'.
    # ==> ((143L, 175L), 'Feb  9 07:09:15 ---- ---- ---- \n')
    readline_prev(infile)   # Seek to start of current line
    start = infile.tell()
    line = infile.readline()
    return ((start, infile.tell()-1), line)


def parsetime(line):
    # Return an array form of the log dates suitable for < > comparisons.
    # 'Feb  9 07:09:15 blah blah blah \n' ==> [0, 7, 9, 15]
    return [days[tuple(line.split()[:2])]] + map(int,line.split()[2].split(':'))



def main(argv):

    if len(argv) != 3:
        print ('Print entries from a (large) log file that\n'
        'fall within the given time range.\n'
        '\n'
        'Usage:\n'
        'tgrep.py <time range> [logfile]\n'
        '\n'
        'Valid time ranges forms are:\n'
        '  23:59-0:03         Searches 23:59:00 - 00:03:99\n'
        '  8:42:04            Searches only 08:42:04\n'
        '  10:01              Searches 10:01:00 - 10:01:59\n'
        '\n'
        'Log file lines must be in the form:\n'
        '  "Feb  9 08:42:47 Lorem ipsum dolor sit amet"\n'
        )
        sys.exit()


    if '-' in argv[1]:                    # 23:59-0:03
        tstart  = map(int, argv[1].split('-')[0].split(':')) + [0]
        tfinish = map(int, argv[1].split('-')[1].split(':')) + [59]
    elif len(argv[1].split(':')) == 3:    # 8:42:04
        tstart  = map(int, argv[1].split(':'))
        tfinish = start[:]
    elif len(argv[1].split(':')) == 2:    # 10:01
        tstart  = map(int, argv[1].split(':')) + [0]
        tfinish = start[:2] + [59]
    else:
        print 'Error: Bad <time range> format.'
        sys.exit()
    infile = open(argv[2])
    sizef = os.path.getsize(argv[2])


    # Quick sanity test of input file
    firstline = infile.readline()
    infile.seek(0, 2)
    lastline = readline_prev(infile)
    try:
        time.strptime(firstline[:15], '%b %d %H:%M:%S')
        time.strptime(lastline[:15], '%b %d %H:%M:%S')
    except:
        print 'Error: Unable to parse log data, invalid date formats:', 
        print repr(firstline[:15]), repr(lastline[:15])
        sys.exit(0)

    days[tuple(firstline.split()[:2])] = 0
    days[tuple(lastline.split()[:2])] = 1


    # Perform the search, for all 3 cases where:
    # - Both times are on the first day
    # - Both times are on the second day
    # - tstart is on the first day, tfinish is on the second
    ranges = [([0]+tstart, [0]+tfinish), ([1]+tstart, [1]+tfinish)]
    if tstart > tfinish: 
        ranges += [([0]+tstart, [1]+tfinish)]

    for t1,t2 in ranges:
        lower = find_first_line(infile, sizef, t1)
        upper = find_last_line(infile, sizef, t2)
        infile.seek(lower)
        # Write out in 4k block chunks
        while lower < upper:
            to_read = min(4096, upper-lower)
            sys.stdout.write(infile.read(to_read))
            lower += to_read
    return


if __name__ == '__main__':
    import sys
    main(sys.argv)
