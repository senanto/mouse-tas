from pynput import mouse, keyboard
from pynput.mouse import Button, Controller
import json
import time
import threading
import sys

SPEED = 200.0

events = []
recording = False
start_time = 0

mode = "idle"
play_thread = None
play_events = []
play_start_time = 0
play_index = 0
pause_flag = False

append_mode = False
base_events = []
new_events = []
append_start_time = 0
base_last_time = 0
backup_base = []
append_history = []

mouse_controller = Controller()

def beep():
    def _beep():
        try:
            import winsound
            winsound.Beep(1000, 300)
        except:
            sys.stdout.write('\a')
            sys.stdout.flush()
    threading.Thread(target=_beep, daemon=True).start()

def on_press(key):
    global recording, events, start_time, mode, play_thread, play_events, play_start_time, play_index, pause_flag
    global append_mode, base_events, new_events, append_start_time, base_last_time, backup_base, append_history
    try:
        if key == keyboard.KeyCode.from_char('q'):
            print("[TAS] - Shutting down...")
            beep()
            beep()
            if play_thread and play_thread.is_alive():
                play_thread.join(0.1)
            sys.exit(0)

        elif key == keyboard.KeyCode.from_char('r'):
            if mode == "idle" or mode == "recording":
                if not recording:
                    print("[TAS] - Recording started...")
                    mode = "recording"
                    recording = True
                    events = []
                    start_time = time.time()
                    beep()
                else:
                    recording = False
                    mode = "idle"
                    for e in events:
                        e['time'] -= start_time
                    with open('mouse_tas.json', 'w') as f:
                        json.dump(events, f, indent=2)
                    print(f"[TAS] - Recording stopped. Saved {len(events)} events to mouse_tas.json")
                    beep()
                    beep()

        elif key == keyboard.KeyCode.from_char('s'):
            if mode == "idle" or mode == "playing" or mode == "paused":
                if mode == "playing" or mode == "paused":
                    mode = "idle"
                    pause_flag = False
                    if play_thread and play_thread.is_alive():
                        play_thread.join(0.1)
                    print("[TAS] - Playback stopped.")
                    beep()
                    beep()
                try:
                    with open('mouse_tas.json', 'r') as f:
                        play_events = json.load(f)
                    if not play_events:
                        print("[TAS] - No events to play.")
                        beep()
                        return
                    print(f"[TAS] - Playing started (speed {SPEED}x)...")
                    beep()
                    mode = "playing"
                    pause_flag = False
                    play_index = 0
                    play_start_time = time.time()
                    if play_thread is None or not play_thread.is_alive():
                        play_thread = threading.Thread(target=play_loop)
                        play_thread.start()
                except FileNotFoundError:
                    print("[TAS] - No recorded file found.")
                    beep()

        elif key == keyboard.KeyCode.from_char('p'):
            if mode == "playing":
                pause_flag = not pause_flag
                if pause_flag:
                    print("[TAS] - Paused.")
                    beep()
                else:
                    print("[TAS] - Resumed.")
                    beep()
                    beep()
            elif mode == "paused":
                pause_flag = False
                mode = "playing"
                print("[TAS] - Resumed.")
                beep()
                beep()

        elif key == keyboard.KeyCode.from_char('a'):
            if mode == "idle" or mode == "append":
                if not append_mode:
                    try:
                        with open('mouse_tas.json', 'r') as f:
                            base_events = json.load(f)
                    except FileNotFoundError:
                        base_events = []
                    new_events = []
                    append_start_time = time.time()
                    base_last_time = base_events[-1]['time'] if base_events else 0
                    backup_base = base_events.copy()
                    append_mode = True
                    mode = "append"
                    print(f"[TAS] - Append mode started. Existing events: {len(base_events)}")
                    beep()
                else:
                    append_mode = False
                    mode = "idle"
                    if new_events:
                        offset = base_last_time + 0.05
                        for e in new_events:
                            e['time'] = e['time'] - append_start_time + offset
                        append_history.append({
                            'before': backup_base,
                            'added': new_events.copy()
                        })
                        base_events.extend(new_events)
                        with open('mouse_tas.json', 'w') as f:
                            json.dump(base_events, f, indent=2)
                        print(f"[TAS] - Append finished. Total events: {len(base_events)}")
                    else:
                        print("[TAS] - No new events to append.")
                    beep()
                    beep()

        elif key == keyboard.KeyCode.from_char('z'):
            if recording:
                if events:
                    removed = events.pop()
                    print(f"[TAS] - Removed last event: {removed['type']}")
                    beep()
                else:
                    print("[TAS] - No events to remove.")
                    beep()
            elif append_mode:
                if new_events:
                    removed = new_events.pop()
                    print(f"[TAS] - Removed last appended event: {removed['type']}")
                    beep()
                else:
                    print("[TAS] - No appended events to remove.")
                    beep()
            else:
                if append_history:
                    last = append_history.pop()
                    base_events = last['before']
                    with open('mouse_tas.json', 'w') as f:
                        json.dump(base_events, f, indent=2)
                    print(f"[TAS] - Undo last append. Total events: {len(base_events)}")
                    beep()
                    beep()
                else:
                    print("[TAS] - No append to undo.")
                    beep()
    except AttributeError:
        pass

