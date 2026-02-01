import json, requests, os, numpy as np, itertools, textwrap, random, re
from math import log
from catboost import Pool, CatBoostRegressor
from Helpers.PriceHelper import getPrice
from parse import parse, compile

from parser import parseMod

requirementsMap = {62: 'level_requirement', 63: 'str_requirement', 64: 'dex_requirement', 65: 'int_requirement'}

def KeepRight(text: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'\[([^\]]+)\]', lambda m: m.group(1).split('|')[-1], text)).strip()

def LoadItems(dataDirectory):
    items = []
    for file in os.listdir(dataDirectory):
        filename = os.fsdecode(file)
        if not filename.startswith('data-'):
            continue
        with open(f'{dataDirectory}/{filename}', encoding='utf-8') as f:
            d = json.load(f)
            items.extend(d['result'])
    random.shuffle(items)
    return items

def GetEmptyVector(possibleModifiers, possibleProperties, possibleStats):
    obj = {}
    obj['baseType'] = ''
    obj['rarity'] = ''
    obj['ilvi'] = ''

    obj['corrupted'] = False
    obj['desecrated'] = False
    obj['mirrored'] = False
    obj['sanctified'] = False

    obj['level_requirement'] = 0
    obj['dex_requirement'] = 0
    obj['str_requirement'] = 0
    obj['int_requirement'] = 0

    obj['prefixes'] = 0
    obj['suffixes'] = 0
    obj['sockets'] = 0

    obj['pdps'] = 0
    obj['edps'] = 0
    obj['dps'] = 0

    obj['ar'] = 0
    obj['es'] = 0
    obj['ev'] = 0

    for possibleProperty in possibleProperties:
        obj[f'prop_{possibleProperty}'] = 0

    for possibleModifier in possibleModifiers:
        obj[f'mod_{possibleModifier}_present'] = 0
        obj[f'mod_{possibleModifier}_fract'] = 0
        obj[f'mod_{possibleModifier}_desecrated'] = 0
        obj[f'mod_{possibleModifier}_tier'] = 0

    for possibleStat in possibleStats:
        obj[f'stat_{possibleStat}_value'] = 0

    return obj

def numerizeProp(valueString):
    if '%' in valueString:
        return float(valueString.replace('%',''))
    if '-' in valueString:
        vals = valueString.split('-')
        return (float(vals[1]) + float(vals[0])) / 2
    if 'Large' in valueString:
        return 3
    if 'Medium' in valueString:
        return 2
    if 'Small' in valueString:
        return 1
    return float(valueString)

arbitraryPriceMultiplier = 10
def GetModString(stats):
    return ','.join(stats)

def GetStatStrings(mod):
    if not 'magnitudes' in mod or mod['magnitudes'] == None:
        return ''
    magns = []
    for magn in mod['magnitudes']:
        magnValue = magn['hash']
        if 'fractured' in magnValue or 'desecrated' in magnValue:
            magnValue = magnValue.replace('fractured', 'explicit').replace('desecrated', 'explicit')
        if not magnValue in magns:
            magns.append(magnValue)
    return magns

