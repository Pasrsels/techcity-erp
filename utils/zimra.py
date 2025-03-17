import os
import requests
import datetime
from loguru import logger
from dotenv import load_dotenv
from apps.settings.models import OfflineReceipt


load_dotenv()

today = datetime.datetime.today()

# Configure Loguru to log to a file and console
logger.add("app.log", rotation="1 MB", level="INFO")


class ZIMRA:
    def __init__(self):
        # Initialize environment variables as instance variables
        self.activation_key = os.getenv("ACTIVATION_KEY", "default_key")
        self.device_model_name = os.getenv("DEVICE_MODEL_NAME", "default_name")
        self.device_model_version = os.getenv("DEVICE_MODEL_VERSION", "1.0")
        self.certificate_path = os.getenv("CERTIFICATE_PATH", "cert.pem")
        self.device_id = os.getenv("DEVICE_ID", "default_id")

        self.base_url=f'https://fdmsapitest.zimra.co.zw/Public/v1/{self.device_id}/RegisterDevice'

        logger.info(f"ZIMRA initialized with:")
        logger.info(f"  - Activation Key: {self.activation_key}")
        logger.info(f"  - Device Model Name: {self.device_model_name}")
        logger.info(f"  - Device Model Version: {self.device_model_version}")
        logger.info(f"  - Certificate Path: {self.certificate_path}")
    
    def register_device(self):
        """Sends a POST request to register the device with ZIMRA API and saves the signed certificate."""
        payload = {
            "activationKey": self.activation_key,
            "certificateRequest": self.load_certificate()  
        }

        headers = {
            "Content-Type": "application/json",
            "deviceModelName": self.device_model_name,
            "deviceModelVersion": float(self.device_model_version),
        }

        try:
            response = requests.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()  
            
            # Extract the signed certificate from the response
            signed_certificate = response.json().get("certificate")
            
            if signed_certificate:
                self.save_certificate(signed_certificate)
                logger.info("Signed certificate received and saved successfully.")
                return signed_certificate
            else:
                logger.error("No signed certificate received in response.")
                return None

        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return None

    def load_certificate(self):
        """Reads the existing certificate request file if it exists."""
        try:
            with open(self.certificate_path, "r") as cert_file:
                return cert_file.read()
        except FileNotFoundError:
            logger.error(f"Certificate request file not found at {self.certificate_path}")
            return "CERTIFICATE REQUEST NOT FOUND"

    def save_certificate(self, signed_certificate):
        """Saves the signed certificate to the default certificate path."""
        try:
            with open(self.certificate_path, "w") as cert_file:
                cert_file.write(signed_certificate)
            logger.info(f"Signed certificate saved at {self.certificate_path}")
        except Exception as e:
            logger.error(f"Failed to save signed certificate")

    def submit_file(self, file_data):
        url = f"{self.base_url}/SubmitFile"
        payload = {
            "file": file_data
        }
        headers = {
            "Content-Type": "application/json",
            "DeviceModelName": self.device_model_name,
            "DeviceModelVersion": self.device_model_version
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info("File submitted successfully.")
            return response.json()
        except Exception as e:
            logger.error(f"Error submitting file: {e}")
            return None







zimra_instance = ZIMRA()
# logger.info(zimra_instance.registerDevice())