def play_loop():
    global mode, play_index, play_start_time, pause_flag
    if not play_events:
        return

    first_event = play_events[0]
    if first_event['type'] in ('move', 'click'):
        mouse_controller.position = (first_event['x'], first_event['y'])
    last_x, last_y = mouse_controller.position

    speed_factor = SPEED / 10.0
    step_size = max(5, int(8 * speed_factor))
    step_delay = 0.001 / speed_factor
    click_delay = 0.002 / speed_factor

    while mode == "playing" or mode == "paused":
        if mode == "paused":
            time.sleep(0.005)
            continue
        if play_index >= len(play_events):
            print("[TAS] - Playback finished.")
            beep()
            beep()
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
            target_x, target_y = event['x'], event['y']
            dx = target_x - last_x
            dy = target_y - last_y
            distance = (dx*dx + dy*dy) ** 0.5
            if distance > 0:
                steps = max(1, int(distance / step_size))
                for i in range(1, steps + 1):
                    t = i / steps
                    x = int(last_x + dx * t)
                    y = int(last_y + dy * t)
                    mouse_controller.position = (x, y)
                    time.sleep(step_delay)
                last_x, last_y = target_x, target_y
            else:
                mouse_controller.position = (target_x, target_y)

        elif event['type'] == 'click':
            if (last_x, last_y) != (event['x'], event['y']):
                mouse_controller.position = (event['x'], event['y'])
                last_x, last_y = event['x'], event['y']
                time.sleep(click_delay)
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
    elif append_mode:
        new_events.append({'type':'move','x':x,'y':y,'time':time.time()})

def on_click(x, y, button, pressed):
    if recording:
        events.append({'type':'click','x':x,'y':y,'button':button.name,'pressed':pressed,'time':time.time()})
    elif append_mode:
        new_events.append({'type':'click','x':x,'y':y,'button':button.name,'pressed':pressed,'time':time.time()})

def on_scroll(x, y, dx, dy):
    if recording:
        events.append({'type':'scroll','x':x,'y':y,'dx':dx,'dy':dy,'time':time.time()})
    elif append_mode:
        new_events.append({'type':'scroll','x':x,'y':y,'dx':dx,'dy':dy,'time':time.time()})

print("[TAS] - Mouse TAS Recorder/Player")
print("[TAS] - R: record start/stop, S: play/stop, P: pause/resume")
print("[TAS] - A: append mode start/stop, Z: undo last event/append, Q: shutdown")
print(f"[TAS] - Playback speed: {SPEED}x")

keyboard_listener = keyboard.Listener(on_press=on_press)
keyboard_listener.start()

mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
mouse_listener.start()

keyboard_listener.join()
mouse_listener.stop()
print("[TAS] - Exiting.")
