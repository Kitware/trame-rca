import asyncio
import keyboard
import time
import numpy as np

from PIL import Image
from vizdoom import DoomGame, ScreenResolution, Button, Mode

# Initialize Doom
game = DoomGame()
# game.load_config("basic.cfg")
game.load_config("deathmatch.cfg")

game.set_episode_timeout(0)
game.set_window_visible(True)  # prevent Vizdoom from handling keyboard events
# game.set_window_visible(False)  # prevent Vizdoom from handling keyboard events
game.set_screen_resolution(ScreenResolution.RES_800X600)

# Keyboard-to-Button mapping
key_to_button_map = {
    "w": Button.MOVE_FORWARD,
    "s": Button.MOVE_BACKWARD,
    "a": Button.TURN_LEFT,
    "d": Button.TURN_RIGHT,
    "space": Button.ATTACK,
    "e": Button.USE,
    "q": Button.JUMP,
    "ctrl": Button.CROUCH,
    "1": Button.SELECT_WEAPON1,
    "2": Button.SELECT_WEAPON2,
    "3": Button.SELECT_WEAPON3,
    "left": Button.MOVE_LEFT,
    "right": Button.MOVE_RIGHT,
    "r": Button.RELOAD
}

# Set available buttons dynamically using the dictionary values
game.set_available_buttons(list(key_to_button_map.values()))


# Function to create action list based on the keys pressed
def get_action_from_keys():
    action = [0] * len(game.get_available_buttons())  # Start with all buttons as 0
    for key, button in key_to_button_map.items():
        if keyboard.is_pressed(key):
            # Set the corresponding button index to 1
            action[game.get_available_buttons().index(button)] = 1
    return action


# Function to save the screen image using PIL
def save_screen_as_jpg(screen_buffer, quality=75):
    # Convert the screen buffer (RGB format) to a PIL Image
    image = Image.fromarray(np.transpose(screen_buffer, (1, 2, 0)))  # Convert from [3, H, W] to [H, W, 3]

    # Save the image as JPG
    filename = f"screenshot_{time.time():.0f}.jpg"
    image.save(filename, "JPEG", quality=quality)
    print(f"Saved image: {filename}")


game.set_mode(Mode.PLAYER)
game.init()


# Game loop running independently
async def run_doom():
    print("ViZDoom started...")

    while not game.is_episode_finished():
        game.advance_action()  # Default game progression

        # Capture and save the screen
        state = game.get_state()
        if state:
            save_screen_as_jpg(state.screen_buffer)  # Raw frame (shape: [3, H, W])

        await asyncio.sleep(0.02)  # Run at ~20 FPS

    game.close()
    print("ViZDoom closed.")


# Real-time user input handling
async def listen_for_input():
    while True:

        # Get the action based on key press
        action = get_action_from_keys()

        if any(action):  # If any action is detected, execute it
            print(f"User action: {action}")
        game.set_action(action)
        # else:
        #     game.make_action([0] * len(buttons), 1)

        await asyncio.sleep(0.1)  # Check input every 100ms


# Main function to run both game and user input handling
async def main():
    # Start Doom in the background
    doom_task = asyncio.create_task(run_doom())

    # Start real-time keyboard input handling
    input_task = asyncio.create_task(listen_for_input())

    # Wait for both tasks to complete
    await asyncio.gather(doom_task, input_task)

# Run the asyncio event loop
asyncio.run(main())
