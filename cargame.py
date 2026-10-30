from time import perf_counter
import copy, json, os, random, argparse, multiprocessing as mp

dfsChain = []
cars = {}
startColors = {}
newComers = []
totalSpaceOverride = -1
totalSpace = 0
cpuCount = 1
GLOBAL_maxDepth = 9
saveResult = True
defaultConfigFile = "cars.json"
maxCoreCount = -1

def printPerf(startPerf, msg = ""):
    end = perf_counter()
    print(f"{msg}{end - startPerf}")
    return perf_counter()

def getConfig():
    global cars, startColors, newComers, totalSpace, cpuCount, defaultConfigFile

    with open(defaultConfigFile, "r") as file:
        carsJson = json.loads(file.read())

    localCars = carsJson["cars"]
    cars = {int(k): v for k, v in localCars[0].items()}
    if len(cars) < GLOBAL_maxDepth:
        GLOBAL_maxDepth = len(cars)
    startColors = carsJson["startColors"]
    newComers = carsJson["newComers"]
    if totalSpaceOverride > 0:
        totalSpace = totalSpaceOverride
    else:
        totalSpace = carsJson["totalSpace"]
    if maxCoreCount > 0:
        cpuCount = maxCoreCount
    else:
        cpuCount = os.cpu_count()
    print(f"Cars dict set with length {len(cars)}. Start colors set with amount of {sum(startColors.values())}. New comers set with length {len(newComers)}. Total parking space is {totalSpace}. Cpu count is {cpuCount}")



def checkVial(chain, chainLength, carsCopy = None, passengers = None, nextPass = None, maxPassengersOut = 140, passengersTaken = 0):
    if carsCopy   is None: carsCopy   = copy.deepcopy(cars)
    if passengers is None: passengers = copy.deepcopy(startColors)
    if nextPass   is None: nextPass   = copy.deepcopy(newComers)
    passengersWaiting = maxPassengersOut
    loops = min(totalSpace, len(chain))
    toDelete = []
    
    for i in range(0, loops):
        for color, amount in passengers.items():
            if carsCopy[chain[i]]["color"] == color:
                if amount == 0:
                    break
                if carsCopy[chain[i]]["capacity"] <= amount:
                    passengersWaiting -= carsCopy[chain[i]]["capacity"]
                    passengers[color] -= carsCopy[chain[i]]["capacity"]
                    passengersTaken += carsCopy[chain[i]]["capacity"]
                    toDelete.append(i)
                else:
                    passengersWaiting -= amount
                    passengersTaken += amount
                    carsCopy[chain[i]]["capacity"] -= amount
                    passengers[color] = 0
                break

    for i in range(loops -1, -1, -1):
        if i in toDelete:
            chain.pop(i)

    remaningNextPass = 0
    for np in nextPass:
        remaningNextPass += np["amount"]
    
    if len(chain) == 0:
        return True, passengersTaken, 0, remaningNextPass

    #   Worst case: We did not pick up anyone and filled all avaiable slots
    if passengersWaiting == maxPassengersOut and len(chain) >= totalSpace:
        return False, passengersTaken, len(chain), remaningNextPass

    if passengersWaiting == maxPassengersOut and len(chain) < totalSpace:
        # if chainLength >= 7 and passengersTaken < 100:
        #     return False, 0, len(chain)
        # if chainLength >= 9 and passengersTaken < 200:
        #     return False, 0, len(chain)
        return True, passengersTaken, len(chain), remaningNextPass 

    while passengersWaiting != maxPassengersOut and nextPass:
        if nextPass[0]["color"] in passengers:
            passengers[nextPass[0]["color"]] += 1
        else:
            passengers.update({nextPass[0]["color"] : 1})
        nextPass[0]["amount"] -=1
        if nextPass[0]["amount"] == 0:
            nextPass.pop(0)
        passengersWaiting += 1

    return checkVial(chain, chainLength, carsCopy, passengers, nextPass, sum(passengers.values()), passengersTaken)


def dfsSingleCore(maxDepth):
    getConfig()
    startperf = perf_counter()

    def dfs(chain, maxDepth):
        if len(chain) >= 4: 
            viable, totalTaken, parked, remaningNextPass = checkVial(chain.copy(), len(chain))
            if not viable:
                return
        if len(chain) == maxDepth:
            dfsChain.append([chain.copy(), totalTaken, parked, remaningNextPass])
            return

        taken = set(chain)
        for cid, car in cars.items():
            if cid not in taken and all(b in taken for b in car["blockedById"]):
                chain.append(cid)
                dfs(chain, maxDepth)
                chain.pop()

    dfs([], maxDepth)
    if saveResult:
        chainCounter = 0
        with open(f"chains_{maxDepth}_{totalSpace}_single.txt", "w") as file:
            file.write("New run\n")
            for chain in dfsChain:
                chainCounter += 1
                file.write(f"Chain {chainCounter}: {chain}\n")
    print(f"Total chain count {chainCounter}")
    print(f"Total time: {perf_counter() - startperf:.2f}s")


        
