import os, json

dataPoints = ['generic', 'unique']

baseExpectedFieldsDir = 'Model/expectedFields'
resultingFileJson = {}

for dataPoint in dataPoints:
    resultingFileJson[dataPoint] = {}
    currentPath = f'{baseExpectedFieldsDir}/{dataPoint}/'
    files = os.listdir(currentPath)
    for file in files:
        filename = os.fsdecode(file)
        if not '.json' in filename:
            print(f'{filename} is not a json file, skipping...')
            continue
        with open(f'{currentPath}/{filename}', 'r', encoding='utf-8') as f:
            data = json.load(f)
        rawFileName = filename.split('.')[0]
        resultingFileJson[dataPoint][rawFileName] = data

with open(f'aggregatedData.json', 'w', encoding='utf-8') as f:
    json.dump(resultingFileJson, f, ensure_ascii=False, indent=4)