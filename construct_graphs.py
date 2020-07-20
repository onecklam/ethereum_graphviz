import json
from pymongo import MongoClient


def construct_ccg(collection):
    for record in db[collection].find():
        db["Contracts"].insert_one({"address": record["address"]})
        if not (record["creator"] in exchanges or record["address"] in exchanges):
            continue

        edge = {
            "from_name": record["creator"],
            "to_name": record["address"],
            "time_stamp": record["createdTimestamp"],
        }
        if record["creatorIsContract"]:
            from_node = {"node_name": edge["from_name"], "node_type": "Contract"}
        else:
            from_node = {"node_name": edge["from_name"], "node_type": "Address"}
        to_node = {"node_name": edge["to_name"], "node_type": "Contract"}
        if record["creator"] in exchanges:
            edge["from_name"] = exchanges[record["creator"]]
            from_node["node_name"] = edge["from_name"]
        if record["address"] in exchanges:
            edge["to_name"] = exchanges[record["address"]]
            to_node["node_name"] = edge["to_name"]

        db["ccg_edges"].replace_one({"to_name": edge["to_name"]}, edge, upsert=True)
        db["ccg_nodes"].replace_one(
            {"node_name": edge["from_name"]}, from_node, upsert=True
        )
        db["ccg_nodes"].replace_one(
            {"node_name": edge["to_name"]}, to_node, upsert=True
        )


def construct_cig(collection):
    for record in db[collection].find():
        if not (record["from"] in exchanges or record["to"] in exchanges):
            continue

        edge = {
            "from_name": record["from"],
            "to_name": record["to"],
            "time_stamp": record["timestamp"],
        }
        if record["fromIsContract"]:
            from_node = {"node_name": edge["from_name"], "node_type": "Contract"}
        else:
            from_node = {"node_name": edge["from_name"], "node_type": "Address"}
        if record["toIsContract"]:
            to_node = {"node_name": edge["to_name"], "node_type": "Contract"}
        else:
            to_node = {"node_name": edge["to_name"], "node_type": "Address"}
        if record["from"] in exchanges:
            edge["from_name"] = exchanges[record["from"]]
            from_node["node_name"] = edge["from_name"]
        if record["to"] in exchanges:
            edge["to_name"] = exchanges[record["to"]]
            to_node["node_name"] = edge["to_name"]

        db["cig_edges"].update_one(edge, {"$inc": {"number_of_calls": 1}}, upsert=True)
        db["cig_nodes"].replace_one(
            {"node_name": edge["from_name"]}, from_node, upsert=True
        )
        db["cig_nodes"].replace_one(
            {"node_name": edge["to_name"]}, to_node, upsert=True
        )


def construct_mfg1(collection):
    for record in db[collection].find():
        db["Transactions"].insert_one({"transactionHash": record["transactionHash"]})
        if not (record["from"] in exchanges or record["to"] in exchanges):
            continue

        edge = {
            "from_name": record["from"],
            "to_name": record["to"],
            "time_stamp": record["timestamp"],
        }
        value_in_ether = record["value"]
        if record["fromIsContract"]:
            from_node = {"node_name": edge["from_name"], "node_type": "Contract"}
        else:
            from_node = {"node_name": edge["from_name"], "node_type": "Address"}
        if record["toIsContract"]:
            to_node = {"node_name": edge["to_name"], "node_type": "Contract"}
        else:
            to_node = {"node_name": edge["to_name"], "node_type": "Address"}
        if record["from"] in exchanges:
            edge["from_name"] = exchanges[record["from"]]
            from_node["node_name"] = edge["from_name"]
        if record["to"] in exchanges:
            edge["to_name"] = exchanges[record["to"]]
            to_node["node_name"] = edge["to_name"]

        db["mfg_edges"].update_one(
            edge, {"$inc": {"value_in_ether": value_in_ether}}, upsert=True
        )
        db["mfg_nodes"].replace_one(
            {"node_name": edge["from_name"]}, from_node, upsert=True
        )
        db["mfg_nodes"].replace_one(
            {"node_name": edge["to_name"]}, to_node, upsert=True
        )


def construct_mfg2(collection):
    for record in db[collection].find():
        if not (record["from"] in exchanges or record["to"] in exchanges):
            continue
        if db["Transactions"].find_one({"transactionHash": record["transactionHash"]}):
            continue

        edge = {
            "from_name": record["from"],
            "to_name": record["to"],
            "time_stamp": record["timestamp"],
        }
        value_in_ether = record["value"]
        if db["Contracts"].find_one({"address": record["from"]}):
            from_node = {"node_name": edge["from_name"], "node_type": "Contract"}
        else:
            from_node = {"node_name": edge["from_name"], "node_type": "Address"}
        if db["Contracts"].find_one({"address": record["to"]}):
            to_node = {"node_name": edge["to_name"], "node_type": "Contract"}
        else:
            to_node = {"node_name": edge["to_name"], "node_type": "Address"}
        if record["from"] in exchanges:
            edge["from_name"] = exchanges[record["from"]]
            from_node["node_name"] = edge["from_name"]
        if record["to"] in exchanges:
            edge["to_name"] = exchanges[record["to"]]
            to_node["node_name"] = edge["to_name"]

        db["mfg_edges"].update_one(
            edge, {"$inc": {"value_in_ether": value_in_ether}}, upsert=True
        )
        db["mfg_nodes"].replace_one(
            {"node_name": edge["from_name"]}, from_node, upsert=True
        )
        db["mfg_nodes"].replace_one(
            {"node_name": edge["to_name"]}, to_node, upsert=True
        )


with open("exchanges.json", "r") as f:
    exchanges = json.load(f)

db = MongoClient()["ethereum_tx"]
collections = list(db.list_collection_names())
ccg_data = [
    collection
    for collection in collections
    if collection.find("ContractInfo_Created") > -1
]
cig_data = [
    collection for collection in collections if collection.find("ContractCall") > -1
]
mfg_data1 = [
    collection
    for collection in collections
    if collection.find("InternalEtherTransaction") > -1
]
mfg_data2 = [
    collection
    for collection in collections
    if collection.find("NormalTransaction") > -1
]
for collection in sorted(ccg_data):
    construct_ccg(collection)
for collection in sorted(cig_data):
    construct_cig(collection)
for collection in sorted(mfg_data1):
    construct_mfg1(collection)
for collection in sorted(mfg_data2):
    construct_mfg2(collection)
for collection in db.list_collection_names():
    if collection.find("Contract") > -1 or collection.find("Transaction") > -1:
        db[collection].drop()
