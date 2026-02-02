import requests
from functools import lru_cache
from datetime import datetime, timedelta

class CurrencyFetcher:
    _cache = {}
    _cache_time = None
    _cache_duration = timedelta(hours=3)
    
    @classmethod
    def _fetch_rates(cls, league="Fate of the Vaal"):
        url = f"https://poe.ninja/poe2/api/economy/exchange/current/overview"
        params = {
            "league": league,
            "type": "Currency"
        }
        
        response = requests.get(url, timeout=10, params=params)
        response.raise_for_status()
        data = response.json()
        
        rates = {"exalted": 1} 
        exaltedRate = data.get("core", "chaos").get("rates").get("exalted", 1)
        for line in data.get("lines", []):
            currency_id = line.get("id", "").lower()
            exalted_value = line.get("primaryValue", 1) * exaltedRate
            rates[currency_id] = exalted_value
        
        return rates
    
    @classmethod
    def get_rates(cls, league="Fate of the Vaal"):
        now = datetime.now()
        if cls._cache_time is None or now - cls._cache_time > cls._cache_duration:
            cls._cache = cls._fetch_rates(league)
            cls._cache_time = now
        return cls._cache
    
    @classmethod
    def get_price(cls, price_raw, league="Fate of the Vaal"):
        rates = cls.get_rates(league)
        currency = price_raw['currency']
        multiplier = rates.get(currency, 1)
        return price_raw['amount'] * multiplier
