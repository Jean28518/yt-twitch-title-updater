import json

def main():
    print("Hello World!")

    # Load the config from the JSON file
    with open("config.json", "r") as file:
        data = json.load(file)
    print(data["name"])


if __name__ == "__main__":
    main()