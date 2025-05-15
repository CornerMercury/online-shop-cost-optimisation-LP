import json
from pulp import *
from collections import defaultdict

INPUT_JSON = ".jsonCarts/flooFullExodia.json"
SMALL_DEL = 132
MED_DEL = 237
BIG_DEL = 2000
BIG_M = 100000

def load_cart(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    items_needed = {}
    item_ids = []
    item_id_to_url = {}
    offer_catalog = {}
    offer_ids = []
    offer_to_seller = {}
    seller_to_offers = defaultdict(list)

    for item_index, item in enumerate(data):
        item_id = f"item_{item_index}"
        item_ids.append(item_id)
        items_needed[item_id] = item["amount"]
        item_id_to_url[item_id] = item["url"]

        for offer_index, offer in enumerate(item["sellers"]):
            if offer["available"] <= 0:
                continue

            base_seller = offer["name"]
            offer_id = f"{base_seller}_{item_index}_{offer_index}"
            offer_catalog[offer_id] = {
                "item_id": item_id,
                "cost": offer["cost"],
                "available": offer["available"],
                "seller": base_seller
            }

            offer_ids.append(offer_id)
            offer_to_seller[offer_id] = base_seller
            seller_to_offers[base_seller].append(offer_id)

    return items_needed, item_id_to_url, offer_catalog, offer_ids, offer_to_seller, seller_to_offers

def solve_shopping_problem(items_needed, item_id_to_url, offer_catalog, offer_ids, offer_to_seller, seller_to_offers):
    sellers = list(seller_to_offers.keys())
    item_ids = list(items_needed.keys())

    prob = LpProblem("ShoppingOptimizer", LpMinimize)

    # Variables
    x = LpVariable.dicts("buy", offer_ids, 0, None, LpInteger)
    y = LpVariable.dicts("use_seller", sellers, 0, 1, LpBinary)
    q = LpVariable.dicts("qty_seller", sellers, 0, None, LpInteger)
    z1 = LpVariable.dicts("small_del", sellers, 0, 1, LpBinary)
    z2 = LpVariable.dicts("med_del", sellers, 0, 1, LpBinary)
    z3 = LpVariable.dicts("big_del", sellers, 0, 1, LpBinary)

    # Objective: item cost + delivery
    prob += (
        lpSum(x[o] * offer_catalog[o]["cost"] for o in offer_ids) +
        lpSum(SMALL_DEL * z1[s] + MED_DEL * z2[s] + BIG_DEL * z3[s] for s in sellers)
    )

    # Demand constraints
    for item_id in item_ids:
        offers = [o for o in offer_ids if offer_catalog[o]["item_id"] == item_id]
        prob += lpSum(x[o] for o in offers) == items_needed[item_id]

    # Stock limits
    for o in offer_ids:
        prob += x[o] <= offer_catalog[o]["available"]

    # Link quantity to offers and seller usage
    for s in sellers:
        prob += q[s] == lpSum(x[o] for o in seller_to_offers[s])
        for o in seller_to_offers[s]:
            prob += x[o] <= offer_catalog[o]["available"] * y[s]  # Strong linkage

    # Delivery tier constraints with Big M logic
    for s in sellers:
        prob += z1[s] + z2[s] + z3[s] == y[s]

        # If z1 = 1 → q <= 4
        prob += q[s] <= 4 + (1 - z1[s]) * BIG_M

        # If z2 = 1 → 5 <= q <= 20
        prob += q[s] >= 5 * z2[s]
        prob += q[s] <= 20 + (1 - z2[s]) * BIG_M

        # If z3 = 1 → q >= 21
        prob += q[s] >= 21 * z3[s]

    print("Solving...")
    prob.solve(PULP_CBC_CMD(msg=True))

    if LpStatus[prob.status] != "Optimal":
        print("No optimal solution found.")
        return None

    # Extract item assignments
    assignment = defaultdict(list)
    for o in offer_ids:
        qty = x[o].varValue
        if qty and qty > 0:
            seller = offer_to_seller[o]
            assignment[seller].append((offer_catalog[o]["item_id"], o, int(qty)))

    # Extract delivery costs
    delivery_costs = {}
    for s in sellers:
        z1_val = z1[s].varValue or 0
        z2_val = z2[s].varValue or 0
        z3_val = z3[s].varValue or 0

        if round(z1_val) == 1:
            delivery_costs[s] = SMALL_DEL
        elif round(z2_val) == 1:
            delivery_costs[s] = MED_DEL
        elif round(z3_val) == 1:
            delivery_costs[s] = BIG_DEL
        else:
            delivery_costs[s] = 0

    # Calculate total cost
    total_cost = sum(
        sum(offer_catalog[offer_id]["cost"] * qty for _, offer_id, qty in orders) + delivery_costs.get(seller, 0)
        for seller, orders in assignment.items()
    )

    return assignment, delivery_costs, total_cost

def print_result(assignment, delivery_costs, total_cost, item_id_to_url, offer_catalog):
    print("\nOptimal Cart:\n")
    total_delivery_cost = 0
    for seller, orders in assignment.items():
        print(f"Seller: {seller}")
        item_total = 0
        total_qty = 0
        for item_id, offer_id, qty in orders:
            url = item_id_to_url.get(item_id, "Unknown URL")
            cost = offer_catalog[offer_id]["cost"]
            item_total += qty * cost
            total_qty += qty
            print(f" x{qty} €{cost / 100:.2f} {url}")
        delivery = delivery_costs.get(seller, 0)
        total_delivery_cost += delivery
        print(f"Total Items: {total_qty}")
        print(f"Items Total: €{item_total / 100:.2f}")
        print(f"Delivery Cost: €{delivery / 100:.2f}\n")

    print(f"Delivery Cost: €{total_delivery_cost / 100:.2f}")
    print(f"Total Cost (including delivery): €{total_cost / 100:.2f}")

# === Main ===
def main():
    (
        items_needed,
        item_id_to_url,
        offer_catalog,
        offer_ids,
        offer_to_seller,
        seller_to_offers
    ) = load_cart(INPUT_JSON)

    print("\n🔍 Checking availability:")
    for item_id in items_needed:
        total_available = sum(
            offer_catalog[o]["available"]
            for o in offer_ids
            if offer_catalog[o]["item_id"] == item_id
        )
        print(f"  - {item_id_to_url[item_id]}: need {items_needed[item_id]}, available {total_available}")
        if total_available < items_needed[item_id]:
            print("    ❌ Not enough stock!")
            return

    result = solve_shopping_problem(
        items_needed,
        item_id_to_url,
        offer_catalog,
        offer_ids,
        offer_to_seller,
        seller_to_offers
    )

    if result:
        assignment, delivery_costs, total_cost = result
        print_result(assignment, delivery_costs, total_cost, item_id_to_url, offer_catalog)

if __name__ == "__main__":
    main()