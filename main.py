#!/usr/bin/env python3
from kivy.config import Config

try:
    from screeninfo import get_monitors
    monitors = get_monitors()
    if monitors:
        monitor = monitors[0]
        print(f"Monitor resolution: {monitor.width}x{monitor.height}")
        if monitor.width <= 800 or monitor.height <= 480:
            Config.set('graphics', 'fullscreen', 'auto')
        else:
            Config.set('graphics', 'width', '800')
            Config.set('graphics', 'height', '480')
            Config.set('graphics', 'fullscreen', '0')
    else:
        Config.set('graphics', 'width', '800')
        Config.set('graphics', 'height', '480')
        Config.set('graphics', 'fullscreen', '0')
except ImportError:
    print("screeninfo module not found. Using default window size 800x480.")
    Config.set('graphics', 'width', '800')
    Config.set('graphics', 'height', '480')
    Config.set('graphics', 'fullscreen', '0')

import os
import requests
import xml.etree.ElementTree as ET
import socket

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.image import Image

from dotenv import load_dotenv, find_dotenv

# Load the .env file.
dotenv_path = find_dotenv()
print("Found .env file at:", dotenv_path)
load_dotenv(override=True)

# Use a directory inside the user’s home directory to store icons.
ICON_DIR = os.environ.get("ICON_DIR", os.path.join(os.path.expanduser("~"), "remote_control_icons"))
if not os.path.exists(ICON_DIR):
    os.makedirs(ICON_DIR)

