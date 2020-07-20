import os
from datetime import datetime
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient


def process_transaction(file, record):
    if float(record["value"]) == 0:
        return 0
    if file.find("NormalTransaction") > -1:
        record["timestamp"] = datetime.fromtimestamp(int(record["timestamp"]))
        record["value"] = float(record["value"])
        db[file].insert_one(record)
    elif file.find("InternalEtherTransaction") > -1:
        if record["from"] != "reward":
            record["timestamp"] = datetime.fromtimestamp(int(record["timestamp"]))
            record["fromIsContract"] = (
                True if int(record["fromIsContract"]) > 0 else False
            )
            record["toIsContract"] = True if int(record["toIsContract"]) > 0 else False
            record["value"] = float(record["value"])
            db[file].insert_one(record)


def process_contract(file, record):
    if file.find("ContractInfo") > -1:
        record["createdTimestamp"] = datetime.fromtimestamp(
            int(record["createdTimestamp"])
        )
        record["creatorIsContract"] = (
            True if int(record["creatorIsContract"]) > 0 else False
        )
    elif file.find("ContractCall") > -1:
        record["timestamp"] = datetime.fromtimestamp(int(record["timestamp"]))
        record["fromIsContract"] = True if int(record["fromIsContract"]) > 0 else False
        record["toIsContract"] = True if int(record["toIsContract"]) > 0 else False
    db[file].insert_one(record)


def save_data(file):
    with ZipFile("data/{}.zip".format(file), "r") as data_zip:
        file = "{}_Created".format(file) if file.find("ContractInfo") > -1 else file
        with data_zip.open("{}.csv".format(file), "r") as data_csv:
            line = data_csv.readline().decode("utf-8").strip()
            if file.find("NormalTransaction") > -1:
                indexes = [1, 2, 3, 4, 6]
                fields = [line.split(",")[index] for index in indexes]
            elif file.find("InternalEtherTransaction") > -1:
                indexes = [1, 2, 3, 4, 5, 6, 7]
                fields = [line.split(",")[index] for index in indexes]
            elif file.find("ContractInfo") > -1:
                indexes = [0, 2, 4, 5]
                fields = [line.split(",")[index] for index in indexes]
            elif file.find("ContractCall") > -1:
                indexes = [1, 3, 4, 5, 6]
                fields = [line.split(",")[index] for index in indexes]

            while True:
                line = data_csv.readline().decode("utf-8").strip()
                if len(line) == 0:
                    break
                values = [line.split(",")[index] for index in indexes]
                record = {field: value for field, value in zip(fields, values)}
                if file.find("Transaction") > -1:
                    process_transaction(file, record)
                elif file.find("Contract") > -1:
                    process_contract(file, record)
    return file


files = [file.split(".")[0] for file in os.listdir("data")]
db = MongoClient()["ethereum_tx"]
with ThreadPoolExecutor() as executor:
    results = executor.map(save_data, files)
    for result in results:
        print("Completed", result)
