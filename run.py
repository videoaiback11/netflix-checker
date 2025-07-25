import asyncio
import aiohttp
import os
import json
import datetime
import random
from colorama import Fore, Style, init

init(autoreset=True)

VERSION = "1.2"
API_VER_URL = "https://blockbot.dev/api/api_version.txt"
API_LIST_URL = "https://blockbot.dev/api/api_netflix.txt"
API_FILE = "api_netflix.txt"
counter = 0

def save_api_file(content):
    with open(API_FILE, "w") as f:
        f.write(content)

async def load_api_list():
    if not os.path.exists(API_FILE):
        print(Fore.YELLOW + f"{API_FILE} not found, downloading...")
        async with aiohttp.ClientSession() as session:
            async with session.get(API_LIST_URL) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    save_api_file(content)
                else:
                    print(Fore.RED + "Failed to fetch API list!")
                    exit()

    with open(API_FILE) as f:
        urls = [x.strip() for x in f if x.strip()]
    if not urls:
        print(Fore.RED + "No API endpoint found in api_netflix.txt")
        exit()
    return urls

async def check_version():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_VER_URL, timeout=10) as resp:
                remote_version = (await resp.text()).strip()
                if remote_version != VERSION:
                    print(Fore.RED + f"Validator out of date (local: {VERSION}, remote: {remote_version})")
                    print(Fore.RED + "Please contact admin for update!")
                    exit()
    except Exception:
        print(Fore.RED + "Failed to check version. Please try again.")
        exit()

def load_proxy():
    if not os.path.exists("config.json"):
        print(Fore.RED + "config.json not found!")
        exit()
    with open("config.json") as f:
        data = json.load(f)
        p = data.get("proxy", {})
        if all(k in p for k in ("ip", "port", "username", "password")):
            return f"{p['ip']}:{p['port']}:{p['username']}:{p['password']}"
        else:
            print(Fore.RED + "Invalid config.json format")
            exit()

def save_result(filename, email, folder):
    filepath = os.path.join(folder, f"{filename}.txt")
    with open(filepath, "a") as f:
        f.write(email + "\n")

def print_box_header():
    box_lines = [
        "Validator : Netflix",
        f"Version   : {VERSION}",
        "Date      : 23 July 2025",
        "We Have   : Amazon, Robinhood, Paypal, Netflix, xFinity, Coinbase"
    ]
    width = max(len(line) for line in box_lines) + 4
    border = "+" + "-" * width + "+"
    print(Fore.YELLOW + border)
    for line in box_lines:
        print(Fore.YELLOW + "| " + line.ljust(width - 2) + "|")
    print(Fore.YELLOW + border)

async def check_email(session, email, api_list, proxy, result_dir, total, attempt=1):
    global counter
    url = random.choice(api_list)
    full_url = f"{url}?email={email}&proxy={proxy}"

    try:
        async with session.get(full_url, timeout=30) as resp:
            if resp.status == 200:
                try:
                    data = await resp.json()
                except aiohttp.ContentTypeError:
                    status, color, file = "ERROR", Fore.RED, "ERROR"
                else:
                    status = data.get("status", "").upper()
                    error = data.get("error", "").upper()

                    if status == "SUBSCRIBED":
                        status, color, file = "LIVE", Fore.GREEN, "LIVE"
                    elif status == "DEAD":
                        status, color, file = "DEAD", Fore.RED, "DEAD"
                    elif status == "FREE":
                        status, color, file = "FREE", Fore.WHITE, "FREE"
                    elif status == "EXPIRED":
                        status, color, file = "EXPIRED", Fore.YELLOW, "EXPIRED"
                    elif status == "BAD_IP" or error == "BAD_IP":
                        if attempt < 3:
                            return await check_email(session, email, api_list, proxy, result_dir, total, attempt + 1)
                        else:
                            status, color, file = "BAD_IP", Fore.BLUE, "BAD_IP"
                    else:
                        status, color, file = "ERROR", Fore.RED, "ERROR"
            else:
                status, color, file = "ERROR", Fore.RED, "ERROR"
    except Exception:
        status, color, file = "ERROR", Fore.RED, "ERROR"

    save_result(file, email, result_dir)
    counter += 1
    timestamp = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    print(f"{color}[{str(counter).rjust(3)}/{total}] [{timestamp}] [{status.ljust(7)}] => {email}")

async def main():
    await check_version()
    print_box_header()

    input_file = input("Input file name: ").strip()
    if not input_file or not os.path.exists(input_file):
        print(Fore.RED + "File not found!")
        return

    result_dir = input("Input folder result (default Result): ").strip() or "Result"
    os.makedirs(result_dir, exist_ok=True)

    proxy = load_proxy()
    with open(input_file, "r") as f:
        emails = [x.strip() for x in f if x.strip()]

    total = len(emails)
    api_list = await load_api_list()

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_email(session, email, api_list, proxy, result_dir, total) for email in emails]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
