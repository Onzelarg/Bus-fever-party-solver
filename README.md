# Level solver script for the mobile game Bus fever party written in python.

I got stuck at level 26, like others in this reddit post:
https://www.reddit.com/r/MobileGaming/comments/1wv6c41/bus_fever_party/

So I made this solver script to find a solution. Spoiler alert: there is none with the free 4 parking spaces configuration.  For comparison a chain with 12 cars and 5 parking spots has 45897997 possible combinations.

# Usage
From command line use python on windows or python3 on linux/mac:
```
python3 cargame.py
```

## Flags
| Flag  | Description |
| ---------------- |:-------------:|
| -h, --help      | show this help message and exit     |
| -d, --depth      | Sets the depth that the chain is going to be explored. WARNING: raising the depth makes the execution to be exponencially longer!    |
| -c, --config      | Sets the config file to be loaded, instead of the default cars.json     |
|-s, --single|Run the solver as a single process. WARNING: can take a long time depending on the level of depth!|
|-m, --maxcore|Set the maximum amount of cores that can be used for solving.|
|-t, --total|Overwrite the total parking spaces.|

# Examples
```
>>> python3 cargame.py -d 6 -t 4
    Cars dict set with length 36. Start colors set with amount of 140. 
    New comers set with length 10. Total parking space is 4. Cpu count is 20
    Roots (8): [1, 8, 9, 18, 19, 20, 31, 36]
    Using 8 workers for 8 tasks
    Total viable count at 4 spaces: 3621
    Total chains found with id 0 is 2584
    Total chains found with id 13 is 2252
    Total chains found with id 4 is 2071
    Total chains found with id 14 is 2561
    Total chains found with id 11 is 2015
    Total chains found with id 15 is 2269
    Total chains found with id 10 is 2296
    Total chains found with id 18 is 2179
    Total chains found with id 2 is 2042
    Total chains found with id 12 is 2224
    Total chains found with id 6 is 2199
    Total chains found with id 8 is 2449
    Total chains found with id 7 is 2323
    Total chains found with id 9 is 2306
    Total chains found with id 3 is 2277
    Total chains found with id 16 is 2286
    Total chains found with id 5 is 2351
    Total chains found with id 17 is 2529
    Total chains found with id 1 is 2402
    Total chains found with id 19 is 2259
    Total chain count 45874
    Total time: 1.54s

```
```
python cargame.py                # multiprocess solve using cars.json
python cargame.py -d 12          # explore deeper (much slower!)
python cargame.py -c other.json  # different level file
python cargame.py -s             # single-core mode (writes chains_X_Y_single.txt)
python cargame.py -m 4 -t 6      # limit to 4 cores, override parking to 6 spaces
```
Example chain from a 11 depth 4 parking spaces simulation:
```
Chain 148796: [[36, 1, 2, 3, 20, 13, 19, 18, 4, 9, 30], 236, 3]

```
This particular chain has picked up 236 passengers and occupying 3 parking spaces. 
The order of the chain is the same as you would pick from the game.
# How does it work

The rule of the game (in case you have not played it): you release cars one at a time. A released car picks up waiting passengers of its own color up to it's capacity. If a car's capacity if exhausted, it leaves the parking space, freeing it up. If no matching passengers are waiting, it just sits in a parking slot. If all parking slots fill up with cars that can't load, you lose.

The script tries huge numbers of possible move orders and saves the ones that don't lead to a dead end.

First it loads the level's configuration from cars.json:

- cars - each car has a color, a passenger capacity, and a blockedById list (which other cars must leave before this one can move). For example car 3 can only go after cars 1 and 2 have gone.  
- startColors - the passengers currently waiting, grouped by color.
- newComers - the queue of passengers who will arrive later, in order.
- totalSpace - how many parking/waiting slots exist for cars that have left the jam but can't load yet.

### main() - splitting the work across CPU cores
Because the number of orderings explodes exponentially, the default mode parallelizes in two phases:  
Find the "root" cars (nothing blocks them) and, using one worker per root, enumerate all viable short chains up to totalSpace length.  
Shuffle those viable starting chains, split them into one batch per CPU core (or maximum allowed), and have each worker extend its batch to the full depth, again pruning dead ends with checkVial.  
All surviving chains are written to a file like chains_9_5.txt (depth 9, 5 spaces), each line showing the car order plus its stats.

### checkVial(...) - is this chain still winnable?
This simulates playing a given sequence of cars:  
Each car in the chain grabs as many same-colored waiting passengers as it can. If it fills up completely, it leaves (freeing its slot).  
When waiting passengers run out, new ones arrive from the newComers queue, and the simulation repeats recursively.  
It returns False (dead end) if the parking lot is full of cars and nobody can board. Otherwise it returns True along with stats: how many passengers were picked up, how many cars are still parked, and how many future passengers remain.

### dfs(...) - trying every legal order
A depth-first search builds chains of car IDs one at a time. A car may be appended only if it isn't already used and everything in its blockedById list has already gone. Once a chain gets long enough, checkVial is called on it to prune non-viable chains. The search doesn't waste time extending hopeless branches. Chains that reach the target depth (--depth, default 9) are recorded as survivors.
### Data structure
The data is created from a screenshot:
<img width="1179" height="2556" alt="level26" src="https://github.com/user-attachments/assets/14689a0b-5bee-40ee-b83e-0c2d9d9c7289" />
```
    "totalSpace" : 5,
    "cars" : [ 
        {
        ...
        "32": {"blockedById": [1, 2, 3, 4, 12, 13, 14, 16, 26, 29, 30, 33, 34, 35, 36], "color": "Purple",     "capacity": 16, "blockedByCount": 15},
        "33": {"blockedById": [34, 35, 36                                            ], "color": "Red",        "capacity": 40, "blockedByCount": 3},
        "34": {"blockedById": [29, 30, 36                                            ], "color": "Orange",     "capacity": 24, "blockedByCount": 3},
        "35": {"blockedById": [36                                                    ], "color": "Blue",       "capacity": 24, "blockedByCount": 1},
        "36": {"blockedById": [                                                      ], "color": "Cyan",       "capacity": 24, "blockedByCount": 0}
        }
    ],
    
    "startColors" : {
        "Blue"   : 16,
        "Yellow" : 24,
        "Red"    : 48,
        "Green"  : 52
    },
    
    "newComers" : [
        {"amount" : 24, "color" : "Blue"},
        {"amount" : 52, "color" : "Green"},
        {"amount" : 12, "color" : "Red"},
        ...
    ]
```
totalSpace is the amount of parking spaces.







blockedById is the ids of other cars that blocks this one. For example car 35 is blocked by 36, so it can only go after 36. 32 is blocked by half of the field. blockedByCount is the amount that each car is blocked. A car can only be picked if it is 0.
starColors is the starting pool that is not queued.
newComers is the passengers that are queuing on the left side.