def get_icon(app_id, roku_ip):
    """
    Try to load the app icon from a file. If not available, retrieve it from the Roku device.
    The icon is saved as 'app<app_id>.png'
    """
    icon_path = os.path.join(ICON_DIR, f"app{app_id}.png")
    
    if os.path.exists(icon_path):
        print(f"Loaded icon from file: {icon_path}")
        return icon_path

    # Build the URL to fetch the icon from the Roku device.
    url = f"http://{roku_ip}:8060/query/icon/{app_id}"
    print(f"Fetching icon from: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(icon_path, 'wb') as file:
            file.write(response.content)
        print(f"Saved icon to file: {icon_path}")
        return icon_path
    else:
        print("Icon failed to save")
        return None

from kivy.uix.behaviors import ButtonBehavior

class AppIcon(ButtonBehavior, Image):
    def __init__(self, app_id, remote, **kwargs):
        kwargs.setdefault("allow_stretch", True)
        kwargs.setdefault("keep_ratio", True)
        kwargs.setdefault("size_hint", (1, 1))
        super().__init__(**kwargs)
        self.app_id = app_id
        self.remote = remote
        self.update_icon()

    def update_icon(self):
        icon_path = get_icon(self.app_id, self.remote.active_tv)
        if not icon_path:
            icon_path = "fallback.png"
        self.source = icon_path
        self.reload()

    def on_release(self):
        self.remote.launch_app(self.app_id)

class RemoteControlApp(App):
    def get_local_ip(self):
        """Return the local IP address of the current device."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Using Google's public DNS server to determine the outgoing interface.
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
        
    def build(self):
        # Load configuration from environment variables.
        self.tv1_ip = os.environ.get("TV01_IP", "10.24.10.23")
        self.tv2_ip = os.environ.get("TV02_IP", "10.24.10.99")
        self.app1_id = os.environ.get("APP1_ID", "app1")
        self.app2_id = os.environ.get("APP2_ID", "app2")
        self.app3_id = os.environ.get("APP3_ID", "app3")
        self.app4_id = os.environ.get("APP4_ID", "app4")
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "admin")

        self.active_tv = self.tv1_ip  # Start by controlling TV01.
        self.admin_mode = False       # Admin mode is off by default.

        # Main vertical layout.
        main_layout = BoxLayout(orientation='vertical')

        # Top bar: TV selector and invisible admin login trigger.
        local_ip = self.get_local_ip()

        # Create a top bar with three widgets: left button, center label, right admin button.
        top_bar = BoxLayout(size_hint_y=0.1)

        # Left: TV toggle button.
        self.tv_toggle_btn = Button(text="TV: 1", size_hint_x=0.2)
        self.tv_toggle_btn.bind(on_release=self.toggle_tv)

        # Center: Label showing the local IP in gray text.
        # (If you wish to show the port for the Flask server, update the text accordingly.)
        center_label = Label(
            text=f"{local_ip}:5000",
            color=(0.5, 0.5, 0.5, 1),  # Gray text.
            size_hint_x=0.6
        )
        center_label.halign = "center"
        center_label.valign = "middle"
        # Bind the label size so that text is properly centered.
        center_label.bind(size=center_label.setter('text_size'))

        # Right: Invisible admin login button.
        admin_btn = Button(text="", background_color=(0, 0, 0, 0), size_hint_x=0.2)
        admin_btn.bind(on_release=self.show_admin_login)

        # Add the three widgets to the top bar.
        top_bar.add_widget(self.tv_toggle_btn)
        top_bar.add_widget(center_label)
        top_bar.add_widget(admin_btn)
        main_layout.add_widget(top_bar)

        # Middle area: D-pad controls in a 3x3 grid.
        controls_layout = GridLayout(cols=3, rows=3, size_hint_y=0.6)
        controls_layout.add_widget(Label())  # Top-left placeholder.

        up_btn = Button(text="Up")
        up_btn.bind(on_release=lambda x: self.send_keypress("Up"))
        controls_layout.add_widget(up_btn)

        controls_layout.add_widget(Label())  # Top-right placeholder.

        left_btn = Button(text="Left")
        left_btn.bind(on_release=lambda x: self.send_keypress("Left"))
        controls_layout.add_widget(left_btn)

        ok_btn = Button(text="OK")
        ok_btn.bind(on_release=lambda x: self.send_keypress("Select"))
        controls_layout.add_widget(ok_btn)

        right_btn = Button(text="Right")
        right_btn.bind(on_release=lambda x: self.send_keypress("Right"))
        controls_layout.add_widget(right_btn)

        controls_layout.add_widget(Label())  # Bottom-left placeholder.

        down_btn = Button(text="Down")
        down_btn.bind(on_release=lambda x: self.send_keypress("Down"))
        controls_layout.add_widget(down_btn)

        controls_layout.add_widget(Label())  # Bottom-right placeholder.

        main_layout.add_widget(controls_layout)

        # Lower area: Direct-launch app icons.
        apps_layout = BoxLayout(orientation='horizontal', size_hint_y=0.15)
        self.app_icons = []
        for app_id in [self.app1_id, self.app2_id, self.app3_id, self.app4_id]:
            icon = AppIcon(app_id=app_id, remote=self)
            self.app_icons.append(icon)
            apps_layout.add_widget(icon)
        main_layout.add_widget(apps_layout)

        # Admin controls: initially hidden.
        self.admin_layout = BoxLayout(orientation='horizontal', size_hint_y=0.15)
        self.admin_layout.opacity = 0
        self.admin_layout.disabled = True

        home_btn = Button(text="Home")
        home_btn.bind(on_release=lambda x: self.send_keypress("Home"))
        self.admin_layout.add_widget(home_btn)

        vol_up_btn = Button(text="Volume Up")
        vol_up_btn.bind(on_release=lambda x: self.send_keypress("VolumeUp"))
        self.admin_layout.add_widget(vol_up_btn)

        vol_down_btn = Button(text="Volume Down")
        vol_down_btn.bind(on_release=lambda x: self.send_keypress("VolumeDown"))
        self.admin_layout.add_widget(vol_down_btn)

        power_btn = Button(text="Power")
        power_btn.bind(on_release=lambda x: self.send_keypress("Power"))
        self.admin_layout.add_widget(power_btn)
        
        # New admin button to reload the .env file.
        reload_btn = Button(text="Reload Env")
        reload_btn.bind(on_release=lambda x: self.reload_env())
        self.admin_layout.add_widget(reload_btn)
        
        main_layout.add_widget(self.admin_layout)

        return main_layout

    def toggle_tv(self, instance):
        """Switch between TV01 and TV02 and update app icons (only available in admin mode)."""
        if not self.admin_mode:
            print("TV toggle is locked. Unlock admin mode to change the active TV.")
            return
        if self.active_tv == self.tv1_ip:
            self.active_tv = self.tv2_ip
            self.tv_toggle_btn.text = "TV: 2"
        else:
            self.active_tv = self.tv1_ip
            self.tv_toggle_btn.text = "TV: 1"
        # Update the app icons.
        for icon in self.app_icons:
            icon.update_icon()

    def show_admin_login(self, instance):
        """Display a popup to enter the admin password."""
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="Enter Admin Password:"))
        password_input = TextInput(password=True, multiline=False)
        content.add_widget(password_input)

        btn_layout = BoxLayout(size_hint_y=0.3, spacing=10)
        ok_btn = Button(text="OK")
        cancel_btn = Button(text="Cancel")
        btn_layout.add_widget(ok_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Admin Login", content=content, size_hint=(0.8, 0.4))

        def on_ok(instance_button):
            if password_input.text == self.admin_password:
                self.toggle_admin_mode()
                popup.dismiss()
            else:
                password_input.text = ""
                password_input.hint_text = "Incorrect, try again"

        ok_btn.bind(on_release=on_ok)
        cancel_btn.bind(on_release=lambda x: popup.dismiss())
        popup.open()

    def toggle_admin_mode(self):
        """Toggle the visibility of admin controls."""
        self.admin_mode = not self.admin_mode
        if self.admin_mode:
            self.admin_layout.opacity = 1
            self.admin_layout.disabled = False
        else:
            self.admin_layout.opacity = 0
            self.admin_layout.disabled = True

    def reload_env(self):
        """
        Reload the .env file, update configuration values, and refresh app icons.
        """
        from dotenv import load_dotenv
        load_dotenv(override=True)
        # Update configuration values from the reloaded .env file.
        self.tv1_ip = os.environ.get("TV01_IP", "10.24.10.23")
        self.tv2_ip = os.environ.get("TV02_IP", "10.24.10.99")
        self.app1_id = os.environ.get("APP1_ID", "app1")
        self.app2_id = os.environ.get("APP2_ID", "app2")
        self.app3_id = os.environ.get("APP3_ID", "app3")
        self.app4_id = os.environ.get("APP4_ID", "app4")
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
        print("Environment reloaded!")
        
        # Update the app icons with the new app IDs.
        new_app_ids = [self.app1_id, self.app2_id, self.app3_id, self.app4_id]
        for i, icon in enumerate(self.app_icons):
            if i < len(new_app_ids):
                icon.app_id = new_app_ids[i]
                icon.update_icon()

    def send_keypress(self, key):
        """
        Send a key press command to the active TV via Roku's External Control API.
        For example, to send an "Up" command, POST to:
        http://<TV_IP>:8060/keypress/Up
        """
        url = f"http://{self.active_tv}:8060/keypress/{key}"
        try:
            response = requests.post(url)
            if response.status_code == 200:
                print(f"Sent '{key}' to {self.active_tv}")
            else:
                print(f"Failed to send '{key}' command, status: {response.status_code}")
        except Exception as e:
            print(f"Error sending '{key}': {e}")

    def launch_app(self, app_id):
        """
        Launch an app on the active TV.
        According to the API, you launch an app with:
        POST to /launch/<app_id>
        """
        url = f"http://{self.active_tv}:8060/launch/{app_id}"
        try:
            response = requests.post(url)
            if response.status_code == 200:
                print(f"Launched app '{app_id}' on {self.active_tv}")
            else:
                print(f"Failed to launch app '{app_id}', status: {response.status_code}")
        except Exception as e:
            print(f"Error launching app '{app_id}': {e}")

if __name__ == '__main__':
    from admin import app as flask_app
    import threading

    # Define a function to run the Flask app.
    def run_flask():
        flask_app.run(debug=True, use_reloader=False, host="0.0.0.0", port=9000)

    # Start Flask in a separate thread.
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # The thread will exit when the main thread exits.
    flask_thread.start()

    # Now run the Kivy app in the main thread.
    RemoteControlApp().run()
