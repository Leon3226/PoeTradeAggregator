def getPrice(priceRaw):
    priceMultiplier = 1

    match priceRaw['currency']:
        case 'divine':
            priceMultiplier = 388
        case 'mirror':
            priceMultiplier = 548000
        case 'wisdom':
            priceMultiplier = 0.0001
        case 'chaos':
            priceMultiplier = 19
        case 'exalted':
            priceMultiplier = 1
        case 'annul':
            priceMultiplier = 86
        case 'vaal':
            priceMultiplier = 1/1.5
        case 'regal':
            priceMultiplier = 0.1
        case 'transmute':
            priceMultiplier = 1/40
        case 'aug':
            priceMultiplier = 1/27
        case 'alch':
            priceMultiplier = 1/11
        case 'chance':
            priceMultiplier = 8.7
        case 'artificers':
            priceMultiplier = 1/7.1
        case 'fracturing-orb':
            priceMultiplier = 199
        case 'perfect-orb-of-transmutation':
            priceMultiplier = 1/3.7
        case 'greater-regal-orb':
            priceMultiplier = 1/3.1
        case 'greater-chaos-orb':
            priceMultiplier = 42
        case 'greater-orb-of-transmutation':
            priceMultiplier = 1/531
        case 'greater-exalted-orb':
            priceMultiplier = 3
        case 'perfect-orb-of-augmentation':
            priceMultiplier = 2.1
        case 'perfect-exalted-orb':
            priceMultiplier = 887
        case _:
            priceMultiplier = 1

    return priceRaw['amount'] * priceMultiplier