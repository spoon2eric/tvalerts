# tvalerts
![image](https://github.com/spoon2eric/tvalerts/assets/35353533/d362d049-749d-43d7-88cf-88f1accb1915)


## Description
**Tradingview Alerts** - Track alerts and their stages.

This is a Python-developed Flash application (webhook) designed to display and track your TradingView alerts. Simple :)

I wanted a way to track TradingView alerts more efficiently. Sometimes, you may want two, three, or even four "alerts" to occur in a specific sequence before making a buy or sell decision. The `tvalerts` project was thus created to help you ensure that multiple conditions are met in the correct order before executing a trade!

## Tradingview Setup
To set up, configure your alerts and pass in JSON. For example:
```json
{"ticker": "APPL", "plan": "Test", "stage": "Price Reached Level"}
```

The "stage" element of the JSON is crucial, and it is used with the assigned static value. If you intend to have three alerts trigger, with the 3rd one being the "BUY" trigger, you should set each alert as follows:

1)
```json
{"ticker": "GOOG", "plan": "Test", "stage": "Price Reached Level"}
```

2)
```json
{"ticker": "GOOG", "plan": "Test", "stage": "Moving Avg Cross"}
```

3)
```json
{"ticker": "GOOG", "plan": "Test", "stage": "Buy"}
```

Setup your plan and tickers on the Settings page and in the schema.sql file to populate tickers.

Last, run the python script and setup your webhook alert in TradingView to point to your server: http(s)://example.com/webhook
I've tested with cloudflare tunnels and it does work, just requires some configuration on your firewall.

In Summary:
Use a public URL, not a localhost or 127.0.0.1.
Consider using HTTPS for security.

![image](https://github.com/spoon2eric/tvalerts/assets/35353533/d2bd8066-1139-459b-93b5-8543eebbdeea)


## Installation
Download and use.
