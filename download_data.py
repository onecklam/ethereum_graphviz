from concurrent.futures import ThreadPoolExecutor
import requests


def get_urls(src="http://xblock.pro/xblock-eth.html"):
    r = requests.get(src)
    r.encoding = "utf-8"
    urls = []
    for line in r.text.strip().split("\n"):
        if line.find("<td>NormalTransaction</td>") > -1:
            urls = []
        elif line.find("<td>ERC20Transaction</td>") > -1:
            break
        elif line.find('<a href="') > -1 and line.find(".zip") > -1:
            urls.append((len(urls), line.split('<a href="')[1].split('" target=')[0]))
    return urls


def save_file(url):
    if url[0] < 9:
        start, end = url[0] * 1000000, url[0] * 1000000 + 999999
        filepath = "data/{}to{}_NormalTransaction.zip".format(start, end)
    elif url[0] >= 9 and url[0] < 18:
        start, end = (url[0] - 9) * 1000000, (url[0] - 9) * 1000000 + 999999
        filepath = "data/{}to{}_InternalEtherTransaction.zip".format(start, end)
    elif url[0] >= 18 and url[0] < 27:
        start, end = (url[0] - 18) * 1000000, (url[0] - 18) * 1000000 + 999999
        filepath = "data/{}to{}_ContractInfo.zip".format(start, end)
    elif url[0] >= 27 and url[0] < 36:
        start, end = (url[0] - 27) * 1000000, (url[0] - 27) * 1000000 + 999999
        filepath = "data/{}to{}_ContractCall.zip".format(start, end)

    with requests.get(url[1], stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return filepath


urls = get_urls()
with ThreadPoolExecutor() as executor:
    results = executor.map(save_file, urls)
    for result in results:
        print("Completed", result)