def dfsMultiprocess(seed_chain, maxDepth):
    local_chains = []

    def dfsSingle(chain, maxDepth):
        if len(chain) >= totalSpace:
            viable, totalTaken, parked, remaningNextPass = checkVial(chain.copy(), len(chain))
            if not viable:
                return
        if len(chain) == maxDepth:
            local_chains.append([chain.copy(), totalTaken, parked, remaningNextPass])
            return

        taken = set(chain)
        for cid, car in cars.items():
            if cid not in taken and all(b in taken for b in car["blockedById"]):
                chain.append(cid)
                dfsSingle(chain, maxDepth)
                chain.pop()

    dfsSingle(list(seed_chain), maxDepth)
    return local_chains


def getViableChains(args):
    seed, spaces = args
    return dfsMultiprocess(seed, spaces)

def exploreChains(args):
    chains, maxDepth, id = args
    localExploreChain = []
    for chain in chains:
        localExploreChain.extend(dfsMultiprocess(chain, maxDepth))
    print(f"Total chains found with id {id} is {len(localExploreChain)}")
    return localExploreChain


def main():
    getConfig()
    startperf = perf_counter()
    maxDepth = 12

    roots = [cid for cid, car in cars.items() if car["blockedById"] == []]
    print(f"Roots ({len(roots)}): {roots}")

    tasks = [([r], totalSpace) for r in roots]

    ctx = mp.get_context("fork") if os.name != "nt" else mp.get_context("spawn")
    workerCount = min(len(tasks), os.cpu_count() or 1)
    print(f"Using {workerCount} workers for {len(tasks)} tasks")

    chainCounter = 0

    tempviableStartChains = []

    with ctx.Pool(processes = workerCount) as pool:
        for result in pool.imap_unordered(getViableChains, tasks, chunksize=1):
            for c in result:
                tempviableStartChains.append(c[0])
                chainCounter += 1

    print(f"Total viable count at {totalSpace} spaces: {chainCounter}")

    viableStartChains = []
    chunks = chainCounter // cpuCount
    remain = chainCounter % cpuCount
    chainCounter = 0
    random.shuffle(tempviableStartChains)
    for i in range(0, cpuCount):
        viableStartChains.append(tempviableStartChains[i * chunks : (i + 1) * chunks])
    viableStartChains[-1] = [*viableStartChains[-1] ,*tempviableStartChains[len(tempviableStartChains) - remain:]]

    workerCount = len(viableStartChains)
    tasks = [(viableStartChains[i], GLOBAL_maxDepth, i) for i in range(0, len(viableStartChains))]

    with ctx.Pool(processes = workerCount) as pool, open(f"chains_{GLOBAL_maxDepth}_{totalSpace}.txt", "w") as file:
        file.write("New run\n")
        for result in pool.imap_unordered(exploreChains, tasks, chunksize = 1):
            if saveResult:
                for c in result:
                    chainCounter += 1
                    file.write(f"Chain {chainCounter}: {c}\n")
            

    print(f"Total chain count {chainCounter}")
    print(f"Total time: {perf_counter() - startperf:.2f}s")

def toggleSave(value):
    global saveResult
    saveResult = value

def setDepth(depth):
    global GLOBAL_maxDepth
    GLOBAL_maxDepth = depth

def setConfigFile(file):
    global defaultConfigFile
    defaultConfigFile = file

def setMaxCoreCount(count):
    global maxCoreCount
    maxCoreCount = min(count, os.cpu_count()) 

def setTotalSpaces(spaces):
    global totalSpaceOverride
    totalSpaceOverride = spaces

parser = argparse.ArgumentParser(
    description = "Bus fever party level solver.",
    usage = "By default the script reads the cars.json file for level configuration. \n" \
    "Total space defines the total avaiable parking spaces. Cars is the starting configuration of the vehicles.\n" \
    "BlockedById represents the vehicles that blockes that. BlockesByCount is amount of vehicles that needs to move first.",
)
parser.add_argument("-d", "--depth", help="Sets the depth that the chain is going to be explored. WARNING: raising the depth makes the execution to be exponencially longer!", type=int)
parser.add_argument("-c", "--config", help="Sets the config file to be loaded, instead of the default cars.json",type=str)
parser.add_argument("-s", "--single", help="Run the solver as a single process. WARNING: can take a long time depending on the level od depth!", action="store_true")
parser.add_argument("-m", "--maxcore", help="Set the maximum amount of cores that can be used for solving.", type=int)
parser.add_argument("-a", "--save", help="Toggle whether the result should be saved or not.", action="store_false")
parser.add_argument("-t", "--total", help="Overwrite the total parking spaces", type=int)
arguments = parser.parse_args()

if arguments.depth is not None:
    setDepth(arguments.depth)

if arguments.config is not None:
    setConfigFile(arguments.config)

if arguments.maxcore is not None:
    setMaxCoreCount(arguments.maxcore)

if arguments.save is not None:
    toggleSave(arguments.save)

if arguments.total is not None:
    setTotalSpaces(arguments.total)

if arguments.single is not None:
    dfsSingleCore(GLOBAL_maxDepth)
else:
    main()
        

