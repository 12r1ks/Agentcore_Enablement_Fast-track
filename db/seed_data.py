"""Reset the CustomerSupport tables to the demo data in data/seed/.

Overwrites every seeded order and customer, and replaces the refunds ledger with the
refunds recorded on the seed orders, so demo refunds from earlier runs are removed.

Usage:  python db/seed_data.py [--region eu-central-1] [--project CustomerSupport]
"""

import argparse
import json
from decimal import Decimal
from pathlib import Path

import boto3

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"


def load(name: str) -> list[dict]:
    # DynamoDB rejects floats, so money values are loaded as Decimal.
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"), parse_float=Decimal)


def refunds_from(orders: list[dict]) -> list[dict]:
    """The refunds ledger rows for the refunds already recorded on the seed orders.
    Ledger keys are scoped per customer, in the same format as store._ledger_key in the tools."""
    return [
        {
            **refund,
            "idempotency_key": f"{order['customer_id']}#{refund['idempotency_key']}",
            "order_id": order["order_id"],
            "currency": order["currency"],
        }
        for order in orders
        for refund in order["refunds"]
    ]


def replace_all(table, key: str, items: list[dict]) -> None:
    scan = {"ProjectionExpression": "#k", "ExpressionAttributeNames": {"#k": key}}
    existing = []
    while True:
        page = table.scan(**scan)
        existing += [item[key] for item in page["Items"]]
        if "LastEvaluatedKey" not in page:
            break
        scan["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    # A batch may not touch a key twice, so only items that aren't seeded again are deleted; puts overwrite the rest.
    seeded = {item[key] for item in items}
    with table.batch_writer() as batch:
        for value in existing:
            if value not in seeded:
                batch.delete_item(Key={key: value})
        for item in items:
            batch.put_item(Item=item)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--project", default="CustomerSupport", help="Table name prefix (ProjectName in infra/data.yaml)")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    orders = load("orders.json")
    customers = load("customers.json")
    refunds = refunds_from(orders)

    replace_all(dynamodb.Table(f"{args.project}-orders"), "order_id", orders)
    replace_all(dynamodb.Table(f"{args.project}-customers"), "customer_id", customers)
    replace_all(dynamodb.Table(f"{args.project}-refunds"), "idempotency_key", refunds)
    print(f"Seeded {len(orders)} orders, {len(customers)} customers, {len(refunds)} refunds.")


if __name__ == "__main__":
    main()
