from pynput import mouse, keyboard
from pynput.mouse import Button, Controller
import json
import time
import threading

SPEED = 10.0

events = []
recording = False
start_time = 0

mode = "idle"
play_thread = None
play_events = []
play_start_time = 0
play_index = 0
pause_flag = False

mouse_controller = Controller()

def on_press(key):
    global recording, events, start_time, mode, play_thread, play_events, play_start_time, play_index, pause_flag
    try:
        if key == keyboard.KeyCode.from_char('q'):
            print("[TAS] - Shutting down...")
            if play_thread and play_thread.is_alive():
                mode = "idle"
                pause_flag = False
                play_thread.join(0.1)
            return False
        elif key == keyboard.KeyCode.from_char('r'):
            if mode == "idle" or mode == "recording":
                if not recording:
                    print("[TAS] - Recording started...")
                    mode = "recording"
                    recording = True
                    events = []
                    start_time = time.time()
                else:
                    recording = False
                    mode = "idle"
                    for e in events:
                        e['time'] -= start_time
                    with open('mouse_tas.json', 'w') as f:
                        json.dump(events, f, indent=2)
                    print(f"[TAS] - Recording stopped. Saved {len(events)} events to mouse_tas.json")
        elif key == keyboard.KeyCode.from_char('s'):
            if mode == "idle" or mode == "playing" or mode == "paused":
                if mode == "playing" or mode == "paused":
                    mode = "idle"
                    pause_flag = False
                    if play_thread and play_thread.is_alive():
                        play_thread.join(0.1)
                    print("[TAS] - Playback stopped.")
                try:
                    with open('mouse_tas.json', 'r') as f:
                        play_events = json.load(f)
                    if not play_events:
                        print("[TAS] - No events to play.")
                        return
                    print(f"[TAS] - Playing started (speed {SPEED}x)...")
                    mode = "playing"
                    pause_flag = False
                    play_index = 0
                    play_start_time = time.time()
                    if play_thread is None or not play_thread.is_alive():
                        play_thread = threading.Thread(target=play_loop)
                        play_thread.start()
                except FileNotFoundError:
                    print("[TAS] - No recorded file found.")
        elif key == keyboard.KeyCode.from_char('p'):
            if mode == "playing":
                pause_flag = not pause_flag
                if pause_flag:
                    print("[TAS] - Paused.")
                else:
                    print("[TAS] - Resumed.")
            elif mode == "paused":
                pause_flag = False
                mode = "playing"
                print("[TAS] - Resumed.")
    except AttributeError:
        pass

def play_loop():
    global mode, play_index, play_start_time, pause_flag
    while mode == "playing" or mode == "paused":
        if mode == "paused":
            time.sleep(0.01)
            continue
        if play_index >= len(play_events):
            print("[TAS] - Playback finished.")
            mode = "idle"
            break
        event = play_events[play_index]
        elapsed = time.time() - play_start_time
        wait = (event['time'] / SPEED) - elapsed
        if wait > 0:
            time.sleep(wait)
        if mode == "paused":
            continue
        if event['type'] == 'move':
            mouse_controller.position = (event['x'], event['y'])
        elif event['type'] == 'click':
            button = getattr(Button, event['button'])
            if event['pressed']:
                mouse_controller.press(button)
            else:
                mouse_controller.release(button)
        elif event['type'] == 'scroll':
            mouse_controller.scroll(event['dx'], event['dy'])
        play_index += 1
    if mode == "playing" or mode == "paused":
        mode = "idle"

def on_move(x, y):
    if recording:
        events.append({'type':'move','x':x,'y':y,'time':time.time()})

def on_click(x, y, button, pressed):
    if recording:
        events.append({'type':'click','x':x,'y':y,'button':button.name,'pressed':pressed,'time':time.time()})

def on_scroll(x, y, dx, dy):
    if recording:
        events.append({'type':'scroll','x':x,'y':y,'dx':dx,'dy':dy,'time':time.time()})

print("[TAS] - Mouse TAS Recorder/Player")
print("[TAS] - R: record start/stop, S: play/stop, P: pause/resume, Q: quit")
print(f"[TAS] - Playback speed: {SPEED}x")

keyboard_listener = keyboard.Listener(on_press=on_press)
keyboard_listener.start()

mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
mouse_listener.start()

keyboard_listener.join()
mouse_listener.stop()
print("[TAS] - Exiting.")
