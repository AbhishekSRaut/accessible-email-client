"""
Single-instance guard for the Accessible Email Client.

Uses a Windows named mutex to detect if another instance is running,
and a local TCP socket to signal the existing instance to restore its window.
"""

import sys
import os
import socket
import threading
import logging
import ctypes

logger = logging.getLogger(__name__)

# Port used for inter-process communication between instances
_IPC_PORT = 47831
_IPC_HOST = "127.0.0.1"
_MUTEX_NAME = "AccessibleEmailClient_SingleInstance_Mutex"

# Windows API constants
_ERROR_ALREADY_EXISTS = 183


class SingleInstanceGuard:
    """
    Ensures only one instance of the application runs at a time.
    
    First instance:
      - Creates a named mutex
      - Starts a local TCP listener for 'SHOW' signals
      - Calls the restore_callback when a signal is received
    
    Second instance:
      - Detects the existing mutex
      - Sends a 'SHOW' signal to the first instance's listener
      - Exits
    """

    def __init__(self):
        self._mutex_handle = None
        self._listener_thread = None
        self._listener_socket = None
        self._running = False
        self._restore_callback = None

    def is_another_instance_running(self) -> bool:
        """
        Try to create a named mutex.
        Returns True if another instance already owns the mutex.
        """
        if sys.platform != 'win32':
            return False

        try:
            kernel32 = ctypes.windll.kernel32
            self._mutex_handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
            last_error = kernel32.GetLastError()

            if last_error == _ERROR_ALREADY_EXISTS:
                # Another instance is running
                logger.info("Another instance detected via mutex.")
                # Close our handle since we won't use it
                if self._mutex_handle:
                    kernel32.CloseHandle(self._mutex_handle)
                    self._mutex_handle = None
                return True

            logger.info("No existing instance found. We are the primary instance.")
            return False

        except Exception as e:
            logger.error(f"Failed to check mutex: {e}")
            return False

    def signal_existing_instance(self) -> bool:
        """
        Send a SHOW signal to the existing instance's TCP listener.
        Returns True if signal was sent successfully.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((_IPC_HOST, _IPC_PORT))
            sock.sendall(b"SHOW")
            sock.close()
            logger.info("Sent SHOW signal to existing instance.")
            return True
        except Exception as e:
            logger.warning(f"Failed to signal existing instance: {e}")
            return False

    def start_listener(self, restore_callback):
        """
        Start a TCP listener that waits for SHOW signals from new instances.
        When received, calls restore_callback on the main thread.
        """
        self._restore_callback = restore_callback
        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

    def _listen_loop(self):
        """Background thread: listen for IPC connections."""
        try:
            self._listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._listener_socket.settimeout(2)
            self._listener_socket.bind((_IPC_HOST, _IPC_PORT))
            self._listener_socket.listen(1)
            logger.info(f"Single-instance listener started on {_IPC_HOST}:{_IPC_PORT}")

            while self._running:
                try:
                    conn, addr = self._listener_socket.accept()
                    data = conn.recv(64)
                    conn.close()

                    if data == b"SHOW":
                        logger.info("Received SHOW signal from new instance.")
                        if self._restore_callback:
                            self._restore_callback()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        logger.debug(f"Listener accept error: {e}")

        except Exception as e:
            logger.error(f"Failed to start single-instance listener: {e}")
        finally:
            self._close_listener_socket()

    def _close_listener_socket(self):
        if self._listener_socket:
            try:
                self._listener_socket.close()
            except Exception:
                pass
            self._listener_socket = None

    def cleanup(self):
        """Release the mutex and stop the listener. Call on exit."""
        self._running = False
        self._close_listener_socket()

        if self._mutex_handle:
            try:
                ctypes.windll.kernel32.ReleaseMutex(self._mutex_handle)
                ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            except Exception:
                pass
            self._mutex_handle = None


# Module-level singleton
instance_guard = SingleInstanceGuard()
