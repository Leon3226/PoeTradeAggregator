import json, os, uuid

sessionId = uuid.uuid4()
dataToSave = {"generic" : {}, "unique":{}}
listingsToDelete = []

os.chdir('Data/Raw')

def ProcessItem(itemJson):
    if not 'item' in itemJson or not 'rarity' in itemJson['item']:
        return
    name = itemJson['item']['name']
    itemRarity = itemJson['item']['rarity']
    identified = itemJson['item']['identified']
    itemType = itemJson['item']['properties'][0]['name'].replace('[','').replace(']','').replace('|',' ')

    if not identified:
        return #skip unidentified for now

    if itemRarity != 'Unique':
        if not itemType in dataToSave['generic']:
            dataToSave['generic'][itemType] = []
        dataToSave['generic'][itemType].append(item)
    else:
        if not name in dataToSave['unique']:
            dataToSave['unique'][name] = []
        dataToSave['unique'][name].append(item)
    listingsToDelete.append(itemJson['id'])

rawFiles = os.listdir()
rawFileLen = len(rawFiles)
print(f'Found {rawFileLen} files to sort')

fileCounter = 0
for file in os.listdir():
    filename = os.fsdecode(file)
    fileCounter+=1
    if not '.json' in filename:
        print(f'{filename} is not a json file, skipping...')
        continue
    with open(filename, encoding='utf-8') as f:
        data = json.load(f)
        if 'data' in data:
            data = data['data']
        if 'result' in data:
            data = data['result']
        for item in data:
            ProcessItem(item)
    print(f'({fileCounter}\\{rawFileLen}) files sorted...')


print()
print('Saving the data...')
os.chdir('..') 
os.makedirs('sorted', exist_ok=True)
os.chdir('sorted') 
os.makedirs('generic', exist_ok=True)
os.chdir('generic') 

print('Saving generics...')

for key in dataToSave['generic']:
    os.makedirs(key, exist_ok=True)
    os.chdir(key) 
    print(f'    Saving {key}...')
    with open(f'data-{sessionId}.json', 'w') as f:
        json.dump({'result':dataToSave['generic'][key]}, f)
    os.chdir('..') 
    pass

print()
print('Saving uniques...')
os.chdir('..')
os.makedirs('unique', exist_ok=True)
os.chdir('unique') 

for key in dataToSave['unique']:
    os.makedirs(key, exist_ok=True)
    print(f'    Saving {key}...')
    os.chdir(key) 
    with open(f'data-{sessionId}.json', 'w') as f:
        json.dump({'result': dataToSave['unique'][key]}, f)
    os.chdir('..') 
    pass

os.chdir('../../Raw') 
print()
print('Deleting processed data from the raw data...')

rawFiles = os.listdir()
rawFileLen = len(rawFiles)
fileCounter = 0
for file in os.listdir():
    filename = os.fsdecode(file)
    fileCounter+=1
    if not '.json' in filename:
        print(f'{filename} is not a json file, skipping...')
        continue
    fileData = {}
    newData = {}
    oldLen = 0
    newLen = 0
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
        newData = {'result': []}
        if 'data' in data:
            data = data['data']
        if 'result' in data:
            data = data['result']
        for item in data:
            if not item['id'] in listingsToDelete:
                newData['result'].append(item)
        oldLen = len(data)
        newLen = len(newData['result'])
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(newData, f, ensure_ascii=False, indent=4)
    print(f'({fileCounter}\\{rawFileLen}) raw files truncated, kept {newLen}\\{oldLen} unsorted items...')

print()