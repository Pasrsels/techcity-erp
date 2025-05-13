import os
import rsa
import requests
import datetime
import json, base64
from loguru import logger
from dotenv import load_dotenv
from apps.settings.models import OfflineReceipt, FiscalDay, FiscalCounter

load_dotenv()

today = datetime.datetime.today()
logger.add("app.log", rotation="1 MB", level="INFO")


class DateTimeEncoder(json.JSONEncoder):
    """
        custom datetime encoder to handle datetime fields in json serialization
    """
    def default(self, obj):
        if type(obj).__name__ == 'datetime':
            return obj.isoformat()
        return super().default(obj)

class ZIMRA:

    device_identification = os.getenv("DEVICE_ID")

    def __init__(self):
        self.activation_key = os.getenv("ACTIVATION_KEY")
        self.device_model_name = os.getenv("DEVICE_MODEL_NAME")
        self.device_model_version = os.getenv("DEVICE_MODEL_VERSION")
        self.device_id = os.getenv("DEVICE_ID")
        self.certificate_path = os.getenv("CERTIFICATE_PATH", "cert.pem")
        self.certificate_key = os.getenv("CERTIFICATE_KEY", "cert_private.pem")
        self.registration_url = f'https://fdmsapitest.zimra.co.zw/Public/v1/{self.device_id}'
        self.base_url = f'https://fdmsapitest.zimra.co.zw/Device/v1/{self.device_id}'

    def register_device(self):
        payload = {
            "activationKey": self.activation_key,
            "certificateRequest": self.load_certificate()
        }

        headers = {
            "Content-Type": "application/json",
            "deviceModelName": self.device_model_name,
            "deviceModelVersion": self.device_model_version
        }
        
        try:
            response = requests.post(f"{self.registration_url}/RegisterDevice", json=payload, headers=headers)
            response.raise_for_status()
            signed_certificate = response.json().get("certificate")
            if signed_certificate:
                self.save_certificate(signed_certificate)
                logger.info("Device registered successfully.")
                return signed_certificate
        except Exception as e:
            logger.error(f"Device registration failed: {e}")

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

    def issue_certificate(self):
        url = f"https://fdmsapitest.zimra.co.zw/Device/v1/{self.device_id}/IssueCertificate"
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "DeviceModelName": self.device_model_name,
            "DeviceModelVersion": "1.0"
        }

        payload = {
            "certificateRequest": self.load_certificate()
        }

        try:
            response = requests.post(url, headers=headers, json=payload, cert=(self.certificate_path, self.certificate_key))
            response.raise_for_status()
            data = response.json()
            
            print("Issue Certificate Response:", data)
            
            if "certificate" in data:
                with open("cert.pem", "w") as cert_file:
                    cert_file.write(data["certificate"])
                print("Certificate saved to cert.pem")

            return data
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return None
        
    def get_status(self):
        headers = {
            "Content-Type": "application/json",
            "deviceModelName": self.device_model_name,
            "deviceModelVersion": self.device_model_version
        }
        try:
            response = requests.get(f"{self.base_url}/getStatus", headers=headers, cert=(self.certificate_path, self.certificate_key))
            response.raise_for_status()  
            print("GetConfig Response:", response.json())
            return response.json()
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return None

    def get_config(self):
        headers = {
            "Content-Type": "application/json",
            "deviceModelName": self.device_model_name,
            "deviceModelVersion": self.device_model_version
        }
        try:
            response = requests.get(f"{self.base_url}/getConfig", headers=headers, cert=(self.certificate_path, self.certificate_key))
            response.raise_for_status()  
            return response.json()
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return None

    def open_day(self):

        active_day = FiscalDay.objects.filter(is_open=True).first()

        if active_day:
            logger.info(f"Fiscal Day {active_day.day_no} is already open.")
            return f"Fiscal Day {active_day.day_no} is already open."

        last_day = FiscalDay.objects.order_by('-created_at').first()
        next_day_no = (last_day.day_no + 1) if last_day else 1
    
        payload = {
            "fiscalDayOpened": today.replace(microsecond=0).isoformat(),
            "fiscalDayNo": next_day_no
        }

        headers = {
            "Content-Type": "application/json",
            "deviceModelName": self.device_model_name,
            "deviceModelVersion": self.device_model_version
        }

        logger.info(f'Payload: {payload}')

        try:
            response = requests.post(f"{self.base_url}/openDay", json=payload, headers=headers, cert=(self.certificate_path, self.certificate_key))
            response.raise_for_status()

            FiscalDay.objects.create(
                day_no=next_day_no, 
                is_open=True,
                receipt_count=0
            )

            logger.info(f"Fiscal Day {next_day_no} opened successfully.")
        except Exception as e:
            logger.error(f"Error opening fiscal day: {e}")


    def submit_receipt(
            self, 
            receipt_data,
            hash,
            signature
        ):
        """
            Submits a single receipt to the FDMS.
        """
        
        try:
        
            logger.info(receipt_data)
            
            receipt_data['receipt']['receiptDeviceSignature'] = {
                "hash": hash,
                "signature": signature
            }
            
            logger.info(receipt_data)
            
        except Exception as e:
            logger.info(e)
        

        headers = {
            "Content-Type": "application/json",
            "deviceModelName": self.device_model_name,
            "deviceModelVersion": self.device_model_version
        }
        
    
        try:
            response = requests.post(f"{self.base_url}/SubmitReceipt", json=receipt_data, headers=headers, cert=(self.certificate_path, self.certificate_key))
            logger.info(response)
            r=response
            response.raise_for_status()
            logger.info("Receipt submitted successfully.")
            logger.info(response.json())
            return response.json()
        except Exception as e:
            logger.error(f"Error submitting receipt: {e}, {r}")
            return e

    def submit_file(self):

        receipts = OfflineReceipt.objects.filter(created_at__date=today)

        logger.info(f'receipts, {receipts}')

        if not receipts.exists():
            logger.info("No receipts to submit.")
            return

        active_day = FiscalDay.objects.filter(is_open=True).first()

        json_data = json.dumps({
            "header": {
                "deviceID": self.device_id,
                "fiscalDayNo": 1,
                "fiscalDayOpened": today.replace(microsecond=0),
                "fileSequence": 1
            },
            "content": {
                "receipts": [receipt.receipt_data for receipt in receipts]
            },
            "footer": {
                "fiscalDayCounters": [],
                "fiscalDayDeviceSignature": {
                    "hash": "",
                    "signature": "sample_signature"
                },
                "receiptCounter": len(receipts),
                "fiscalDayClosed": today.replace(microsecond=0),
            }
        }, cls=DateTimeEncoder)
        encoded_data = base64.b64encode(json_data.encode()).decode()

        logger.info(f'payload: {encoded_data}')
        headers = {
            "Content-Type": "application/json",
            "deviceModelName": self.device_model_name,
            "deviceModelVersion": self.device_model_version
        }

        try:
            response = requests.post(f"{self.base_url}/SubmitFile", json=json_data, headers=headers, cert=(self.certificate_path, self.certificate_key))
            response.raise_for_status()
            receipts.update(submitted=True)
            logger.info("File submitted successfully.")
            return response.json()
        except Exception as e:
            logger.error(f"Error submitting file: {e}")

    def close_day(
            self,
            hash,
            signature,
            counters
        ):
        """
        Closes the active fiscal day and submits the necessary data to ZIMRA FDMS.
        """
        active_day = FiscalDay.objects.filter(is_open=True).first()

        if not active_day: 
            logger.info("No active fiscal day to close.")
            return
        
        logger.info(f'signature: {signature}')
        logger.info(f'signature: {hash}')
        logger.info(f'signature: {counters}')

        regular_counters = []
        sale_tax_by_tax_counter = [] 
        balance_by_money_counter = [] 

        for counter in counters:
            fiscal_counter_data = {
                "fiscalCounterType": counter.fiscal_counter_type,
                "fiscalCounterCurrency": counter.fiscal_counter_currency,
                "fiscalCounterTaxPercent": float(counter.fiscal_counter_tax_percent) if counter.fiscal_counter_tax_percent != 0.00 else None,
                "fiscalCounterTaxID": counter.fiscal_counter_tax_id if counter.fiscal_counter_tax_percent != 0.00 else None,
                "fiscalCounterMoneyType": counter.fiscal_counter_money_type if counter.fiscal_counter_tax_percent == 0.00 else None,
                "fiscalCounterValue": float(round(counter.fiscal_counter_value, 2)),
            }

            if counter.fiscal_counter_type == "SaleTaxByTax":
                sale_tax_by_tax_counter.append(fiscal_counter_data)  
            elif counter.fiscal_counter_type == "BalanceByMoneyType":
                balance_by_money_counter.append(fiscal_counter_data) 
            else:
                logger.info(fiscal_counter_data)
                regular_counters.append(fiscal_counter_data)

        fiscal_day_counters = regular_counters + sale_tax_by_tax_counter + balance_by_money_counter
        
        logger.debug(fiscal_day_counters)
        
        
        
        payload = {
            "fiscalDayNo": active_day.day_no,
            "fiscaleDate": active_day.created_at.date().isoformat(),
            "fiscalDayCounters": fiscal_day_counters,
            "fiscalDayDeviceSignature": {
                "hash": hash,
                "signature": signature
            },
            "receiptCounter": active_day.receipt_count
        }

        logger.info(f"Closing Fiscal Day with payload: {payload}")

        headers = {
            "Content-Type": "application/json",
            "deviceModelName": self.device_model_name,
            "deviceModelVersion": self.device_model_version
        }

        try:
            import json
            json_payload = json.dumps(payload)
        
            logger.info(f"JSON payload: {json_payload}")
            
            response = requests.post(
                f"{self.base_url}/CloseDay", 
                data=json_payload, 
                headers=headers, 
                cert=(self.certificate_path, self.certificate_key)
            )
            response.raise_for_status()

            active_day.is_open = False
            active_day.save()

            logger.info(f"Fiscal Day {active_day.day_no} closed successfully.")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error closing fiscal day: {e}")
            return f"Error closing fiscal day: {e}"