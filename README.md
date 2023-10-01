# tvalerts
![image](https://github.com/spoon2eric/tvalerts/assets/35353533/f74ff2e9-fc0a-4116-9c53-08aaaf0a77c5)


Your README.md file is looking good! Here are a few suggestions to make it clearer and more polished:

---

## Description
**Tradingview Alerts** - Track alerts and their stages.

This is a Python-developed Flash application (webhook) designed to display and track your TradingView alerts. Simple :)

I wanted a way to track TradingView alerts more efficiently. Sometimes, you may want two, three, or even four "events" to occur in a specific sequence before making a buy or sell decision. The `tvalerts` project was thus created to help you ensure that multiple conditions are met in the correct order before executing a trade!

## Tradingview Setup
To set up, configure your alerts and pass in JSON. For example:
```json
{"ticker": "ETH", "action": "Buy", "signal_type": "Green Dot", "stage": 3}
```

The "stage" element of the JSON is crucial, and it is used with the assigned static value. If you intend to have three alerts trigger, with the 3rd one being the "BUY" trigger, you should set each alert as follows:

1)
```json
{"ticker": "ETH", "action": "Buy", "signal_type": "Big Green Dot", "stage": 1}  // First buy signal
```

2)
```json
{"ticker": "ETH", "action": "Sell", "signal_type": "Red Dot", "stage": 2}  // First sell signal
```

3)
```json
{"ticker": "ETH", "action": "Buy", "signal_type": "Green Dot", "stage": 3}  // Final signal to BUY!!
```

Once the static value and stage are equal, the sequence is complete. If stage 3 occurs before stage 2, an error will occur.

Last, run the python script and setup your webhook alert in TradingView to point to your server: https://example.com:5000/webhook

In Summary:
Use a public URL, not a localhost or 127.0.0.1.
Consider using HTTPS for security.

![image](https://github.com/spoon2eric/tvalerts/assets/35353533/d2bd8066-1139-459b-93b5-8543eebbdeea)


## Installation
Download and use.
