
# Online Shop Cost Optimisation

A linear programming solution to minimise cost for the delivery of a large amount of items, particularly optimised for situations where the delivery cost is not negligible and sellers are common between items.

An example of this is [Cardmarket](https://www.cardmarket.com/en/). I made this project for this site, so feel free to ask for the webscraper.




## Usage

### JSON Format

Scrape the item data into this format.

- Each item in the outer array represents an item you want to buy.
- Cost is stored in the base unit, so cents or pence etc.
```json
[
  {
    "sellers": [
        {
        "available": 1,
        "cost": 1,
        "name": "seller"
      }
    ],
    "amount": 1,
    "url": "https://google.com"
  }
]
```

### Edit Constants
- In constants.py, edit these values to your liking.

### Run

- Run main.py with a specified file
```sh
python3 main.py 1.json
```