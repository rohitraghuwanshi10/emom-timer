import asyncio
import threading
from bleak import BleakClient, BleakScanner

# Standard Heart Rate Service UUID
HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
# Heart Rate Measurement Characteristic UUID
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

class HeartRateMonitor:
    def __init__(self, on_hr_update=None, on_status_change=None):
        self.on_hr_update = on_hr_update
        self.on_status_change = on_status_change
        self.client = None
        self.loop = None
        self.thread = None
        self._stop_event = asyncio.Event()
        self.is_connected = False

    def start(self):
        """Starts the BLE loop in a separate thread."""
        if self.thread and self.thread.is_alive():
            return

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        """Internal method to run the asyncio loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_listen())

    async def _connect_and_listen(self):
        self._update_status("Scanning...")
        
        try:
            # specifically look for devices with Heart Rate Service
            device = await BleakScanner.find_device_by_filter(
                lambda d, ad: HR_SERVICE_UUID.lower() in [s.lower() for s in ad.service_uuids]
            )

            if not device:
                self._update_status("No HR Device Found")
                return

            self._update_status(f"Connecting to {device.name}...")

            async with BleakClient(device, disconnected_callback=self._on_disconnect) as client:
                self.client = client
                self.is_connected = True
                self._update_status("Connected")

                await client.start_notify(HR_MEASUREMENT_UUID, self._notification_handler)

                # Keep running until stop event is set
                while not self._stop_event.is_set() and client.is_connected:
                    await asyncio.sleep(1.0)

                await client.stop_notify(HR_MEASUREMENT_UUID)
                self.is_connected = False
        
        except Exception as e:
            self._update_status(f"Error: {e}")
            print(f"BLE Error: {e}")
        finally:
            self._update_status("Disconnected")
            self.is_connected = False

    def stop(self):
        """Signals the loop to stop and disconnect."""
        if self.loop:
            self.loop.call_soon_threadsafe(self._stop_event.set)

    def _notification_handler(self, sender, data):
        """Parses the heart rate measurement characteristic."""
        # First byte: flags
        flags = data[0]
        hr_format = flags & 0x01
        
        if hr_format == 0:
            # UINT8
            hr_val = data[1]
        else:
            # UINT16
            hr_val = int.from_bytes(data[1:3], byteorder='little')

        if self.on_hr_update:
            self.on_hr_update(hr_val)

    def _on_disconnect(self, client):
        self.is_connected = False
        self._update_status("Disconnected")

    def _update_status(self, status):
        if self.on_status_change:
            self.on_status_change(status)