def TrainModel(modelName, dataDirectory, modelSaveDirectory, fieldsSaveDirectory, iterations = 1500, learningRate = 0.15, depth = 6):
    print(f"Starting training for {modelName}")
    print('Loading items...')
    items = LoadItems(dataDirectory)
    itemVectors = []
    itemPrices = []
    possibleProperties = []
    possibleModifiers = []
    possibleStats = []

    def LoadModifiers():
        print('Loading modifiers...')
        for item in items:
            mods = item['item']['extended']['mods']
            allmods = []
            for modCategory in ['explicit', 'implicit', 'fractured', 'desecrated']:
                if modCategory in mods:
                    allmods.extend(mods[modCategory])
            for mod in allmods:
                statStrs = GetStatStrings(mod)
                modStr = GetModString(statStrs)
                
                for statStr in statStrs:
                    if len(statStr) > 0 and not statStr in possibleStats:
                        possibleStats.append(statStr)
                if len(modStr) > 0 and not modStr in possibleModifiers:
                    possibleModifiers.append(modStr)

            properties = item['item']['properties']
            for itemProperty in properties:
                if 'type' in itemProperty and not itemProperty['type'] in possibleProperties:
                    possibleProperties.append(itemProperty['type'])

            possibleModifiers.sort()
            possibleProperties.sort()
            possibleStats.sort()

    def TransformItems():
        print('Transforming vectors...')
        itemsCount = len(items)
        itemsProcessed = 0
        for item in items:
            itemvector = GetEmptyVector(possibleModifiers, possibleProperties, possibleStats)
            itemvector['baseType'] = item['item']['baseType']
            itemvector['rarity'] = item['item']['rarity']
            if 'sockets' in item['item']:
                itemvector['sockets'] = len(item['item']['sockets'])
            if 'ilvl' in item['item']:
                itemvector['ilvl'] = item['item']['ilvl']

            # Requirements
            if 'requirements' in item['item']:
                requirements = item['item']['requirements']
                for reqirement in requirements:
                    if not reqirement['type'] in requirementsMap:
                        print(f'Can not find a requirement {reqirement['type']}')
                    else:
                        itemvector[requirementsMap[reqirement['type']]] = int(reqirement['values'][0][0])

            # Properties
            for simpleProperty in ['corrupted', 'desecrated', 'mirrored', 'sanctified']:
                if simpleProperty in item['item']:
                    itemvector[simpleProperty] = item['item'][simpleProperty]

            for extendedProperty in ['pdps', 'edps', 'dps', 'ar', 'es', 'ev']:
                if extendedProperty in item['item']['extended']:
                    itemvector[extendedProperty] = item['item']['extended'][extendedProperty]

            prefixes = 0
            suffixes = 0

            props = item['item']['properties']
            for prop in props:
                if not 'type' in prop:
                    continue
                propVal = 0
                for x in prop['values']:
                    propVal+= numerizeProp(x[0])
                itemvector[f'prop_{prop['type']}'] = propVal

            # Mods
            mods = item['item']['extended']['mods']
            hashes = item['item']['extended']['hashes']
            for modCategory in ['explicit', 'implicit', 'fractured', 'desecrated']:
                if not modCategory in mods:
                    continue;
                for mod in mods[modCategory]:
                    if mod['magnitudes'] == None:
                        continue
                    modStr = GetModString(GetStatStrings(mod))
                    tier = 0 
                    fractured = 0 
                    desecrated = 0 
                    isPrefix = False
                    isSuffix = False
                    if mod['tier'] != '':
                        isPrefix = 'P' in mod['tier']
                        isSuffix = 'S' in mod['tier']
                        tier = int(mod['tier'].replace('S','').replace('P',''))
                    if 'fractured' in modStr:
                        modStr = modStr.replace('fractured', 'explicit')
                        fractured = 1 
                    if 'desecrated' in modStr:
                        modStr = modStr.replace('desecrated', 'explicit')
                        desecrated = 1 

                    if f'mod_{modStr}_present' in itemvector:
                        itemvector[f'mod_{modStr}_present'] = 1
                        itemvector[f'mod_{modStr}_tier'] = tier
                        itemvector[f'mod_{modStr}_fract'] = fractured
                        itemvector[f'mod_{modStr}_desecrated'] = desecrated
                    else:
                        print('stuff not found!')
                    if isPrefix:
                        prefixes+=1
                    if isSuffix:
                        suffixes+=1

            itemvector['prefixes'] = prefixes
            itemvector['suffixes'] = suffixes

            # Stats
            stats = item['item']
            for modCategory in ['explicitMods', 'implicitMods', 'fracturedMods', 'desecratedMods']:
                if not modCategory in stats:
                    continue;
                for modText in stats[modCategory]:
                    textToParse = KeepRight(modText)
                    parsedResult = parseMod(textToParse)
                    if parsedResult == None:
                        print(f'Can not parse a mod! Value: {modText}')
                        continue;

                    numericValue = 0
                    if len(parsedResult['parseResult']) == 0:
                        numericValue = parsedResult['matchingData'][1]
                    elif len(parsedResult['parseResult']) == 1:
                        numericValue = parsedResult['parseResult'][0]
                    else:
                        numericValue = sum(parsedResult['parseResult']) / len(parsedResult['parseResult'])

                    statType = ''
                    if modCategory in ['explicitMods', 'fracturedMods', 'desecratedMods']:
                        statType = 'explicit'
                    else:
                        statType = 'implicit'
                    
                    statname = ''
                    for potentialStatName in parsedResult['matchingData'][3]['ids'][statType]:
                        if potentialStatName in possibleStats:
                            statname = potentialStatName
                            break
                    if len(statname) == 0:
                        print(f'Couldn\'t find a stat name for the stat! Value: {modText}')

                    itemvector[f'stat_{statname}_value'] += numericValue


            itemVectors.append([itemvector[k] for k in itemvector])

            priceCalculated = np.log1p(getPrice(item['listing']['price']) * arbitraryPriceMultiplier)
            itemPrices.append(priceCalculated)
            itemsProcessed+=1
            if itemsProcessed % 1000 == 0:
                print(f' Transformed ({itemsProcessed}/{itemsCount}) items...')
    def TrainModel():
        evalSetSize = int(len(itemVectors) * 0.1)

        trainVectors = itemVectors[:-evalSetSize or None]   
        trainPrices = itemPrices[:-evalSetSize or None]

        controlVectors = itemVectors[-evalSetSize:]
        controlPrices = itemPrices[-evalSetSize:]

        controlItems = items[-evalSetSize:]

        cat_features = [0,1]

        model = CatBoostRegressor(iterations=iterations,
                                  learning_rate=learningRate,
                                  depth=depth)

        eval_dataset = Pool(controlVectors,
                            controlPrices, 
                            cat_features=cat_features)

        model.fit(trainVectors, trainPrices, cat_features=cat_features, eval_set=eval_dataset)

        preds = model.predict(controlVectors)
        for i in range(preds.size):
            print(f'{i:>4}. [{"%.1f" % (np.expm1(controlPrices[i])/arbitraryPriceMultiplier):<8} { "%.1f" % (np.expm1(preds[i])/arbitraryPriceMultiplier):<12}] ({"%.1f" % np.abs(float(controlPrices[i]) - preds[i]):>12}) [{controlVectors[i][1]}]')
                
        print('')

        model.save_model(f"{modelSaveDirectory}/{modelName}", format="cbm", pool=trainVectors)
        with open(f"{fieldsSaveDirectory}/{modelName}.json", 'w', encoding='utf-8') as f:
            json.dump({'properties': possibleProperties, 'modifiers': possibleModifiers, 'stats': possibleStats}, f, ensure_ascii=False, indent=4)

    LoadModifiers()
    TransformItems();
    TrainModel();
    
    print()

