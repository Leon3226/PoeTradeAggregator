from parse import parse, compile
import pandas as pd

records = {'values': []}
matchers = []

def compile_parse(matcher: str):
    fmt = matcher.replace('#', '{:g}')
    return compile(fmt)

def initParser():
    records['values'] = pd.read_json('Data/stats.ndjson', lines=True)
    i = 0
    for record in records['values'].values:
        for matcher in record[2]:
            compiledMatcher = compile_parse(matcher['string'])
            matchers.append({'matcher': compiledMatcher, 'recordIndex': i})
        i+=1
    
def parseMod(modText):
    i = 0
    for matcher in matchers:
        parseResult = matcher['matcher'].parse(modText)
        if not parseResult == None:
            return {'parseResult': parseResult.fixed, 'matchingData': records['values'].values[matcher['recordIndex']]} 
        i+=1
    return None
