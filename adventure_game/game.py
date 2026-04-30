import os

SCENES = {
    "kitchen_counter": {
        "text": "You are Mudford the mudbug, stranded on the kitchen counter. A giant human is humming near a steaming pot. One wrong move and you are dinner.",
        "choices": [
            ("Scuttle toward the sink", "sink"),
            ("Duck behind the spice rack", "pantry"),
            ("Make a desperate dash toward the stove", "stove"),
        ],
    },
    "sink": {
        "text": "You reach the sink. A few drops of water glisten like hope, but the drain is a dark whirlpool of doom.",
        "choices": [
            ("Climb down the wet sponge", "hallway"),
            ("Hide in the drain strainer", "trapped"),
            ("Skitter along the rim toward the fridge", "under_fridge"),
        ],
    },
    "pantry": {
        "text": "Inside the pantry it smells like crackers and old onions. It is dim, quiet, and almost safe.",
        "choices": [
            ("Hide behind the potato bag", "dining_room"),
            ("Climb the canned corn tower", "boil_pot_area"),
            ("Sneak back out toward the hallway", "hallway"),
        ],
    },
    "stove": {
        "text": "Bad choice. The stove is hot, the air is steamy, and the boil pot is terrifyingly close.",
        "choices": [
            ("Leap for the nearby towel", "laundry_room"),
            ("Freeze and play dead", "boiled"),
            ("Back away toward the dining room", "dining_room"),
        ],
    },
    "dining_room": {
        "text": "You reach the dining room. Chair legs rise like a forest. No one is here... yet.",
        "choices": [
            ("Head for the hallway", "hallway"),
            ("Hide under the table", "trapped"),
            ("Sprint toward the back door", "back_door"),
        ],
    },
    "laundry_room": {
        "text": "You tumble into the laundry room in a pile of warm towels. It is safer here, but the dryer thumps like thunder.",
        "choices": [
            ("Crawl behind the detergent", "hallway"),
            ("Climb into a sock basket", "trapped"),
            ("Follow the cool breeze toward the back door", "back_door"),
        ],
    },
    "hallway": {
        "text": "The hallway stretches ahead like a hardwood desert. You can hear the human say, 'Where'd that little mudbug go?'",
        "choices": [
            ("Run to the back door", "back_door"),
            ("Dive under the fridge", "under_fridge"),
            ("Take a wrong turn back toward the kitchen", "boil_pot_area"),
        ],
    },
    "under_fridge": {
        "text": "Under the fridge is dusty, cramped, and full of ancient crumbs. Not glamorous, but maybe survivable.",
        "choices": [
            ("Wait quietly for the humans to leave", "escape"),
            ("Creep back out toward the hallway", "hallway"),
            ("Follow the warm pipe toward the stove", "stove"),
        ],
    },
    "back_door": {
        "text": "You made it to the back door. A sliver of daylight shines through the gap at the bottom.",
        "choices": [
            ("Squeeze through the gap to freedom", "escape"),
            ("Turn back because outside seems scary", "hallway"),
            ("Climb the doormat for a better look", "boil_pot_area"),
        ],
    },
    "boil_pot_area": {
        "text": "Oh no. You are right beside the giant boil pot. The water bubbles like a dragon's bath.",
        "choices": [
            ("Make a wild leap for the floor", "hallway"),
            ("Stay still and hope not to be noticed", "boiled"),
            ("Hide behind the seasoning box", "pantry"),
        ],
    },
    "escape": {
        "text": "You squeeze through the gap and tumble into the cool grass outside. You are muddy, alive, and definitely not boiled. You win!",
        "choices": [],
    },
    "boiled": {
        "text": "A massive hand scoops you up. The last thing you hear is, 'This one looks tasty.' You have been boiled. Game over.",
        "choices": [],
    },
    "trapped": {
        "text": "You picked a hiding place so good that now you cannot get out. You are safe from the pot... for now... but hopelessly trapped. Game over.",
        "choices": [],
    },
}

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def show_scene(scene_key):
    scene = SCENES[scene_key]
    clear_screen()
    print("=" * 60)
    print(scene["text"])
    print("=" * 60)
    print()
    if scene["choices"]:
        for i, (label, _) in enumerate(scene["choices"], start=1):
            print(f"{i}. {label}")

def get_choice(scene_key):
    choices = SCENES[scene_key]["choices"]
    while True:
        raw = input("\nChoose a number: ").strip()
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        number = int(raw)
        if 1 <= number <= len(choices):
            return choices[number - 1][1]
        print("That choice is out of range.")

def main():
    current = "kitchen_counter"
    while True:
        show_scene(current)
        if not SCENES[current]["choices"]:
            break
        current = get_choice(current)
    print("\nThanks for playing Mudbug Escape!")

if __name__ == "__main__":
    main()
