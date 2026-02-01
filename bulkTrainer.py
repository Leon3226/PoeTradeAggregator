from PoeTradeAggregator import train_model
from parser import initParser, parseMod

import os

initParser();

TRAIN_GENERIC = True
TRAIN_UNUIQUE = False
IGNORE_EXISTING = False

whitelist = ['Bow']
exceptions = ['Area Level']

baseDataDir = 'Data/sorted'
baseExpectedFieldsDir = 'Model/expectedFields'
baseTrainModelDir = 'Model/gradientBoostModel'

trainDirs = []
if TRAIN_GENERIC:
    trainDirs.append('generic')
if TRAIN_UNUIQUE:
    trainDirs.append('unique')

whitelistMode = len(whitelist) > 0
for specificDir in trainDirs:
    dirPath = f'{baseDataDir}/{specificDir}'
    for folder in os.listdir(dirPath):

        if whitelistMode:
            if not folder in whitelist:
                continue
        else:
            if folder in exceptions:
                continue
        if IGNORE_EXISTING and os.path.exists(f'{baseTrainModelDir}/{specificDir}/{folder}'):
            continue
        train_model(folder, f'{dirPath}/{folder}', f'{baseTrainModelDir}/{specificDir}', f'{baseExpectedFieldsDir}/{specificDir}', learning_rate=0.12, depth=7)
print()