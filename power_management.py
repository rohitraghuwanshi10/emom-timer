import sys
import ctypes
import os

class PowerManager:
    def __init__(self):
        self.os_type = sys.platform
        self.reason = "EMOM Timer Workout"
        self._assertion_id = None
        
    def prevent_sleep(self):
        """Prevents the system from sleeping."""
        if self.os_type == 'win32':
            self._prevent_sleep_windows()
        elif self.os_type == 'darwin':
            self._prevent_sleep_macos()
        else:
            print(f"Power management not supported on {self.os_type}")

    def allow_sleep(self):
        """Allows the system to sleep normally."""
        if self.os_type == 'win32':
            self._allow_sleep_windows()
        elif self.os_type == 'darwin':
            self._allow_sleep_macos()

    def _prevent_sleep_windows(self):
        """
        Uses SetThreadExecutionState to prevent sleep on Windows.
        Flags:
        ES_CONTINUOUS (0x80000000)
        ES_SYSTEM_REQUIRED (0x00000001)
        ES_DISPLAY_REQUIRED (0x00000002)
        """
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            print("Windows Sleep Prevention Active")
        except Exception as e:
            print(f"Failed to prevent sleep on Windows: {e}")

    def _allow_sleep_windows(self):
        """Resets execution state."""
        try:
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            print("Windows Sleep Prevention Released")
        except Exception as e:
            print(f"Failed to allow sleep on Windows: {e}")

    def _prevent_sleep_macos(self):
        """
        Uses IOKit to create an assertion preventing display sleep on macOS.
        """
        if self._assertion_id is not None:
             return # Already active

        try:
            # Constants
            kIOPMAssertionTypeNoDisplaySleep = "NoDisplaySleepAssertion"
            kIOPMAssertionLevelOn = 255
            
            # Load Frameworks
            IOKit = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
            
            # Define Types for IOPMAssertionCreateWithName
            # IOReturn IOPMAssertionCreateWithName(CFStringRef, IOPMAssertionLevel, CFStringRef, IOPMAssertionID *)
            IOKit.IOPMAssertionCreateWithName.argtypes = [
                ctypes.c_void_p, # CFStringRef type
                ctypes.c_uint32, # IOPMAssertionLevel level
                ctypes.c_void_p, # CFStringRef reason
                ctypes.POINTER(ctypes.c_uint32) # IOPMAssertionID *AssertionID
            ]
            IOKit.IOPMAssertionCreateWithName.restype = ctypes.c_int # IOReturn

            # Create string for reason
            reason_cf = self._cf_string(self.reason)
            type_cf = self._cf_string(kIOPMAssertionTypeNoDisplaySleep)
            
            # Output variable for Assertion ID
            assertion_id = ctypes.c_uint32(0)
            
            # Call IOPMAssertionCreateWithName
            ret = IOKit.IOPMAssertionCreateWithName(
                type_cf,
                kIOPMAssertionLevelOn,
                reason_cf,
                ctypes.byref(assertion_id)
            )
            
            if ret == 0:
                self._assertion_id = assertion_id
                print(f"MacOS Sleep Prevention Active (ID: {self._assertion_id.value})")
            else:
                print(f"Failed to create sleep assertion (Error: {ret})")
                
        except Exception as e:
            print(f"Failed to prevent sleep on MacOS: {e}")

    def _allow_sleep_macos(self):
        """Releases the IOKit assertion."""
        if self._assertion_id is None:
            return

        try:
            IOKit = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
            
            # IOReturn IOPMAssertionRelease(IOPMAssertionID)
            IOKit.IOPMAssertionRelease.argtypes = [ctypes.c_uint32]
            IOKit.IOPMAssertionRelease.restype = ctypes.c_int

            ret = IOKit.IOPMAssertionRelease(self._assertion_id)
            
            if ret == 0:
                 print("MacOS Sleep Prevention Released")
                 self._assertion_id = None
            else:
                 print(f"Failed to release assertion (Error: {ret})")
                 
        except Exception as e:
            print(f"Failed to allow sleep on MacOS: {e}")

    def _cf_string(self, p_string):
        """Helper to create a CFStringRef from python string."""
        CoreFoundation = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        
        # CFStringRef CFStringCreateWithCString(CFAllocatorRef, const char *, CFStringEncoding)
        CoreFoundation.CFStringCreateWithCString.argtypes = [
            ctypes.c_void_p, # CFAllocatorRef
            ctypes.c_char_p, # const char *
            ctypes.c_uint32  # CFStringEncoding
        ]
        CoreFoundation.CFStringCreateWithCString.restype = ctypes.c_void_p # CFStringRef
        
        # kCFStringEncodingUTF8 = 0x08000100
        return CoreFoundation.CFStringCreateWithCString(
            None, 
            p_string.encode('utf-8'), 
            0x08000100
        )
