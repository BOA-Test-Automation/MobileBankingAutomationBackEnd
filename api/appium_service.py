import os
import subprocess
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.conf import settings
import logging
import time
from appium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webelement import WebElement
import json
from functools import wraps
from appium.options.android import UiAutomator2Options

logger = logging.getLogger(__name__)

def socket_emit(event, message):
    """Helper to emit socket messages"""
    channel_layer = get_channel_layer()
    asyncio.run(channel_layer.group_send("appium", {
        'type': 'send_message',
        'event': event,
        'message': message
    }))

def sync_async_wrapper(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper

class CriticalStepError(Exception):

    def __init__(self, message, step_order, element_id):
        super().__init__(message)
        self.message = message
        self.step_order = step_order
        self.element_id = element_id

class AppiumService:
    _instance = None
    driver = None
    
    _instance = None
    driver = None

    # def __init__(self):
    #     self.driver = None
    #     self._socket_emit = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppiumService, cls).__new__(cls)
        return cls._instance
    
    async def _socket_emit(self, event, message):
        channel_layer = get_channel_layer()
        await channel_layer.group_send("appium", {
            'type': 'log_message',  # Must match consumer method name
            'message': message
        })

        
    
    async def get_connected_devices(self):
        try:
            adb_path = getattr(settings, 'ADB_PATH', '/usr/bin/adb')
            
            result = subprocess.run([adb_path, 'devices'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error('Failed to get devices:', result.stderr)
                await self._socket_emit('log', f'Failed to get devices: {result.stderr}')
                return {'devices': []}
            
            devices = []
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('List of devices') and line.endswith('device'):
                    udid = line.split('\t')[0]
                    
                    try:
                        version_result = subprocess.run(
                            [adb_path, '-s', udid, 'shell', 'getprop', 'ro.build.version.release'],
                            capture_output=True, text=True
                        )
                        version = version_result.stdout.strip() if version_result.returncode == 0 else 'Unknown'
                        
                        model_result = subprocess.run(
                            [adb_path, '-s', udid, 'shell', 'getprop', 'ro.product.model'],
                            capture_output=True, text=True
                        )
                        model = model_result.stdout.strip() if model_result.returncode == 0 else 'Unknown'
                        
                        manufacturer_result = subprocess.run(
                            [adb_path, '-s', udid, 'shell', 'getprop', 'ro.product.manufacturer'],
                            capture_output=True, text=True
                        )
                        manufacturer = manufacturer_result.stdout.strip().lower() if manufacturer_result.returncode == 0 else 'Unknown'
                        
                        platform = 'Android'
                        if 'apple' in manufacturer or (len(udid) == 40 and all(c in 'abcdef0123456789' for c in udid.lower())):
                            platform = 'iOS'
                            
                        devices.append({
                            'device_uuid': udid,
                            'device_name': model if model != 'Unknown' else f'Device {udid[:8]}',
                            'os_version': version,
                            'platform': platform
                        })
                        
                    except Exception as e:
                        logger.error(f'Error getting device details for {udid}: {str(e)}')
                        devices.append({
                            'device_uuid': udid,
                            'device_name': f'Device {udid[:8]}',
                            'os_version': 'Unknown',
                            'platform': 'Unknown'
                        })
            
            return {'devices': devices}
            
        except Exception as e:
            logger.error('Error in get_connected_devices:', str(e))
            await self._socket_emit('log', f'Error in get_connected_devices: {str(e)}')
            return {'devices': []}
    
    @sync_async_wrapper
    async def start_session(self, capabilities):
        try:
            logger.info(f'Starting new Appium session with capabilities: {capabilities}')
            await self._socket_emit('log', f'Starting new Appium session with capabilities: {capabilities}')
            
            max_retries = 3
            last_error = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    options = UiAutomator2Options().load_capabilities(capabilities)
                    
                    # Set longer timeout values (in seconds)
                    options.new_command_timeout = 3600  # 1 hour timeout
                    options.app_wait_duration = 30000  # 30 seconds
                    options.android_install_timeout = 300000  # 5 minutes
                    
                    # Add these important options
                    options.udid = capabilities.get('appium:udid')  # Ensure device connection
                    options.no_reset = True  # Don't reset app state between sessions
                    options.full_reset = False  # Don't uninstall app between sessions

                    self.driver = webdriver.Remote(
                        command_executor=f"http://{settings.APPIUM_HOST}:{settings.APPIUM_PORT}",
                        options=options
                    )
                    
                    logger.info(f'Session started with ID: {self.driver.session_id}')
                    await self._socket_emit('log', f'Session started with ID: {self.driver.session_id}')
                    return self.driver
                    
                except Exception as error:
                    last_error = error
                    logger.warning(f'Session start attempt {attempt} failed: {str(error)}')
                    await self._socket_emit('log', f'Session start attempt {attempt} failed: {str(error)}')
                    if attempt < max_retries:
                        await asyncio.sleep(2)
            
            raise last_error
            
        except Exception as error:
            logger.error(f'Failed to start session after retries: {str(error)}')
            await self._socket_emit('log', f'Failed to start session after retries: {str(error)}')
            raise error
       
    async def _find_element(self, selector):
        """Fixed element finding with proper locator strategy"""
        try:
            # Parse the selector string (e.g., "~9" -> ('accessibility id', '9'))
            if selector.startswith('~'):
                by, value = 'accessibility id', selector[1:]
            elif selector.startswith('android='):
                by, value = '-android uiautomator', selector[8:]
            elif selector.startswith('id='):
                by, value = 'id', selector[3:]
            elif selector.startswith('class='):
                by, value = 'class name', selector[6:]
            elif selector.startswith('xpath='):
                by, value = 'xpath', selector[6:]
            else:
                by, value = 'id', selector  # Default fallback

            element = await self.driver.find_element(by, value)
            return element
        except Exception as e:
            print(f"Element not found: {selector} - {str(e)}")  # Debug selector issues
            raise

    def _map_identifier_type(self, identifier):
        """Maps frontend identifier types to Appium format"""
        mapping = {
            'ID': 'id',
            'CLASS_NAME': 'class name',
            'ANDROID_UIAUTOMATOR': '-android uiautomator',
            'XPATH': 'xpath',
            'ACCESSIBILITY_ID': 'accessibility id'
        }
        return mapping.get(identifier, 'id')  # Default to 'id' if not found

    def _get_selector(self, step):
        """Exactly matches your Node.js selector format"""
        selector_map = {
            'id': f'id={step["ElementId"]}',
            'class name': f'class={step["ElementId"]}',
            '-android uiautomator': f'android={step["ElementId"]}',
            'xpath': f'xpath={step["ElementId"]}',
            'accessibility id': f'~{step["ElementId"]}'
        }
        return selector_map.get(step["ElementIdentifier"], 
                            f'Unsupported locator strategy: {step["ElementIdentifier"]}')

    async def _apply_waits(self, element, options):
        """Matches your Node.js wait sequence exactly"""
        wait = WebDriverWait(self.driver, options['timeout'])
        wait.until(EC.presence_of_element_located(element))
        wait.until(EC.visibility_of(element))
        wait.until(lambda el: el.is_enabled())

    async def _execute_action(self, element, action, input_value=None):
        """Fixed action execution with proper error handling"""
        try:
            if action == 'click':
                await element.click()
            elif action == 'send_keys':
                await element.send_keys(input_value or "")
            elif action == 'clear':
                await element.clear()
            elif action == 'get_text':
                return {'success': True, 'text': await element.text}
            elif action == 'is_displayed':
                return {'success': True, 'displayed': await element.is_displayed()}
            else:
                raise ValueError(f"Unsupported action: {action}")
            return None
        except Exception as e:
            print(f"Action failed: {action} - {str(e)}")
    
    async def end_session(self):
        if self.driver:
            try:
                logger.info("Ending Appium session")
                await self._socket_emit('log', 'Ending Appium session')
                self.driver.quit()
                self.driver = None
                return {"success": True}
            except Exception as e:
                logger.error(f"Failed to end session: {str(e)}")
                await self._socket_emit('log', f'Failed to end session: {str(e)}')
                raise
        return {"success": False, "message": "No active session"}
    
    async def get_session_info(self):
        if not self.driver:
            return None
        return {
            'sessionId': self.driver.session_id,
            'capabilities': self.driver.capabilities
        }

    def _get_locator_tuple(self, step: dict) -> tuple:

        element_id = step["ElementId"]
        identifier = step["ElementIdentifier"]

        BY_MAP = {
            'id': (AppiumBy.ID, element_id),
            'class name': (AppiumBy.CLASS_NAME, element_id),
            '-android uiautomator': (AppiumBy.ANDROID_UIAUTOMATOR, element_id),
            'xpath': (AppiumBy.XPATH, element_id),
            'accessibility id': (AppiumBy.ACCESSIBILITY_ID, element_id),
        }
        locator = BY_MAP.get(identifier)
        if not locator:
            raise ValueError(f"Unsupported locator strategy: {identifier}")
        return locator
    
    async def _find_element_with_wait(self, locator: tuple, wait_options: dict) -> WebElement:

                timeout = wait_options.get('timeout', 10)
                end_time = time.time() + timeout
                last_exception = None

                while time.time() < end_time:
                    try:
                        # BRIDGE: Run the blocking find_element call in a separate thread.
                        element = await asyncio.to_thread(self.driver.find_element, *locator)
                        
                        # BRIDGE: Check if element is ready for interaction, also in a thread.
                        is_ready = await asyncio.to_thread(lambda: element.is_displayed() and element.is_enabled())
                        
                        if is_ready:
                            return element # Success!
                        else:
                            # Element found but not ready, continue waiting.
                            last_exception = Exception("Element found but was not displayed or enabled.")

                    except NoSuchElementException as e:
                        # Element not found yet, keep trying.
                        last_exception = e

                    await asyncio.sleep(0.5) # Poll every 500ms without blocking.

                # If the loop finishes without returning, the element was never found/ready.
                raise TimeoutException(
                    f"Element with locator {locator} was not found and clickable within {timeout} seconds. Last error: {last_exception}"
                )
    
    async def _execute_action(self, element: WebElement, action: str, input_value=None) -> dict:

        action_result = {}
        # BRIDGE: Each synchronous call is wrapped to make it awaitable.
        if action == 'click':
            await asyncio.to_thread(element.click)
        elif action == 'send_keys':
            await asyncio.to_thread(element.send_keys, input_value or "")
        elif action == 'clear':
            await asyncio.to_thread(element.clear)
        elif action == 'get_text':
            text = await asyncio.to_thread(lambda: element.text)
            action_result['text'] = text
        elif action == 'is_displayed':
            displayed = await asyncio.to_thread(element.is_displayed)
            action_result['displayed'] = displayed
        else:
            raise ValueError(f"Unsupported action: {action}")
        
        return action_result
    
    async def execute_step(self, step: dict) -> dict:

        if not self.driver:
            raise Exception('No active session. Please start a session first.')

        try:
            log_message = f'Executing step {step["Step_order"]}: {step["Action"]} on {step["ElementId"]}'
            logger.info(log_message)
            if self._socket_emit:
                await self._socket_emit('log', log_message)

            # Step 1: Find the element with proper waiting logic.
            locator = self._get_locator_tuple(step)
            element = await self._find_element_with_wait(locator, {'timeout': 25})

            # Step 2: Execute the action on the found element.
            start_time = time.time()
            action_error = None
            action_result = {}

            try:
                action_result = await self._execute_action(
                    element, step["Action"], step.get("ActualInput")
                )
            except Exception as err:
                logger.warning(f"Action '{step['Action']}' failed on element '{step['ElementId']}': {err}")
                action_error = str(err)
            
            # Step 3: Format and return the final result.
            duration = round(time.time() - start_time, 4)
            response = {
                'success': not action_error,
                'actual_id': step["ElementId"],
                'duration': duration,
                'error': action_error,
                **action_result
            }
            return response

        except (TimeoutException, ValueError, NoSuchElementException) as error:
            # If finding the element fails, raise our specific critical error.
            raise CriticalStepError(
                message=f"Element '{step['ElementId']}' not found",
                step_order=step.get('Step_order'),
                element_id=step.get('ElementId')
            )
        except Exception as error:
            # Catch any other unexpected errors and re-raise them.
            logger.error(f"An unexpected error occurred in execute_step: {error}", exc_info=True)
            raise